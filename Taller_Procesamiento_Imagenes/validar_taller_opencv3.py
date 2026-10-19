"""Pruebas de geometria, perdida de linea, signo del control y desplazamiento."""
import numpy as np
import cv2
from taller_opencv3 import lane,pwm,ajustar_recta

def main():
    a=np.zeros((240,320),np.uint8); a[:,100:141]=255
    _,_,_,rows=lane(a)
    assert len(rows)>150
    assert all(r['centro_bordes_px']==120 for r in rows)
    assert all(r['ancho_px']==41 for r in rows)
    assert all(r['error_px']==-39.5 for r in rows)
    assert all(r['centro_momento_px']==120 for r in rows)
    fit=ajustar_recta(rows,240,320)
    assert fit is not None and abs(fit['centro_recta_px']-120)<1e-4
    assert fit['rmse_ortogonal_px']<1e-4
    inclined=[dict(y=y,centro_bordes_px=80+.25*y) for y in range(60,239)]
    fit=ajustar_recta(inclined,240,320)
    assert fit is not None and abs(fit['centro_recta_px']-128)<1e-4
    assert fit['rmse_ortogonal_px']<1e-4
    assert ajustar_recta([],240,320) is None
    assert ajustar_recta(inclined[:10],240,320) is None
    assert lane(np.zeros_like(a))[3]==[]
    clipped=np.zeros_like(a); clipped[:,:40]=255
    assert lane(clipped)[3]==[], 'No estimar centro con borde cortado'
    assert pwm(0,False,320)==(0.,0.)
    assert pwm(40,True,320)[0]>pwm(40,True,320)[1]
    assert pwm(-40,True,320)[0]<pwm(-40,True,320)[1]
    rng=np.random.default_rng(42); a=rng.normal(size=(128,128))
    b=np.roll(np.roll(a,7,axis=1),-4,axis=0)
    fa,fb=np.fft.fft2(a),np.fft.fft2(b)
    cross=fb*np.conj(fa); r=np.fft.ifft2(cross/abs(cross)).real
    py,px=np.unravel_index(np.argmax(r),r.shape)
    assert (px,py)==(7,124)
    shifted,response=cv2.phaseCorrelate(a,b)
    assert np.allclose(shifted,[7,-4],atol=.01)
    ratio=abs(fa)/abs(fb); delta=np.angle(fa*np.conj(fb))
    h=ratio*np.exp(1j*delta)
    assert np.max(abs(np.fft.ifft2(h*fb).real-a))<1e-10
    print('OK: ajuste L2 vertical/inclinado/sin datos, centros, anchos, perdida/corte, signo PWM, desplazamiento y reconstruccion Fourier.')

if __name__=='__main__': main()
