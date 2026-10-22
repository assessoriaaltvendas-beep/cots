const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync(__dirname+'/../app/util5.js','utf8');
const end=src.indexOf('/* Pix copia e cola');
const ctx={TextEncoder};vm.createContext(ctx);vm.runInContext(src.slice(0,end)+';this.QR=QR;',ctx);
const mk=(t,f)=>fs.writeFileSync(__dirname+'/'+f,ctx.QR.svg(t,400).replace('aria-label="QR Code do Pix"','aria-label="QR Code"').replace(/#1f1416/,'#2a0610'));
mk('https://dra-thalia-santiago.vercel.app','qr-site.svg');
mk('https://wa.me/5531995745413','qr-wa.svg');
console.log('ok');
