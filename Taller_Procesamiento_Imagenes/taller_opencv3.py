"""Control 2: puntos 1, 2, 6, 7, 9 y 10. Ejecutar: python taller_opencv3.py

Procesamiento offline; no envia ordenes a motores. Coordenadas x derecha, y abajo.
No requiere camara ni GUI. Entradas y resultados relativos a este archivo.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import platform
import sys
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
K = np.ones((3, 3), np.uint8)
SOBEL_X = np.array([[-1,0,1],[-2,0,2],[-1,0,1]], np.float32)

CARPETAS = (
    '01_pruebas_artificiales', '02_imagenes_video',
    '03_video_linea_central', '04_mascaras_y_distancias',
    '05_control_pwm', '06_fourier_video', '07_datos'
)

def ruta_salida(out, nombre):
    """Clasifica cada resultado; conserva los nombres originales de archivo."""
    if nombre.startswith(('09_', 'artificial_')) or nombre in ('circulo.npz', 'cuadrado.npz', 'linea_inclinada.npz'):
        carpeta = CARPETAS[0]
    elif nombre.startswith('cuadro_') and nombre.endswith('.png'):
        carpeta = CARPETAS[1]
    elif (nombre.startswith('centros_') and nombre.endswith('.png')) or nombre.startswith('02_contacto_'):
        carpeta = CARPETAS[2]
    elif nombre.startswith('06_'):
        carpeta = CARPETAS[3]
    elif nombre.startswith('07_'):
        carpeta = CARPETAS[4]
    elif nombre.startswith('10_') or nombre.endswith('.npz'):
        carpeta = CARPETAS[5]
    elif nombre.endswith(('.csv', '.json')):
        carpeta = CARPETAS[6]
    else:
        raise ValueError(f'Tipo de resultado no reconocido: {nombre}')
    return out / carpeta / nombre

def write_csv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def lane(binary):
    """Mayor componente que llega al 20% inferior; seguimiento por filas.

    Apertura/cierre 3x3, ROI y>=0.25H. Descarta tramos cortados por los
    laterales, anchos <3 o >0.65W, y saltos de centro >0.12W.
    """
    h,w = binary.shape
    clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN, K, borderType=cv2.BORDER_REPLICATE)
    clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, K, borderType=cv2.BORDER_REPLICATE)
    clean[:int(.25*h)] = 0
    n, labels, stats, _ = cv2.connectedComponentsWithStats(clean)
    candidates = [i for i in range(1,n) if np.any(labels[int(.8*h):] == i)]
    mask = np.zeros_like(clean)
    if candidates:
        chosen = max(candidates, key=lambda i: stats[i,cv2.CC_STAT_AREA])
        mask[labels == chosen] = 255
    gx = cv2.filter2D(mask.astype(np.float32)/255, -1, SOBEL_X,
                      borderType=cv2.BORDER_REPLICATE)
    border = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, K,
                             borderType=cv2.BORDER_REPLICATE)
    rows = []; previous = None
    for y in range(h-2,int(.25*h)-1,-1):
        xs = np.flatnonzero(mask[y]); groups = np.split(xs,np.where(np.diff(xs)>1)[0]+1)
        segments = [g for g in groups if 3<=len(g)<=.65*w and g[0]>0 and g[-1]<w-1]
        if not segments: continue
        g = min(segments,key=lambda a: abs((a[0]+a[-1])/2-(previous if previous is not None else (w-1)/2)))
        l,r = int(g[0]),int(g[-1]); c = (l+r)/2
        if previous is not None and abs(c-previous)>.12*w: continue
        # Comprueba respuesta de la mascara 3x3 alrededor de ambas transiciones.
        if np.max(gx[y,max(0,l-1):l+2])<=0 or np.min(gx[y,r-1:min(w,r+2)])>=0: continue
        previous = c
        xs_all = np.flatnonzero(mask[y])
        rows.append(dict(y=y,izquierda_px=l,derecha_px=r,ancho_px=r-l+1,
                         centro_bordes_px=c,centro_momento_px=float(xs_all.mean()),
                         error_px=c-(w-1)/2,dist_izquierda_px=(w-1)/2-l,
                         dist_derecha_px=r-(w-1)/2))
    return mask, border, gx, rows

def ajustar_recta(rows, h, w):
    """Investigacion punto 5: minimos cuadrados ortogonales (DIST_L2).

    Ajuste local entre 65% y 90% H; centro de control evaluado en 80% H.
    Requiere cobertura alrededor de la fila objetivo; no extrapola.
    """
    near = [r for r in rows if .65*h <= r['y'] <= .9*h]
    if len(near) < .15*h:
        return None
    points = np.array([[r['centro_bordes_px'], r['y']] for r in near], dtype=np.float32)
    yref = .8*h
    if not points[:,1].min() <= yref <= points[:,1].max():
        return None
    vx, vy, x0, y0 = map(float, cv2.fitLine(points, cv2.DIST_L2, 0, .01, .01).ravel())
    if abs(vy) < 1e-6:
        return None
    if vy < 0: vx, vy = -vx, -vy
    xref = x0 + (yref-y0)*vx/vy
    if not 0 <= xref < w: return None
    residual = (points[:,0]-x0)*vy - (points[:,1]-y0)*vx
    return dict(vx=vx, vy=vy, x0=x0, y0=y0, fila_referencia_px=yref,
                centro_recta_px=xref, error_recta_px=xref-(w-1)/2,
                rmse_ortogonal_px=float(np.sqrt(np.mean(residual**2))),
                filas_ajuste=len(near), y_min=float(points[:,1].min()), y_max=float(points[:,1].max()))

def curvature(rows,h):
    if len(rows)<.3*h: return 0.
    y=np.array([r['y'] for r in rows])/h; x=np.array([r['centro_bordes_px'] for r in rows])
    coef=np.polyfit(y,x,2)
    return float(abs(coef[0])*(y.max()-y.min())**2/4)

def pwm(error, valid, width, base=110., kp=70.):
    if not valid: return 0.,0.
    e=error/((width-1)/2)
    speed=base*(1-.5*min(abs(e),1))
    return float(np.clip(speed+kp*e,0,255)),float(np.clip(speed-kp*e,0,255))

def panel(path, arrays, titles, cmaps=None, cols=3):
    fig,axs=plt.subplots(int(np.ceil(len(arrays)/cols)),cols,figsize=(4*cols,3.15*int(np.ceil(len(arrays)/cols))),squeeze=False)
    for ax,a,t,c in zip(axs.flat,arrays,titles,cmaps or ['gray']*len(arrays)):
        im=ax.imshow(a,cmap=c); ax.set_title(t,fontsize=10); ax.axis('off')
        if c in ('twilight','magma','coolwarm'): fig.colorbar(im,ax=ax,fraction=.035,pad=.02)
    for ax in list(axs.flat)[len(arrays):]: ax.axis('off')
    fig.tight_layout(); fig.savefig(path,dpi=150); plt.close(fig)

def fourier_figures(out):
    shapes={}; n=256
    for name in ['circulo','cuadrado','linea_inclinada']:
        a=np.zeros((n,n),np.uint8)
        if name=='circulo': cv2.circle(a,(128,128),45,255,-1)
        elif name=='cuadrado': cv2.rectangle(a,(83,83),(173,173),255,-1)
        else: cv2.line(a,(48,200),(205,50),255,3)
        cv2.imwrite(str(ruta_salida(out, f'artificial_{name}.png')), a)
        f=np.fft.fft2(a/255.); mag=abs(f); phase=np.angle(f)
        valid=mag>mag.max()*1e-6
        phase_vis=np.where(np.fft.fftshift(valid),np.fft.fftshift(phase),np.nan)
        np.savez_compressed(ruta_salida(out, f'{name}.npz'),imagen=a,magnitud=mag,fase=phase,fase_valida=valid)
        panel(ruta_salida(out, f'09_{name}.png'),[a,np.log1p(np.fft.fftshift(mag)),phase_vis],
              [name.replace('_',' '),'log(1 + magnitud)','Fase [rad]; ceros en blanco'],['gray','magma','twilight'])
        shapes[name]=a
    # Ejemplo exacto separado de las mediciones del video: traslacion circular.
    a=shapes['cuadrado']/255.; b=np.roll(a,17,axis=1)
    fa,fb=np.fft.fft2(a),np.fft.fft2(b)
    # Fase relativa en frecuencias positivas: pendiente conocida -2*pi*17/N.
    k=np.arange(0,100); wrapped=np.angle(fb[0,k]*np.conj(fa[0,k])); unwrapped=np.unwrap(wrapped)
    fig,ax=plt.subplots(figsize=(9,3)); ax.plot(k,wrapped,label='Fase relativa envuelta'); ax.plot(k,unwrapped,label='np.unwrap, eje u'); ax.set(xlabel='Frecuencia u [indice DFT]',ylabel='Fase [rad]'); ax.legend(); fig.tight_layout(); fig.savefig(ruta_salida(out, '09_unwrap.png'),dpi=150); plt.close(fig)
    return float(np.max(abs(abs(fa)-abs(fb))))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--video',type=Path,default=BASE/'resultados/taller2/clip_original_otsu_inv.mp4')
    ap.add_argument('--out',type=Path,default=BASE/'taller3_opencv')
    args=ap.parse_args(); out=args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for carpeta in CARPETAS:
        (out / carpeta).mkdir(exist_ok=True)
    cap=cv2.VideoCapture(str(args.video))
    if not cap.isOpened(): raise ValueError(f'No se puede abrir {args.video}')
    fps=cap.get(cv2.CAP_PROP_FPS)
    if not np.isfinite(fps) or fps<=0: raise ValueError('FPS no valido')
    frames=[]; scores=[]; coverage=[]
    while True:
        ok,bgr=cap.read()
        if not ok: break
        # El video ya es Otsu-inverso. 127 solo elimina grises de compresion.
        b=(cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)>127).astype(np.uint8)*255
        frames.append(b); _,_,_,rows=lane(b); scores.append(curvature(rows,b.shape[0])); coverage.append(len(rows))
    cap.release()
    if len(frames)<40: raise ValueError('Se requieren al menos 40 cuadros reales')
    h,w=frames[0].shape
    # 20 muestras uniformes + 20 con mayor desviacion cuadratica (proxy de curva).
    chosen=set(np.linspace(0,len(frames)-1,20,dtype=int).tolist())
    curve_indices=[]
    for i in np.argsort(-np.asarray(scores),kind='stable'):
        i=int(i)
        if len(chosen)>=40: break
        if all(abs(i-j)>=3 for j in chosen): chosen.add(i); curve_indices.append(i)
    if len(chosen)<40:
        for i in range(len(frames)):
            chosen.add(i)
            if len(chosen)==40: break
    ids=sorted(chosen); manifest=[]; allrows=[]; summary=[]; overlays=[]; spectra={}; ajustes=[]
    for i in ids:
        a=frames[i]; mask,border,gx,rows=lane(a)
        f=np.fft.fft2(a/255.); spectra[i]=f
        np.savez_compressed(ruta_salida(out, f'cuadro_{i:04d}.npz'),magnitud=abs(f),fase=np.angle(f))
        cv2.imwrite(str(ruta_salida(out, f'cuadro_{i:04d}.png')),a)
        plot=cv2.cvtColor(a,cv2.COLOR_GRAY2BGR)
        cv2.line(plot,((w-1)//2,0),((w-1)//2,h-1),(255,160,0),1)
        for r in rows:
            allrows.append(dict(cuadro=i,tiempo_s=i/fps,**r))
            cv2.circle(plot,(round(r['centro_bordes_px']),r['y']),1,(0,145,255),-1)
        # Banda cercana: 65%-90% H; referencia de distancia y control.
        near=[r for r in rows if .65*h<=r['y']<=.9*h]
        mean_error=float(np.mean([r['error_px'] for r in near])) if near else None
        fit=ajustar_recta(rows,h,w)
        valid=fit is not None
        err=fit['error_recta_px'] if valid else None
        ajustes.append(dict(cuadro=i,**(fit or {k:None for k in ['vx','vy','x0','y0','fila_referencia_px','centro_recta_px','error_recta_px','rmse_ortogonal_px','filas_ajuste','y_min','y_max']})))
        if valid:
            endpoints=[(round(fit['x0']+(y-fit['y0'])*fit['vx']/fit['vy']),round(y)) for y in [fit['y_min'],fit['y_max']]]
            visible,p1,p2=cv2.clipLine((0,0,w,h),*endpoints)
            if visible: cv2.line(plot,p1,p2,(0,220,0),2)
            cv2.circle(plot,(round(fit['centro_recta_px']),round(fit['fila_referencia_px'])),4,(255,0,255),-1)
        cv2.putText(plot,'L2: verde | centros: naranja',(5,h-7),cv2.FONT_HERSHEY_SIMPLEX,.35,(0,220,0),1)
        pl,pr=pwm(err or 0,valid,w)
        disagreement=float(np.mean([abs(r['centro_bordes_px']-r['centro_momento_px']) for r in rows])) if rows else None
        # Distancia euclidiana al borde mas cercano desde centro de banda.
        dist=cv2.distanceTransform(255-border,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        summary.append(dict(cuadro=i,tiempo_s=i/fps,filas_validas=len(rows),curva_proxy_px=scores[i],
                            error_medio_px=mean_error,error_control_recta_px=err,rmse_ajuste_px=fit['rmse_ortogonal_px'] if valid else None,dist_borde_euclidiana_px=float(dist[round(.8*h),(w-1)//2]) if rows else None,
                            diferencia_metodos_px=disagreement,pwm_izquierdo_propuesto=pl,pwm_derecho_propuesto=pr,
                            estado='propuesta_recta_L2_offline' if valid else 'sin_ajuste_parar',distancia_cm='SIN_CALIBRACION'))
        cv2.putText(plot,f'frame {i}  e={err:.1f}px' if valid else f'frame {i} SIN LINEA',(5,16),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,120,255),1)
        cv2.imwrite(str(ruta_salida(out, f'centros_{i:04d}.png')),plot)
        overlays.append(cv2.cvtColor(plot,cv2.COLOR_BGR2RGB))
        manifest.append(dict(cuadro=i,tiempo_s=i/fps,seleccion='curva' if i in curve_indices else 'uniforme',curva_proxy_px=scores[i],archivo=ruta_salida(out, f'cuadro_{i:04d}.png').relative_to(out).as_posix()))
    write_csv(ruta_salida(out, 'ajustes_recta.csv'),ajustes)
    write_csv(ruta_salida(out, 'seleccion_40.csv'),manifest); write_csv(ruta_salida(out, 'centros_por_fila.csv'),allrows); write_csv(ruta_salida(out, 'resultados_40.csv'),summary)
    write_csv(ruta_salida(out, 'exploracion_458.csv'),[dict(cuadro=i,curva_proxy_px=scores[i],filas_validas=coverage[i]) for i in range(len(frames))])
    for start in [0,20]:
        panel(ruta_salida(out, f'02_contacto_{start//20+1}.png'),overlays[start:start+20],[f'Cuadro {i} | {i/fps:.2f} s' for i in ids[start:start+20]],cols=4)
    sample=max(ids,key=lambda i:scores[i]); mask,border,gx,rows=lane(frames[sample])
    panel(ruta_salida(out, '06_mascaras.png'),[frames[sample],mask,border,gx,overlays[ids.index(sample)],cv2.distanceTransform(255-border,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)],
          [f'Otsu-inverso: cuadro {sample}','Componente + ROI','Borde: gradiente 3x3','Respuesta Sobel X 3x3','Centros + ajuste local L2','Distancia al borde [px]'],['gray','gray','gray','coolwarm','gray','magma'])
    fig,axs=plt.subplots(2,1,figsize=(10,6),sharex=True)
    axs[0].plot([r['tiempo_s'] for r in summary],[r['error_control_recta_px'] if r['error_control_recta_px'] is not None else np.nan for r in summary],'.-'); axs[0].axhline(0,color='gray'); axs[0].set_ylabel('Error recta L2 en y=0.8H [px]')
    for name in ['izquierdo','derecho']: axs[1].plot([r['tiempo_s'] for r in summary],[r[f'pwm_{name}_propuesto'] for r in summary],'.-',label=name)
    axs[1].set(xlabel='Tiempo en clip [s]',ylabel='PWM propuesto [0-255]'); axs[1].legend(); fig.tight_layout(); fig.savefig(ruta_salida(out, '07_control.png'),dpi=150); plt.close(fig)
    mag_error=fourier_figures(out)
    # Par de cuadros elegido entre los extraidos, al menos cuatro indices aparte.
    pairs=[(a,b) for a in ids for b in ids if b-a>=4]
    i,j=min(pairs,key=lambda p:(p[1]-p[0],-scores[p[0]]))
    fi,fj=spectra[i],spectra[j]; mi,mj=abs(fi),abs(fj)
    eps=1e-6*max(float(mj.max()),1.); supported=mj>eps
    ratio=np.zeros_like(mi); np.divide(mi,mj,out=ratio,where=supported)
    raw_phase=np.angle(fi)-np.angle(fj); delta=np.angle(fi*np.conj(fj))
    transfer=ratio*np.exp(1j*delta); inv=np.fft.ifft2(transfer)
    reconstructed=np.fft.ifft2(transfer*fj).real
    # Correlacion de fase: i -> j. Pico circular y estimacion subpixel de OpenCV.
    cross=fj*np.conj(fi); support_cross=abs(cross)>1e-12*max(float(abs(cross).max()),1.)
    cross_norm=np.divide(cross,abs(cross),out=np.zeros_like(cross),where=support_cross)
    corr=np.fft.ifft2(cross_norm).real; peak=np.unravel_index(np.argmax(corr),corr.shape)
    dy=int(peak[0] if peak[0]<=h//2 else peak[0]-h); dx=int(peak[1] if peak[1]<=w//2 else peak[1]-w)
    window=cv2.createHanningWindow((w,h),cv2.CV_64F)
    shift,response=cv2.phaseCorrelate(frames[i].astype(np.float64)/255,frames[j].astype(np.float64)/255,window)
    np.savez_compressed(ruta_salida(out, 'operaciones_par.npz'),i=i,j=j,magnitud_cociente=ratio,frecuencias_validas=supported,
                        fase_diferencia_directa=raw_phase,fase_diferencia_envuelta=delta,espectro_cociente=transfer,
                        inversa_compleja=inv,reconstruccion_i=reconstructed,correlacion_fase=corr)
    panel(ruta_salida(out, '10_par.png'),[frames[i],frames[j],np.log1p(np.fft.fftshift(ratio)),np.fft.fftshift(delta),np.fft.fftshift(inv.real),np.fft.fftshift(corr)],
          [f'Cuadro i={i}',f'Cuadro j={j}','log(1 + Mi/Mj), regularizado','Fase i - fase j, envuelta [rad]','Re{IFFT(cociente)}','Correlacion de fase j respecto a i'],['gray','gray','magma','twilight','coolwarm','magma'])
    for start in [0,20]:
        imgs=[]; titles=[]
        for idx in ids[start:start+20]:
            f=spectra[idx]; imgs.extend([np.log1p(np.fft.fftshift(abs(f))),np.fft.fftshift(np.angle(f))]); titles.extend([f'{idx}: log magnitud',f'{idx}: fase [rad]'])
        panel(ruta_salida(out, f'10_espectros_{start//20+1}.png'),imgs,titles,['magma','twilight']*20,cols=4)
    info=dict(video=str(args.video.resolve()),sha256=digest(args.video),fps=fps,cuadros_decodificados=len(frames),ancho=w,alto=h,
              seleccion=ids,curvas=curve_indices,ejemplo=sample,par=[i,j],separacion_s=(j-i)/fps,
              fraccion_frecuencias_descartadas=float(1-supported.mean()),epsilon=eps,
              error_reconstruccion_rmse=float(np.sqrt(np.mean((reconstructed-frames[i]/255.)**2))),
              residuo_imaginario_max=float(abs(inv.imag).max()),desplazamiento_pico_px=[dx,dy],
              desplazamiento_hann_px=list(shift),respuesta_hann=float(response),
              invariancia_magnitud_sintetica_error=mag_error,
              python=platform.python_version(),opencv=cv2.__version__,numpy=np.__version__,matplotlib=matplotlib.__version__,
              metodo_control='fitLine DIST_L2: minimos cuadrados ortogonales, investigacion punto 5',fila_control_fraccion=.8,calibracion='NO DISPONIBLE',motores='NO ENSAYADOS',parametros=dict(roi_y=.25,banda_control=[.65,.9],kernel='3x3',kp=70,pwm_base=110))
    (ruta_salida(out, 'ejecucion.json')).write_text(json.dumps(info,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Listo. Imagenes y resultados guardados en: {out}')
    print('40 cuadros originales, 40 cuadros con centros y figuras de mascaras, control y Fourier. No se genera PDF.')

if __name__=='__main__': main()
