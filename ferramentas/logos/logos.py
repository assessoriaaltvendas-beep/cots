import numpy as np
from PIL import Image
O='/home/claude/logos-novos/'
def cut(src, light_on_dark, white=False):
    a=np.asarray(Image.open(O+'originais/'+src).convert('RGB')).astype(float)
    h,w,_=a.shape
    # fundo = mediana das bordas
    border=np.concatenate([a[:20].reshape(-1,3),a[-20:].reshape(-1,3),a[:,:20].reshape(-1,3),a[:,-20:].reshape(-1,3)])
    B=np.median(border,axis=0)
    L=lambda x: x[...,0]*.299+x[...,1]*.587+x[...,2]*.114
    lb=L(B); lp=L(a)
    if light_on_dark:
        fg_l=np.percentile(lp[lp>lb+60],12)
        al=(lp-lb)/(fg_l-lb)
    else:
        fg_l=np.percentile(lp[lp<lb-60],5)
        al=(lb-lp)/(lb-fg_l)
    al=np.clip(al,0,1)
    al[al<0.06]=0
    al=np.clip((al-0.06)/0.94,0,1)
    safe=np.maximum(al,1e-3)[...,None]
    col=np.clip((a-(1-safe)*B)/safe,0,255)
    if not light_on_dark:
        # cor vinho sólida (evita franjas)
        m=al>0.7; col[:]=np.median(a[m],axis=0) if m.any() else col
    if white: col[:]=255
    rgba=np.dstack([col,al*255]).astype(np.uint8)
    im=Image.fromarray(rgba,'RGBA'); bb=im.getbbox(); im=im.crop(bb)
    return im,B,bb
res={}
for src,name,lod in [('logo-dourado-fundo-vinho.png','dourado',True),('logo-branco-fundo-vinho.png','branco',True),('logo-vinho-fundo-branco.png','vinho',False)]:
    im,B,bb=cut(src,lod,name=='branco'); res[name]=(im,bb)
    im.save(O+f'logo-{name}-transparente.png',optimize=True)
    print(name,im.size,'fundo',B.round(),bb)

# ---- tamanhos para o site ----
A='/home/claude/logos-novos/site/'; import os; os.makedirs(A,exist_ok=True)
for name in ('dourado','vinho','branco'):
    im=Image.open(O+f'logo-{name}-transparente.png')
    w=900; r=im.resize((w,round(w*im.height/im.width)),Image.LANCZOS)
    r.save(A+f'logo-{name}.webp',quality=92,method=6)
# ---- dente (ícone) a partir do logo dourado ----
g=np.asarray(Image.open(O+'originais/logo-dourado-fundo-vinho.png').convert('RGB')).astype(float)
crop=Image.open(O+'logo-dourado-transparente.png')
print('ok')
