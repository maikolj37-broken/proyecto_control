"""Pruebas de geometria, perdida de linea, signo del control y desplazamiento."""
import numpy as np
import cv2
from taller import lane,pwm

def main():
    a=np.zeros((240,320),np.uint8); a[:,100:141]=255
    _,_,_,rows=lane(a)
    assert len(rows)>150
    assert all(r['centro_bordes_px']==120 for r in rows)
    assert all(r['ancho_px']==41 for r in rows)
    assert all(r['error_px']==-39.5 for r in rows)
    assert all(r['centro_momento_px']==120 for r in rows)
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
    print('OK: centros, anchos, perdida/corte, signo PWM, desplazamiento y reconstruccion Fourier.')

if __name__=='__main__': main()
