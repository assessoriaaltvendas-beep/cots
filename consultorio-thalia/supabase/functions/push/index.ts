// Função "push" do Supabase: entrega as notificações nos celulares (Web Push), sem custo.
// Quem chama é o próprio banco de dados (gatilhos e lembretes). Não precisa de nenhuma configuração aqui.
// Como publicar: Supabase > Edge Functions > Deploy a new function > Via Editor > nome "push" > cole este arquivo > Deploy.
// Depois, nos detalhes da função, desligue "Enforce JWT verification" (ou "Verify JWT") e salve.

const HOSTS = ['fcm.googleapis.com', 'push.services.mozilla.com', 'push.apple.com', 'notify.windows.com'];
const te = new TextEncoder();
const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS' };

function b64u(bytes) {
  let s = '';
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function fromB64u(str) {
  const s = String(str).replace(/-/g, '+').replace(/_/g, '/');
  const bin = atob(s + '='.repeat((4 - (s.length % 4)) % 4));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
function concat(...parts) {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}
function hostOk(url) {
  try {
    const u = new URL(url);
    return u.protocol === 'https:' && HOSTS.some(h => u.hostname === h || u.hostname.endsWith('.' + h));
  } catch (_) { return false; }
}
async function hkdf(salt, ikm, info, bytes) {
  const key = await crypto.subtle.importKey('raw', ikm, 'HKDF', false, ['deriveBits']);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: 'HKDF', hash: 'SHA-256', salt, info }, key, bytes * 8));
}

// Assinatura VAPID (RFC 8292): identifica o consultório para o serviço de notificações.
export async function vapidHeader(endpoint, publicKey, privateKey, subject) {
  const raw = fromB64u(publicKey);
  const jwk = { kty: 'EC', crv: 'P-256', x: b64u(raw.slice(1, 33)), y: b64u(raw.slice(33, 65)), d: privateKey, ext: true };
  const key = await crypto.subtle.importKey('jwk', jwk, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
  const head = b64u(te.encode(JSON.stringify({ typ: 'JWT', alg: 'ES256' })));
  const claims = b64u(te.encode(JSON.stringify({ aud: new URL(endpoint).origin, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: subject })));
  const sig = new Uint8Array(await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, key, te.encode(head + '.' + claims)));
  return `vapid t=${head}.${claims}.${b64u(sig)}, k=${publicKey}`;
}

// Criptografia da mensagem (RFC 8291, aes128gcm): só o aparelho de destino consegue ler.
export async function encrypt(p256dh, authSecret, text, test) {
  const ua = fromB64u(p256dh), auth = fromB64u(authSecret);
  let pair, asPub;
  if (test) {
    const raw = fromB64u(test.publicKey);
    pair = { privateKey: await crypto.subtle.importKey('jwk', { kty: 'EC', crv: 'P-256', x: b64u(raw.slice(1, 33)), y: b64u(raw.slice(33, 65)), d: test.privateKey, ext: true }, { name: 'ECDH', namedCurve: 'P-256' }, false, ['deriveBits']) };
    asPub = raw;
  } else {
    pair = await crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
    asPub = new Uint8Array(await crypto.subtle.exportKey('raw', pair.publicKey));
  }
  const uaKey = await crypto.subtle.importKey('raw', ua, { name: 'ECDH', namedCurve: 'P-256' }, false, []);
  const shared = new Uint8Array(await crypto.subtle.deriveBits({ name: 'ECDH', public: uaKey }, pair.privateKey, 256));
  const ikm = await hkdf(auth, shared, concat(te.encode('WebPush: info\0'), ua, asPub), 32);
  const salt = test ? fromB64u(test.salt) : crypto.getRandomValues(new Uint8Array(16));
  const cek = await hkdf(salt, ikm, te.encode('Content-Encoding: aes128gcm\0'), 16);
  const nonce = await hkdf(salt, ikm, te.encode('Content-Encoding: nonce\0'), 12);
  const key = await crypto.subtle.importKey('raw', cek, 'AES-GCM', false, ['encrypt']);
  const cipher = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce }, key, concat(te.encode(text), new Uint8Array([2]))));
  const rs = new Uint8Array([0, 0, 16, 0]); // 4096
  return concat(salt, rs, new Uint8Array([asPub.length]), asPub, cipher);
}

const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { ...CORS, 'Content-Type': 'application/json' } });

export async function handler(req) {
  if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });
  if (req.method !== 'POST') return json({ ok: true, funcao: 'push' });
  let data;
  try { data = await req.json(); } catch (_) { return json({ erro: 'json' }, 400); }
  const v = data && data.vapid, subs = Array.isArray(data && data.subs) ? data.subs.slice(0, 500) : [];
  if (!v || !/^[A-Za-z0-9_-]{87}$/.test(v.publicKey || '') || !/^[A-Za-z0-9_-]{43}$/.test(v.privateKey || '')) return json({ erro: 'chaves' }, 400);
  const text = JSON.stringify(data.payload || {}).slice(0, 3000);
  const subject = /^(mailto:|https:\/\/)/.test(v.subject || '') ? v.subject : 'mailto:contato@consultorio.app';
  const gone = [];
  let ok = 0;
  await Promise.all(subs.map(async s => {
    if (!s || !hostOk(s.endpoint) || !s.p256dh || !s.auth) return;
    try {
      const body = await encrypt(s.p256dh, s.auth, text);
      const r = await fetch(s.endpoint, {
        method: 'POST',
        headers: {
          Authorization: await vapidHeader(s.endpoint, v.publicKey, v.privateKey, subject),
          'Content-Encoding': 'aes128gcm',
          'Content-Type': 'application/octet-stream',
          TTL: '86400',
          Urgency: 'high',
        },
        body,
      });
      if (r.status === 404 || r.status === 410) gone.push(s.endpoint);
      else if (r.ok) ok++;
    } catch (_) { /* aparelho fora do ar: tenta na próxima */ }
  }));
  return json({ ok, gone });
}

Deno.serve(handler);
