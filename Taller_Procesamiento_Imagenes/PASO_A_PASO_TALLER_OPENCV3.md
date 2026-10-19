# Resultados del taller OpenCV 3

Ejecuta desde Taller_Procesamiento_Imagenes:

```cmd
python -B taller_opencv3.py
```

Todo se guarda en taller3_opencv, organizado asi:

| Carpeta | Contenido |
|---|---|
| 01_pruebas_artificiales | Circulo, cuadrado y linea sinteticos; sus magnitudes/fases y ejemplo unwrap. |
| 02_imagenes_video | Los 40 cuadros Otsu-inverso del video, sin anotaciones. |
| 03_video_linea_central | Los 40 cuadros con centros naranjas y referencia azul, mas hojas de contacto. |
| 04_mascaras_y_distancias | Comparacion de limpieza, bordes, centros y distancias en pixeles. |
| 05_control_pwm | Grafica de error y PWM propuesto, sin enviar ordenes a motores. |
| 06_fourier_video | Atlas espectrales, comparacion del par y matrices NPZ de los cuadros reales. |
| 07_datos | CSV de seleccion, centros y resultados, mas metadatos JSON. |

La prueba artificial visible corresponde a las figuras del punto 9. Las pruebas automaticas de validar_taller_opencv3.py siguen mostrando su resultado en la terminal.

Para verificar los algoritmos: python -B validar_taller_opencv3.py

El programa no genera PDF ni exporta MP4. Guarda imagenes y datos. No modifica el video original. Al repetir una ejecucion reemplaza los resultados de igual nombre en estas carpetas. Los CSV registran rutas relativas de los cuadros dentro de esta estructura.

No se calculan centimetros sin calibracion real y los PWM no estan ensayados en motores.


## Metodo de la investigacion ahora utilizado

Se implementa el punto 5, apartado de ajuste por minimos cuadrados, mediante ajustar_recta() y cv2.fitLine(puntos, cv2.DIST_L2, 0, 0.01, 0.01).

Los centros por fila son las observaciones. Se ajusta una recta local entre 65% y 90% de la altura minimizando distancias perpendiculares al cuadrado (minimos cuadrados ortogonales, no regresion vertical y=mx+b). La recta parametrica es (x,y)=(x0,y0)+t(vx,vy).

En y_ref=0.8H se calcula x_ref=x0+(y_ref-y0)*vx/vy. El error que alimenta pwm() es x_ref-(W-1)/2. Antes se utilizaba la media de errores; ahora la recta interviene realmente en el calculo del control. La media anterior se conserva solo como comparacion en el CSV.

Imagenes: naranja=centros observados; verde=recta local de minimos cuadrados; magenta=punto de control; azul=referencia de imagen. No se ajusta una sola recta a toda la curva. No se extrapola fuera de las filas observadas. Si faltan puntos o no se puede obtener un ajuste util, se proponen ambos PWM en cero.

07_datos/ajustes_recta.csv contiene vector director, punto de paso, centro estimado, error de control y RMSE perpendicular. resultados_40.csv contiene error_medio_px para comparacion y error_control_recta_px como entrada real del PWM.

El RMSE cuantifica dispersion respecto a la recta, no exactitud respecto a una pista anotada. Por ahora se registra pero no hay un umbral de rechazo por RMSE sintonizado experimentalmente. DIST_L2 es sensible a puntos atipicos. El PWM sigue siendo una propuesta offline sin ensayo de motores.

Referencia de la funcion: https://docs.opencv.org/4.13.0/d3/dc0/group__imgproc__shape.html
