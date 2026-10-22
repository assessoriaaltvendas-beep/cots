// Simulação do supabase-js v2 para testes locais (somente o que o site usa), com regras de acesso parecidas com o schema.sql.
(function () {
  const LS = k => { try { return JSON.parse(localStorage.getItem(k)); } catch (_) { return null; } };
  const SV = (k, v) => localStorage.setItem(k, JSON.stringify(v));
  const uuid = () => 'u' + Math.random().toString(16).slice(2, 10) + Date.now().toString(16);
  function createClient() {
    const db = LS('mockdb') || { slots: [], bookings: [], dentists: [], avisos: [], problemas: [], espera: [], admins: [], users: [] };
    ['faq','app_config','pacientes','consultas','evolucoes','paciente_docs','termos_versoes','termos_aceites','planos','pac_orcamentos','pac_pagamentos'].forEach(t => { db[t] = db[t] || []; }); db.files = db.files || { fotos: [], comprovantes: [] }; db.files.pacientes = db.files.pacientes || []; db.secret = db.secret || null; db.sent = db.sent || [];
    const save = () => SV('mockdb', db);
    if (!db.termos_versoes.length) db.termos_versoes.push({ id: 'tv1', versao: 1, texto: (window.TERMOS_MOCK || 'TERMOS E CONDIÇÕES DE USO\nCOTS – teste\n1. Cancelamentos e reembolsos\nTexto de teste dos termos com mais de vinte letras.'), resumo: 'Versão inicial', criado_em: '2026-10-01T10:00:00' });
    if (window.MOCK_TERMOS_OK) db.dentists.forEach(d => { if (d.termos_versao == null) d.termos_versao = 1; });
    const termAtual = () => db.termos_versoes.slice().sort((a, b) => b.versao - a.versao)[0];
    let session = LS('mocksess');
    const listeners = [];
    const uid = () => (session && session.user.id) || null;
    function precoHora(date, h) { const c = (db.cfg || {}), p = c.precos || {}, dow = new Date(date + 'T12:00').getDay(); const r = (p.porHora || []).find(x => h >= x.de && h < x.ate); if (r) return r.valor; if (p.porDia && p.porDia[dow] != null) return p.porDia[dow]; return c.valorHora == null ? null : c.valorHora; }
    const CF = () => Object.assign({ limiteHoras: 3, periodos: [{ de: 8, ate: 13, valor: 180 }, { de: 13, ate: 18, valor: 180 }, { de: 18, ate: 22, valor: 180 }], diaria: { de: 8, ate: 18, valor: 350 } }, db.cfg || {});
    const usaPer = (a, b) => (b - a) > CF().limiteHoras && CF().periodos.length > 0;
    function precoPer(h1, h2) { const P = CF().periodos, D = CF().diaria; for (const p of P) if (h1 >= p.de && h2 <= p.ate) return p.valor; let acc = 0, cur = h1; if (D && h1 === D.de && h2 >= D.ate) { acc = D.valor; cur = D.ate; } while (cur < h2) { const p = P.find(x => x.de === cur && x.ate <= h2); if (!p) return null; acc += p.valor; cur = p.ate; } return acc; }
    const tm = t => { const [h, m] = String(t).split(':').map(Number); return h * 60 + (m || 0); };
    const horasC = c => { const out = []; for (let h = Math.floor(tm(c.inicio) / 60); h < Math.ceil(tm(c.fim) / 60); h++) out.push(h); return out; };
    function recalc(d) { db.slots = db.slots.filter(s => !(s.date === d && s.consulta)); const hs = new Set(); db.consultas.filter(c => c.data === d && c.status !== 'cancelada').forEach(c => horasC(c).forEach(h => hs.add(h))); hs.forEach(h => { if (!db.slots.some(s => s.date === d && s.hour === h)) db.slots.push({ date: d, hour: h, booking_id: null, consulta: true }); }); }
    function checaCons(c) { if (c.status === 'cancelada') return null; if (db.consultas.some(x => x.id !== c.id && x.data === c.data && x.status !== 'cancelada' && tm(x.inicio) < tm(c.fim) && tm(x.fim) > tm(c.inicio))) return 'CONSULTA_CONFLITO'; if (db.slots.some(s => s.date === c.data && s.booking_id && horasC(c).includes(s.hour))) return 'HORARIO_OCUPADO'; return null; }
    function precoReserva(date, a, b) { if (usaPer(a, b)) return precoPer(a, b); let t = 0; for (let h = a; h < b; h++) { const v = precoHora(date, h); if (v == null) return null; t += Number(v); } return t; }
    const isAdmin = () => db.admins.includes(uid());
    db.adm = db.adm || {}; db.admlog = db.admlog || []; db.calc = db.calc || { itens: null, liberada: false, base: null, log: [] };
    const nivelDe = u => (db.adm[u] || {}).nivel || 'completo';
    const isComp = () => isAdmin() && nivelDe(uid()) === 'completo';
    const userEmail = u => (db.users.find(x => x.id === u) || {}).email || '';
    const nomeDe = u => (db.adm[u] || {}).nome || (db.dentists.find(d => d.id === u) || {}).nome || userEmail(u);
    const emit = (ev) => listeners.forEach(f => f(ev, session));
    const PACT = ['pacientes', 'consultas', 'evolucoes', 'paciente_docs', 'pac_orcamentos', 'pac_pagamentos'];
    const canSee = (t, r) => {
      if (PACT.includes(t)) return isComp();
      if (t === 'slots' || t === 'faq' || t === 'termos_versoes') return true;
      if (t === 'termos_aceites' || t === 'planos') return isAdmin() || r.dentist_id === uid();
      if (t === 'app_config') return isAdmin();
      if (t === 'avisos') return !!uid();
      if (t === 'dentists') return r.id === uid() || isAdmin();
      if (['bookings', 'problemas', 'espera'].includes(t)) return isAdmin() || r.dentist_id === uid();
      if (t === 'admins') return r === uid();
      return false;
    };
    const canInsert = (t, r) => PACT.includes(t) ? isComp() : (t === 'avisos' || t === 'faq') ? isAdmin() : ['problemas', 'espera'].includes(t) ? r.dentist_id === uid() : false;
    const canUpdate = (t, r) => PACT.includes(t) ? isComp() : t === 'faq' ? isAdmin() : t === 'dentists' ? (r.id === uid() || isAdmin()) : t === 'bookings' ? (isAdmin() || r.dentist_id === uid()) : t === 'problemas' ? isAdmin() : false;
    const canDelete = (t, r) => PACT.includes(t) ? isComp() : (t === 'avisos' || t === 'faq') ? isAdmin() : t === 'espera' ? (isAdmin() || r.dentist_id === uid()) : false;
    const PROT = ['falta', 'valor_original', 'taxa_em', 'plano_id', 'plano_data_orig', 'id', 'dentist_id', 'nome', 'cro', 'tel', 'primeira', 'date', 'h_from', 'h_to', 'status', 'origem', 'serie', 'conf_aberta_em', 'pago', 'pago_em', 'criado_em', 'email', 'lembrete_em'];
    function from(t) {
      const q = { op: 'select', filters: [], single: false, payload: null };
      const b = {
        select() { return b; }, order() { return b; },
        eq(c, v) { q.filters.push(r => r[c] === v); return b; },
        gte(c, v) { q.filters.push(r => r[c] >= v); return b; },
        maybeSingle() { q.single = true; return b; },
        insert(o) { q.op = 'insert'; q.payload = o; return b; },
        update(o) { q.op = 'update'; q.payload = o; return b; },
        delete() { q.op = 'delete'; return b; },
        then(res, rej) { return Promise.resolve().then(run).then(res, rej); }
      };
      function run() {
        const rows = db[t];
        if (q.op === 'insert') {
          const r = { id: uuid(), criado_em: new Date().toISOString(), ...q.payload };
          if (t === 'problemas') r.status = r.status || 'aberto';
          if (!canInsert(t, r)) return { data: null, error: { message: 'new row violates row-level security policy' } };
          if (t === 'consultas') { r.status = r.status || 'agendada'; const er = checaCons(r); if (er) return { data: null, error: { message: er } }; }
          rows.push(r); if (t === 'consultas') recalc(r.data); save(); return { data: null, error: null };
        }
        const sel = rows.filter(r => canSee(t, r) && q.filters.every(f => f(r)));
        if (q.op === 'update') {
          if (t === 'consultas') { for (const r of sel) { const nr = { ...r, ...q.payload }; const er = checaCons(nr); if (er) return { data: null, error: { message: er } }; } }
          sel.filter(r => canUpdate(t, r)).forEach(r => {
            const p = { ...q.payload }; const od = r.data;
            if (t === 'bookings' && !isAdmin()) PROT.forEach(k => delete p[k]);
            Object.assign(r, p);
            if (t === 'consultas') { recalc(od); recalc(r.data); }
          });
          save(); return { data: null, error: null };
        }
        if (q.op === 'delete') { sel.filter(r => canDelete(t, r)).forEach(r => { rows.splice(rows.indexOf(r), 1); if (t === 'consultas') recalc(r.data); if (t === 'pacientes') { const ds = new Set(db.consultas.filter(c => c.paciente_id === r.id).map(c => c.data)); ['consultas', 'evolucoes', 'paciente_docs'].forEach(n => { db[n] = db[n].filter(x => x.paciente_id !== r.id); }); ds.forEach(recalc); } }); save(); return { data: null, error: null }; }
        const data = JSON.parse(JSON.stringify(sel));
        return { data: q.single ? (data[0] || null) : data, error: null };
      }
      return b;
    }
    const now = () => new Date();
    const isoD = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const cfgPl = () => Object.assign({ planos: { diaria: 1000, periodo: 600 }, planoAvisoDias: 3 }, db.cfg || {});
    const ERR = m => ({ data: null, error: { message: m } });
    const busy = (d, a, z) => { for (let h = a; h < z; h++) if (db.slots.some(s => s.date === d && s.hour === h)) return true; return false; };
    const horasOk = (mod, a, z) => { const c = CF(); return mod === 'diaria' ? !!c.diaria && a === c.diaria.de && z === c.diaria.ate : c.periodos.some(p => p.de === a && p.ate === z); };
    function gerar(p) {
      const d0 = db.dentists.find(d => d.id === p.dentist_id) || {}; let criadas = 0; const conf = [];
      const t = now(); for (let k = 0; k < 2; k++) {
        const m0 = new Date(t.getFullYear(), t.getMonth() + k, 1, 12), occ = [];
        for (let d = new Date(m0); d.getMonth() === m0.getMonth(); d.setDate(d.getDate() + 1)) if (d.getDay() === p.dia_semana) occ.push(isoD(d));
        const cada = Math.round(p.valor_mensal / occ.length * 100) / 100;
        occ.forEach((s, i) => {
          if (s < p.inicio || (p.fim && s > p.fim)) return;
          if (new Date(`${s}T${String(p.h_from).padStart(2, '0')}:00`) <= now()) return;
          if (db.bookings.some(b => b.plano_id === p.id && (b.plano_data_orig || b.date) === s)) return;
          if (busy(s, p.h_from, p.h_to)) { if (!(db.conf || []).includes(p.id + s)) { db.conf = (db.conf || []).concat(p.id + s); conf.push(s); } return; }
          const id = uuid(), v = i === occ.length - 1 ? p.valor_mensal - cada * (occ.length - 1) : cada;
          db.bookings.push({ id, dentist_id: p.dentist_id, nome: d0.nome || 'Dentista', cro: d0.cro || null, tel: d0.whatsapp || '', primeira: false, date: s, h_from: p.h_from, h_to: p.h_to, status: 'ativo', origem: 'plano', serie: 'plano-' + p.id, plano_id: p.id, plano_data_orig: s, valor: v, pago: false, criado_em: new Date().toISOString() });
          for (let h = p.h_from; h < p.h_to; h++) db.slots.push({ date: s, hour: h, booking_id: id });
          criadas++;
        });
      }
      save(); return { criadas, conflitos: conf };
    }
    function novoPlano(dent, a, status) {
      const hoje = isoD(now());
      if (!['diaria', 'periodo'].includes(a.p_modalidade) || !horasOk(a.p_modalidade, a.p_from, a.p_to)) return 'HORARIO_INVALIDO';
      if (new Date(a.p_inicio + 'T12:00').getDay() !== a.p_dia || a.p_inicio < hoje) return 'DADOS_INVALIDOS';
      if (db.planos.some(x => x.dentist_id === dent && ['pendente', 'ativo'].includes(x.status) && x.dia_semana === a.p_dia && x.h_from < a.p_to && x.h_to > a.p_from)) return 'PLANO_DUPLICADO';
      const p = { id: uuid(), dentist_id: dent, modalidade: a.p_modalidade, dia_semana: a.p_dia, h_from: a.p_from, h_to: a.p_to, valor_mensal: Number(cfgPl().planos[a.p_modalidade]), inicio: a.p_inicio, fim: null, status, obs: null, criado_em: new Date().toISOString(), aprovado_em: status === 'ativo' ? new Date().toISOString() : null };
      db.planos.push(p); save(); return p;
    }
    async function rpc(name, a) {
      if (name === 'is_admin') return { data: isAdmin(), error: null };
      const OK = d => ({ data: d === undefined ? null : d, error: null }), NIV = { completo: 'administrador completo', agenda: 'administrador da agenda' };
      const logA = (email, acao, det) => { db.admlog.unshift({ quando: new Date().toISOString(), autor: nomeDe(uid()), email, acao, detalhe: det }); };
      if (name === 'meu_acesso') { if (window.MOCK_V8) return ERR('function meu_acesso does not exist'); if (!uid()) return ERR('permission denied'); return OK({ admin: isAdmin(), nivel: isAdmin() ? nivelDe(uid()) : null, dentista: db.dentists.some(d => d.id === uid()), nome: (db.adm[uid()] || {}).nome || (db.dentists.find(d => d.id === uid()) || {}).nome || null }); }
      if (name === 'listar_admins') { if (!isComp()) return ERR('SEM_PERMISSAO'); return OK({ admins: db.admins.map(u => ({ id: u, email: userEmail(u), nome: (db.adm[u] || {}).nome || (db.dentists.find(d => d.id === u) || {}).nome || null, nivel: nivelDe(u), adicionado_em: (db.adm[u] || {}).em || '2026-10-01T10:00:00', por: (db.adm[u] || {}).por || null, eu: u === uid(), dentista: db.dentists.some(d => d.id === u) })), log: db.admlog.slice(0, 40) }); }
      if (name === 'adicionar_admin') { if (!isComp()) return ERR('SEM_PERMISSAO'); if (!['completo', 'agenda'].includes(a.p_nivel)) return ERR('DADOS_INVALIDOS'); const em = String(a.p_email || '').trim().toLowerCase(); const u = db.users.find(x => x.email.toLowerCase() === em); if (!u) return ERR('CONTA_NAO_ENCONTRADA'); if (db.admins.includes(u.id)) return ERR('JA_ADMIN'); db.admins.push(u.id); db.adm[u.id] = { nivel: a.p_nivel, em: new Date().toISOString(), por: nomeDe(uid()) }; logA(em, 'adicionou', NIV[a.p_nivel]); save(); return OK(u.id); }
      if (name === 'mudar_nivel_admin') { if (!isComp()) return ERR('SEM_PERMISSAO'); if (a.p_id === uid()) return ERR('NAO_PODE_SI_MESMA'); if (!db.admins.includes(a.p_id)) return ERR('ADMIN_NAO_ENCONTRADO'); const antes = nivelDe(a.p_id); if (antes === a.p_nivel) return OK(); if (antes === 'completo' && db.admins.filter(u => nivelDe(u) === 'completo').length <= 1) return ERR('ULTIMO_COMPLETO'); db.adm[a.p_id] = Object.assign(db.adm[a.p_id] || {}, { nivel: a.p_nivel }); logA(userEmail(a.p_id), 'mudou o nível', NIV[antes] + ' → ' + NIV[a.p_nivel]); save(); return OK(); }
      if (name === 'remover_admin') { if (!isComp()) return ERR('SEM_PERMISSAO'); if (a.p_id === uid()) return ERR('NAO_PODE_SI_MESMA'); if (!db.admins.includes(a.p_id)) return ERR('ADMIN_NAO_ENCONTRADO'); const nv = nivelDe(a.p_id); db.admins = db.admins.filter(u => u !== a.p_id); delete db.adm[a.p_id]; logA(userEmail(a.p_id), 'removeu', NIV[nv]); save(); return OK(); }
      if (name === 'salvar_meu_nome_admin') { if (!isAdmin()) return ERR('SEM_PERMISSAO'); db.adm[uid()] = Object.assign(db.adm[uid()] || {}, { nome: a.p_nome.trim() }); save(); return OK(); }
      if (name === 'calc_dados') { if (!uid()) return ERR('SEM_PERMISSAO'); const dn = db.dentists.find(d => d.id === uid()); if (!isAdmin() && !(dn && (dn.status || 'liberado') === 'liberado')) return ERR('SEM_PERMISSAO'); const c = db.calc; return OK({ liberada: c.liberada, base: c.base, atualizadaEm: c.em || null, atualizadaPor: c.por || null, itens: (isAdmin() || c.liberada) ? c.itens : null, log: isAdmin() ? c.log.slice(0, 30) : null }); }
      if (name === 'salvar_calc') { if (!isComp()) return ERR('SEM_PERMISSAO'); const c = db.calc; if (a.p_itens != null && !Array.isArray(a.p_itens)) return ERR('DADOS_INVALIDOS'); if (a.p_liberada && a.p_itens == null && c.itens == null) return ERR('DADOS_INVALIDOS'); if (a.p_itens != null) c.itens = a.p_itens; if (a.p_liberada != null) c.liberada = a.p_liberada; if (a.p_base != null) c.base = a.p_base; c.em = new Date().toISOString(); c.por = nomeDe(uid()); c.log.unshift({ quando: c.em, autor: c.por, acao: a.p_acao }); save(); return OK(); }
      if (name === 'reservar') {
        const start = new Date(`${a.p_date}T${String(a.p_from).padStart(2, '0')}:00`);
        if (start <= now()) return { data: null, error: { message: 'HORARIO_PASSADO' } };
        for (let h = a.p_from; h < a.p_to; h++) if (db.slots.some(s => s.date === a.p_date && s.hour === h)) return { data: null, error: { message: 'HORARIO_OCUPADO' } };
        let dent = db.dentists.find(d => d.id === uid()); let origem = dent ? a.p_origem : (isAdmin() ? 'painel' : 'site');
        if (!isAdmin() && usaPer(a.p_from, a.p_to) && precoPer(a.p_from, a.p_to) == null) return { data: null, error: { message: 'FORA_DO_PERIODO' } };
        if (!isAdmin() && dent && (dent.termos_versao || 0) < termAtual().versao) return ERR('TERMOS_PENDENTES');
        if (!isAdmin()) { if (!dent) return { data: null, error: { message: 'LOGIN_NECESSARIO' } }; if ((dent.status || 'liberado') === 'pendente') return { data: null, error: { message: 'CONTA_PENDENTE' } }; if (dent.status === 'bloqueado') return { data: null, error: { message: 'CONTA_BLOQUEADA' } }; }
        if (a.p_dentist && isAdmin()) { dent = db.dentists.find(d => d.id === a.p_dentist); origem = 'painel'; }
        const id = uuid();
        db.bookings.push({ id, dentist_id: dent ? dent.id : null, nome: a.p_nome, cro: a.p_cro || null, tel: a.p_tel, primeira: a.p_primeira, date: a.p_date, h_from: a.p_from, h_to: a.p_to, status: 'ativo',
          origem, email: a.p_email || null, valor: precoReserva(a.p_date, a.p_from, a.p_to), pedido: a.p_pedido, serie: a.p_serie, conf_aberta_em: null, comprovante_em: null, pago: false, pago_em: null, checklist: null, avaliacao: null, criado_em: new Date().toISOString() });
        for (let h = a.p_from; h < a.p_to; h++) db.slots.push({ date: a.p_date, hour: h, booking_id: id });
        save(); db.sent.push('confirmacao'); save(); return { data: id, error: null };
      }
      if (name === 'bloquear') {
        if (!isAdmin()) return { data: null, error: { message: 'SEM_PERMISSAO' } };
        for (let h = a.p_from; h < a.p_to; h++) if (db.slots.some(s => s.date === a.p_date && s.hour === h)) return { data: null, error: { message: 'HORARIO_OCUPADO' } };
        const id = uuid();
        db.bookings.push({ id, dentist_id: null, nome: a.p_motivo || 'Horário bloqueado', cro: null, tel: '', primeira: false, date: a.p_date, h_from: a.p_from, h_to: a.p_to, status: 'ativo', origem: 'bloqueio', pago: false, criado_em: new Date().toISOString() });
        for (let h = a.p_from; h < a.p_to; h++) db.slots.push({ date: a.p_date, hour: h, booking_id: id });
        save(); return { data: id, error: null };
      }
      if (name === 'status_email') { const c = db.app_config[0] || {}; return { data: { chave: !!db.secret, email_admin: c.email_admin || null, email_remetente: c.email_remetente || null, nome_remetente: c.nome_remetente || 'Consultório Thalia Santiago', pg_net: true, pg_cron: true }, error: null }; }
      if (name === 'salvar_config_email') { db.app_config[0] = { email_admin: a.p_email_admin, email_remetente: a.p_email_remetente, nome_remetente: a.p_nome_remetente, site_url: a.p_site_url }; if (a.p_chave) db.secret = a.p_chave; save(); return { data: null, error: null }; }
      const cfgx = () => Object.assign({ valorHora: 50, limiteHoras: 3, periodos: [{ de: 8, ate: 13, valor: 180 }, { de: 13, ate: 18, valor: 180 }, { de: 18, ate: 22, valor: 180 }], diaria: { de: 8, ate: 18, valor: 350 }, precos: { porDia: {}, porHora: [] }, pacotes: [], abre: 8, fecha: 22, diasAbertos: [1, 2, 3, 4, 5, 6], prazoCancelamentoH: 4, planos: { diaria: 1000, periodo: 600 }, planoAvisoDias: 3, pix: null, pixNome: null, pixCidade: 'Ipatinga', regras: null, checklist: null, espaco: null, limiteAtrasoDias: null, lembretePagamento: true, relatorioMensal: true, agendaToken: null, taxaCancelPct: 100, profNome: null, profCro: null, profEspecialidade: null }, db.cfg || {});
      if (name === 'config_publica') { const c = cfgx(); delete c.lembretePagamento; delete c.relatorioMensal; delete c.agendaToken; return { data: c, error: null }; }
      if (name === 'config_admin') { if (!isAdmin()) return { data: null, error: { message: 'SEM_PERMISSAO' } }; return { data: cfgx(), error: null }; }
      if (name === 'salvar_ajustes') { if (!isAdmin()) return { data: null, error: { message: 'SEM_PERMISSAO' } }; const p = a.p || {}; if (p.abre != null && p.fecha != null && p.fecha <= p.abre) return { data: null, error: { message: 'DADOS_INVALIDOS' } }; db.cfg = Object.assign(cfgx(), p); if ('valorHora' in p || 'precos' in p) db.bookings.forEach(b => { if (b.valor == null && b.origem !== 'bloqueio' && b.status === 'ativo' && !b.pago) b.valor = precoReserva(b.date, b.h_from, b.h_to); }); save(); return { data: null, error: null }; }
      if (name === 'gerar_token_agenda') { if (!isAdmin()) return { data: null, error: { message: 'SEM_PERMISSAO' } }; db.cfg = Object.assign(cfgx(), { agendaToken: 'f'.repeat(64) }); save(); return { data: db.cfg.agendaToken, error: null }; }
      if (name === 'enviar_relatorio') { if (!isAdmin()) return { data: null, error: { message: 'SEM_PERMISSAO' } }; const ok = !!db.secret; if (ok) { db.sent.push('relatorio'); save(); } return { data: ok, error: null }; }
      if (name === 'excluir_dentista') { if (!isAdmin() || db.admins.includes(a.p_id)) return { data: null, error: { message: 'SEM_PERMISSAO' } }; db.dentists = db.dentists.filter(d => d.id !== a.p_id); db.users = db.users.filter(u => u.id !== a.p_id); db.bookings.forEach(b => { if (b.dentist_id === a.p_id) b.dentist_id = null; }); save(); return { data: null, error: null }; }
      if (name === 'definir_status_dentista') { if (!isAdmin()) return { data: null, error: { message: 'SEM_PERMISSAO' } }; const d = db.dentists.find(x => x.id === a.p_id); if (!d) return { data: null, error: { message: 'DENTISTA_NAO_ENCONTRADO' } }; d.status = a.p_status; d.status_em = new Date().toISOString(); db.sent.push('status-' + a.p_status); save(); return { data: null, error: null }; }
      if (name === 'push_chave_publica') return { data: db.push && db.push.url ? db.push.pub : null, error: null };
      if (name === 'push_inscrever') { if (!uid()) return { data: null, error: { message: 'SEM_PERMISSAO' } }; db.subs = (db.subs || []).filter(x => x.endpoint !== a.p_endpoint); db.subs.push({ endpoint: a.p_endpoint, user_id: uid(), p256dh: a.p_p256dh, auth: a.p_auth, aparelho: a.p_aparelho }); save(); return { data: null, error: null }; }
      if (name === 'push_cancelar') { db.subs = (db.subs || []).filter(x => !(x.endpoint === a.p_endpoint && x.user_id === uid())); save(); return { data: null, error: null }; }
      if (name === 'status_push') { if (!isAdmin()) return { data: null, error: { message: 'SEM_PERMISSAO' } }; const subs = db.subs || []; return { data: { ativo: !!(db.push && db.push.url), url: db.push && db.push.url, aparelhos: subs.length, pessoas: new Set(subs.map(x => x.user_id)).size, pg_net: true }, error: null }; }
      if (name === 'salvar_config_push') { if (!isAdmin()) return { data: null, error: { message: 'SEM_PERMISSAO' } }; if (!/^[A-Za-z0-9_-]{87}$/.test(a.p_publica) || !/^[A-Za-z0-9_-]{43}$/.test(a.p_privada)) return { data: null, error: { message: 'DADOS_INVALIDOS' } }; if (!db.push || db.push.pub !== a.p_publica) db.subs = []; db.push = { pub: a.p_publica, priv: a.p_privada, url: a.p_url }; save(); return { data: null, error: null }; }
      if (name === 'testar_push') { const n = (db.subs || []).filter(x => x.user_id === uid()).length; if (n) { db.pushes = (db.pushes || []).concat([{ to: uid(), title: 'Notificações ativadas' }]); save(); } return { data: n, error: null }; }
      if (name === 'testar_email') { const c = db.app_config[0] || {}; const ok = !!(db.secret && c.email_remetente && c.email_admin); if (ok) { db.sent.push('teste'); save(); } return { data: ok, error: null }; }
      if (name === 'cancelar') {
        const b = db.bookings.find(x => x.id === a.p_id);
        if (!uid()) return { data: null, error: { message: 'SEM_PERMISSAO' } };
        if (!isAdmin()) {
          if (b.dentist_id !== uid()) return { data: null, error: { message: 'SEM_PERMISSAO' } };
          if (b.plano_id) return ERR('PLANO_USE_CREDITO');
          if (new Date(`${b.date}T${String(b.h_from).padStart(2, '0')}:00`) - now() < (cfgx().prazoCancelamentoH) * 36e5) return { data: null, error: { message: 'FORA_DO_PRAZO' } };
        }
        b.status = 'cancelado'; db.slots = db.slots.filter(s => s.booking_id !== b.id); save(); return { data: null, error: null };
      }
      if (name === 'cancelar_com_taxa') { if (!isAdmin()) return ERR('SEM_PERMISSAO'); const b = db.bookings.find(x => x.id === a.p_id); if (!b || b.status !== 'ativo' || b.origem === 'bloqueio') return ERR('DADOS_INVALIDOS'); const v = Math.round((b.valor || 0) * a.p_pct) / 100; b.valor_original = b.valor; b.valor = v; b.status = 'taxa'; b.taxa_em = new Date().toISOString(); db.slots = db.slots.filter(x => x.booking_id !== b.id); save(); return { data: v, error: null }; }
      if (name === 'marcar_falta') { if (!isAdmin()) return ERR('SEM_PERMISSAO'); const b = db.bookings.find(x => x.id === a.p_id); if (!b) return ERR('RESERVA_NAO_ENCONTRADA'); b.falta = !!a.p_falta; save(); return { data: null, error: null }; }
      if (name === 'salvar_cfg_v8') { if (!isComp() && a.p && ('profCro' in a.p || 'profNome' in a.p || 'profEspecialidade' in a.p)) return ERR('SEM_PERMISSAO'); if (!isAdmin()) return ERR('SEM_PERMISSAO'); const p = a.p || {}; if (p.taxaCancelPct != null && (p.taxaCancelPct < 0 || p.taxaCancelPct > 100)) return ERR('DADOS_INVALIDOS'); db.cfg = Object.assign(cfgx(), p); save(); return { data: null, error: null }; }
      if (name === 'termos_atual') { const t = termAtual(); return { data: { versao: t.versao, texto: t.texto, resumo: t.resumo, criadoEm: t.criado_em }, error: null }; }
      if (name === 'aceitar_termos') { const d = db.dentists.find(x => x.id === uid()); if (!d) return ERR('SEM_PERMISSAO'); if (a.p_versao !== termAtual().versao) return ERR('TERMOS_DESATUALIZADOS'); if (!db.termos_aceites.some(x => x.dentist_id === d.id && x.versao === a.p_versao)) db.termos_aceites.push({ id: uuid(), dentist_id: d.id, versao: a.p_versao, aceito_em: new Date().toISOString() }); d.termos_versao = a.p_versao; d.termos_aceito_em = new Date().toISOString(); save(); return { data: null, error: null }; }
      if (name === 'salvar_termos') { if (!isAdmin()) return ERR('SEM_PERMISSAO'); const t = termAtual(), tx = String(a.p_texto || '').trim(); if (tx.length < 20) return ERR('DADOS_INVALIDOS'); if (t.texto === tx) return { data: t.versao, error: null }; const v = t.versao + 1; db.termos_versoes.push({ id: 'tv' + v, versao: v, texto: tx, resumo: a.p_resumo || null, criado_em: new Date().toISOString() }); save(); return { data: v, error: null }; }
      if (name === 'pedir_plano') { const d = db.dentists.find(x => x.id === uid()); if (!d) return ERR('LOGIN_NECESSARIO'); if ((d.status || 'liberado') === 'pendente') return ERR('CONTA_PENDENTE'); if ((d.termos_versao || 0) < termAtual().versao) return ERR('TERMOS_PENDENTES'); const p = novoPlano(d.id, a, 'pendente'); if (typeof p === 'string') return ERR(p); db.sent.push('pedido-plano'); save(); return { data: p.id, error: null }; }
      if (name === 'criar_plano') { if (!isAdmin()) return ERR('SEM_PERMISSAO'); const p = novoPlano(a.p_dentist, a, 'ativo'); if (typeof p === 'string') return ERR(p); return { data: Object.assign(gerar(p), { id: p.id }), error: null }; }
      if (name === 'aprovar_plano') { if (!isAdmin()) return ERR('SEM_PERMISSAO'); const p = db.planos.find(x => x.id === a.p_id); if (!p) return ERR('PLANO_NAO_ENCONTRADO'); if (p.status !== 'pendente') return ERR('PLANO_JA_DECIDIDO'); p.status = 'ativo'; p.aprovado_em = new Date().toISOString(); save(); return { data: gerar(p), error: null }; }
      if (name === 'recusar_plano') { if (!isAdmin()) return ERR('SEM_PERMISSAO'); const p = db.planos.find(x => x.id === a.p_id && x.status === 'pendente'); if (!p) return ERR('PLANO_JA_DECIDIDO'); p.status = 'recusado'; p.obs = a.p_motivo || null; p.encerrado_em = new Date().toISOString(); save(); return { data: null, error: null }; }
      if (name === 'encerrar_plano') { const p = db.planos.find(x => x.id === a.p_id); if (!p) return ERR('PLANO_NAO_ENCONTRADO'); if (!isAdmin() && p.dentist_id !== uid()) return ERR('SEM_PERMISSAO'); if (!['pendente', 'ativo'].includes(p.status)) return ERR('PLANO_JA_DECIDIDO'); if (p.status === 'ativo') { const t = now(), fim = isoD(new Date(t.getFullYear(), t.getMonth() + 1, 0, 12)); p.fim = fim; db.bookings.forEach(b => { if (b.plano_id === p.id && (b.plano_data_orig || b.date) > fim && ['ativo', 'credito'].includes(b.status) && !b.pago) { b.status = 'cancelado'; db.slots = db.slots.filter(s => s.booking_id !== b.id); } }); } p.status = 'encerrado'; p.encerrado_em = new Date().toISOString(); save(); return { data: null, error: null }; }
      if (name === 'plano_liberar_dia') { const b = db.bookings.find(x => x.id === a.p_booking); if (!b || !b.plano_id || b.status !== 'ativo') return ERR('DADOS_INVALIDOS'); const st = new Date(`${b.date}T${String(b.h_from).padStart(2, '0')}:00`); if (st <= now()) return ERR('HORARIO_PASSADO'); if (!isAdmin()) { if (b.dentist_id !== uid()) return ERR('SEM_PERMISSAO'); if (st - now() < cfgPl().planoAvisoDias * 864e5) return ERR('PLANO_PRAZO_CREDITO'); } b.status = 'credito'; db.slots = db.slots.filter(s => s.booking_id !== b.id); save(); return { data: null, error: null }; }
      if (name === 'plano_usar_credito') { const b = db.bookings.find(x => x.id === a.p_booking); if (!b || !b.plano_id || b.status !== 'credito') return ERR('DADOS_INVALIDOS'); if (!isAdmin() && b.dentist_id !== uid()) return ERR('SEM_PERMISSAO'); const p = db.planos.find(x => x.id === b.plano_id) || { modalidade: 'periodo' }; if (a.p_date.slice(0, 7) !== (b.plano_data_orig || b.date).slice(0, 7)) return ERR('PLANO_MES_CREDITO'); if (!horasOk(p.modalidade, a.p_from, a.p_to)) return ERR('HORARIO_INVALIDO'); if (new Date(`${a.p_date}T${String(a.p_from).padStart(2, '0')}:00`) <= now()) return ERR('HORARIO_PASSADO'); if (busy(a.p_date, a.p_from, a.p_to)) return ERR('HORARIO_OCUPADO'); Object.assign(b, { date: a.p_date, h_from: a.p_from, h_to: a.p_to, status: 'ativo' }); for (let h = a.p_from; h < a.p_to; h++) db.slots.push({ date: a.p_date, hour: h, booking_id: b.id }); save(); return { data: null, error: null }; }
      if (name === 'salvar_planos_cfg') { if (!isAdmin()) return ERR('SEM_PERMISSAO'); db.cfg = Object.assign(cfgx(), { planos: { diaria: a.p_diaria, periodo: a.p_periodo }, planoAvisoDias: a.p_aviso }); save(); return { data: null, error: null }; }
      return { data: null, error: { message: 'rpc desconhecida' } };
    }
    const setSession = s => { session = s; SV('mocksess', s); };
    const auth = {
      async getSession() { return { data: { session }, error: null }; },
      async signInWithPassword({ email, password }) {
        const u = db.users.find(x => x.email === email && x.password === password);
        if (!u) return { data: {}, error: { message: 'Invalid login credentials' } };
        setSession({ user: { id: u.id, email } }); setTimeout(() => emit('SIGNED_IN'), 0); return { data: { session }, error: null };
      },
      async signUp({ email, password, options }) {
        if (db.users.some(x => x.email === email)) return { data: {}, error: { message: 'User already registered' } };
        const id = uuid(); db.users.push({ id, email, password });
        const m = options.data || {};
        if (m.whatsapp && !db.termos_versoes.some(v => String(v.versao) === String(m.termos_versao))) { db.users.pop(); return { data: {}, error: { message: 'Database error saving new user' } }; }
        if (m.whatsapp) db.termos_aceites.push({ id: uuid(), dentist_id: id, versao: Number(m.termos_versao), aceito_em: new Date().toISOString() });
        if (m.whatsapp) db.dentists.push({ termos_versao: Number(m.termos_versao), termos_aceito_em: new Date().toISOString(), id, nome: m.nome, cro: m.cro || null, whatsapp: m.whatsapp, email, especialidade: m.especialidade || null, regras_aceitas_em: m.regras_aceitas_em ? new Date().toISOString() : null, status: 'pendente', criado_em: new Date().toISOString() });
        save(); setSession({ user: { id, email } }); setTimeout(() => emit('SIGNED_IN'), 0);
        return { data: { session, user: session.user }, error: null };
      },
      async signOut() { setSession(null); setTimeout(() => emit('SIGNED_OUT'), 0); return { error: null }; },
      async resetPasswordForEmail() { return { data: {}, error: null }; },
      async updateUser({ password }) { const u = db.users.find(x => x.id === uid()); if (u) u.password = password; save(); return { data: {}, error: null }; },
      onAuthStateChange(f) { listeners.push(f); return { data: { subscription: { unsubscribe() {} } } }; }
    };
    const toUrl = blob => new Promise(res => { const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(blob); });
    const storage = { from(bucket) { return {
      async list() { return { data: (db.files[bucket] || []).map(f => ({ name: f.name })), error: null }; },
      async upload(path, blob) { if ((bucket === 'fotos' && !isAdmin()) || (bucket === 'pacientes' && !isComp())) return { error: { message: 'permission' } }; db.files[bucket].push({ name: path, url: await toUrl(blob) }); save(); return { data: { path }, error: null }; },
      async remove(paths) { db.files[bucket] = db.files[bucket].filter(f => !paths.includes(f.name)); save(); return { data: null, error: null }; },
      getPublicUrl(name) { const f = db.files[bucket].find(x => x.name === name); return { data: { publicUrl: f ? f.url : '' } }; },
      async createSignedUrl(path) { const f = db.files[bucket].find(x => x.name === path); return { data: f ? { signedUrl: f.url } : null, error: null }; }
    }; } };
    return { from, rpc, auth, storage, channel() { const c = { on() { return c; }, subscribe() { return c; } }; return c; } };
  }
  window.supabase = { createClient };
})();
