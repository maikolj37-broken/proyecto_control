"""Nucleo reutilizado de taller_opencv3.py: lane, ajustar_recta y pwm.
Funciones copiadas sin cambios del taller; sin generadores offline ni matplotlib.
"""
import cv2
import numpy as np

K = np.ones((3, 3), np.uint8)
SOBEL_X = np.array([[-1,0,1],[-2,0,2],[-1,0,1]], np.float32)

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

def pwm(error, valid, width, base=110., kp=70.):
    if not valid: return 0.,0.
    e=error/((width-1)/2)
    speed=base*(1-.5*min(abs(e),1))
    return float(np.clip(speed+kp*e,0,255)),float(np.clip(speed-kp*e,0,255))
