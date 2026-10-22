import re,subprocess
import os; D = os.path.dirname(os.path.abspath(__file__)) + '/'
q=lambda f: open(D+f).read().replace('width="400" height="400"','width="100%" height="100%" style="display:block"')
for s in ('manual','cartaz'):
    h=open(D+s+'.html').read()
    h=h.replace('<span class="k">Baixar recibo do mês (PDF)</span>','<span class="k">Baixar recibo de [mês] (PDF)</span>')
    h=h.replace('<li>O recibo de cada reserva paga fica nos detalhes dela.</li>','<li>Cada reserva paga também tem o botão <span class="k">Baixar comprovante</span> nos detalhes dela.</li>')
    h=h.replace('%QRSITE%',q('qr-site.svg')).replace('%QRWA%',q('qr-wa.svg')).replace('%CK%','<svg viewBox="0 0 24 24"><path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke="#590117" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>')
    open(D+s+'_b.html','w').write(h)
    subprocess.run(['python3',D+'mk.py',s+'_b.html',s+'.pdf'],check=True)
