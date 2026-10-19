# Identificación y guía de línea con el stream

## Ejecutar

Conectar PC y cámara al mismo hotspot, cerrar el video del navegador y otros clientes. Desde esta carpeta:

```powershell
python -m pip install -r requirements.txt
python seguimiento_linea.py --ip 10.226.156.32
```

Usar la IP actual del monitor serie si cambió. Sin `--ip`, el programa la pregunta. También acepta `--url` y `ROBOT_CAMERA_IP` como los clientes anteriores. No requiere cambiar el firmware de cámara.

**Esta versión guía visualmente y calcula referencias; no manda PWM ni controla motores.** La integración con el controlador de velocidad de cada motor es una etapa posterior. Los valores de giro y velocidad son adimensionales, no rad/s ni m/s.

## Recorrer las 16 etapas

`M`: mosaico. `N`: siguiente etapa. `P`: anterior. `Espacio`: congelar/reanudar (guía inválida durante la pausa). `S`: guardar las 16 imágenes y el panel del cuadro. `Q`: cerrar. La recepción continúa durante la pausa para volver al cuadro reciente al reanudar.

| Paso | Qué hace y qué revisar |
|---|---|
| 1. Original | Reduce la imagen a 320 × 240 para procesar. La cámara ya gira 180°; no se vuelve a girar. La parte inferior debe ser la pista más cercana al carro. |
| 2. Gris | Convierte BGR a intensidad. Comprobar que línea y fondo se distinguen. |
| 3. Gamma | Usa la fórmula del taller: `255*(I/255)^gamma`. Con gamma=1 no cambia; mayor que 1 oscurece. |
| 4. Mediana | Filtro 3 × 3 para ruido pequeño sin promediar tanto los bordes. |
| 5. Segmentación | Otsu inverso para línea negra: la línea queda blanca en la máscara. También admite umbral manual o línea blanca. |
| 6. Diferencia | Diferencia absoluta entre la segmentación elegida y Otsu sobre gris original. Compara el efecto del filtrado/gamma; no se usa como máscara principal, pues puede estar vacía cuando ambas coinciden. |
| 7. Limpieza + ROI | Apertura/cierre 3 × 3; descarta el 25% superior, igual que el taller. |
| 8. Componente | Selecciona la mayor componente que llega al 20% inferior. Verificar que selecciona la pista y no una sombra. |
| 9. Máscara | Aplica la componente a la imagen gamma para comprobar qué zona se conservó. |
| 10. Bordes | Gradiente morfológico. Sobel X se usa internamente para validar los bordes izquierdo y derecho. |
| 11. Centros | Centros entre ambos bordes por fila. Rechaza tramos recortados en laterales, anchos no válidos y saltos bruscos. |
| 12. Recta L2 | Ajuste local entre 65% y 90% de altura. Evalúa el centro en 80% de altura para obtener el error lateral. |
| 13. Perfil FFT | Naranja: centros x(y). Verde: perfil reconstruido con bajas frecuencias espaciales. |
| 14. Espectro | Magnitud logarítmica de la FFT del perfil sin tendencia; verde muestra los componentes retenidos. El eje es índice espacial, no Hz. |
| 15. Anticipación | Flecha desde la fila cercana (80% H) a la lejana (45% H), ambas dentro de línea observada. Indica izquierda/recta/derecha del tramo visible. |
| 16. Guía | Error/dirección combinados en una referencia exploratoria de giro y una velocidad relativa. Si faltan datos válidos, ambas son cero. |

Los algoritmos `lane`, `ajustar_recta` y `pwm` de `taller_opencv3.py` están copiados **sin cambios** a `linea_taller.py`, para ejecutarlos sin el generador de imágenes offline ni matplotlib. El nuevo código añade preprocesamiento de cámara, confirmación temporal, rechazo por RMSE y FFT del perfil. Los scripts anteriores y los talleres permanecen disponibles.

## Ajustar en orden

1. **Orientación e iluminación:** fijar altura/ángulo de cámara. Confirmar físicamente cuál es la derecha del robot. Evitar reflejos y saturación. El programa supone línea negra sobre fondo claro y cámara viendo pista cercana abajo y lejana arriba.
2. **Segmentación:** comenzar con Otsu y gamma=1. Si no separa bien la línea, comparar `--gamma 0.7` y `--gamma 1.4`. No adoptar el gamma 2.2 del video ajeno sin comprobarlo. Para manual: `--modo manual --umbral 80`. Para pista blanca: `--linea blanca`.
3. **Máscara y centros:** comprobar pasos 7–11. Si se selecciona una sombra o unión, los valores posteriores no son confiables. No compensar una máscara incorrecta cambiando el controlador.
4. **Ajuste:** `--rmse-max 3` es un límite inicial de 3 píxeles, no una calibración validada. Verificar la recta verde y el punto de referencia. No aumentar el límite solo para hacer aparecer VALIDA.
5. **Anticipación:** comparar centros y perfil FFT. Por defecto `--armonicos 5`; reducir suaviza más y puede borrar curvas; aumentar conserva detalle y ruido. Requiere cubrir la fila lejana, al menos 35% de H en centros, y no tener huecos mayores de 5% H.
6. **Seguimiento temporal:** `--confirmar 3` exige tres cuadros procesados válidos antes de habilitar la guía. Una pérdida la invalida inmediatamente. No son tres segundos ni una medida de confianza probabilística.
7. **Ensayo de pista:** presentar recta, curvas a ambos lados, pérdida de línea y recuperación. Registrar con `--guardar`. Esto debe hacerse antes de usar las referencias en el controlador real.

Ejemplo:

```powershell
python seguimiento_linea.py --ip 10.226.156.32 --gamma 1.0 --armonicos 5 --guardar
```

## Fórmulas y significado de la FFT

En una fila, `c(y)=(x_izquierdo+x_derecho)/2`. La recta L2 es `(x,y)=(x0,y0)+t(vx,vy)`. En `y_ref=0.8H`:

`x_ref = x0 + (y_ref-y0)*vx/vy`

`error_px = x_ref - (W-1)/2`, `error_normalizado = error_px/((W-1)/2)`.

Error positivo significa línea a la derecha de la imagen. La banda de ajuste debe cubrir la referencia: no se extrapola el ajuste local.

Para anticipar, se construye `x(y)` con los centros observados. Se interpolan solo huecos pequeños dentro del intervalo observado, se resta una tendencia lineal y se extiende por reflexión para reducir la discontinuidad del cierre periódico. Se calcula `rfft`, se conservan DC y los primeros K índices y se reconstruye con `irfft`, añadiendo otra vez la tendencia. Así una recta inclinada conserva su pendiente.

En las filas lejana y cercana se obtiene:

`delta_x = x_lejano - x_cercano`

`angulo_imagen = atan2(delta_x, y_cercano-y_lejano)`.

Se clasifica derecha/izquierda si delta_x supera ±3% del ancho; en caso contrario, recta. Es una dirección media de la pista visible, **no orientación física calibrada, ni predicción temporal, ni detección de una curva oculta**. Una S puede tener desplazamiento neto pequeño: revisar también el perfil dibujado.

La FFT 2D de una imagen del taller sirve para estudiar su contenido espacial; por sí sola no da una orden de giro. Aquí la adaptación útil es la FFT 1D del perfil geométrico detectado, conservando fase en la reconstrucción. No se convierten frecuencias a velocidad del carro.

Referencia: [rfft de NumPy](https://numpy.org/doc/stable/reference/generated/numpy.fft.rfft.html) y [transformadas/inversas de NumPy](https://numpy.org/doc/stable/reference/routines.fft.html).

## Salida para el futuro controlador

`linea_pipeline.Pipeline.process(frame)` devuelve las etapas y un diccionario. Campos principales:

| Campo | Interpretación |
|---|---|
| `guia_valida` | Confirmación temporal + L2 válido + cobertura para FFT. |
| `error_px`, `error_normalizado` | Desplazamiento lateral de la línea en la imagen de análisis. |
| `angulo_imagen_deg` | Dirección hacia el tramo visible lejano en coordenadas de imagen. |
| `direccion_visible` | IZQUIERDA, RECTA, DERECHA o DESCONOCIDA. |
| `rmse_px`, `residuo_fft_px` | Calidad del ajuste y diferencia respecto al perfil filtrado; no exactitud física. |
| `giro_relativo` | `clip(0.6*error_normalizado + 0.4*sin(angulo_imagen), -1, 1)`. Positivo: derecha en imagen. Ganancias iniciales, no sintonizadas. |
| `velocidad_relativa` | Factor exploratorio entre 0.2 y 1 si la guía es válida; cero en otro caso. Reduce la propuesta al aumentar giro/ángulo. No es velocidad medida ni garantiza estabilidad a alta velocidad. |

Los campos `pwm_taller_*` se mantienen en el registro solo para comparar con la fórmula histórica del taller; **no son las salidas para tu controlador** y pueden existir si hay ajuste cercano pero no anticipación válida. Para integrar motores usar la validez y las referencias de guía, con temporizador de pérdida de comunicación en el controlador.

La futura conversión a referencias de rueda requiere parámetros físicos, signo de giro, velocidad máxima ensayada y el contrato de comunicación con el controlador. Por ejemplo, con velocidad lineal v, giro físico omega y separación L: `v_derecha=v+omega*L/2`, `v_izquierda=v-omega*L/2` para omega positivo antihorario. No se puede insertar directamente el giro relativo en esa fórmula: su signo de imagen y su escala deben convertirse primero.

## Registro, reproducción y límites

`--guardar` crea `resultados_seguimiento/FECHA_HORA/` con configuración y CSV por cuadro, más registro de pausa/pérdida/finalización. `S` guarda imágenes de las etapas y el panel. Estas capturas locales no se publican automáticamente en GitHub. Las mediciones son en píxeles: `SIN_CALIBRACION`.

Para un video propio grabado anteriormente:

```powershell
python seguimiento_linea.py --video ruta_al_video.mp4
python seguimiento_linea.py --video ruta_al_video.mp4 --sin-ventana --max-cuadros 100 --guardar
```

El modo video procesa a la velocidad disponible, no reproduce tiempos físicos. No añade las referencias temporales de la cámara a un archivo grabado.

En vivo un lector mantiene solo el cuadro recibido más reciente. `--edad-max 0.5` invalida la guía si no llega un cuadro nuevo durante medio segundo. Es tiempo desde recepción, **no edad desde exposición**: el firmware no envía esa marca temporal. La latencia de la cámara/red requiere medición antes de correr como velocista. El controlador debe tener además su propio watchdog.

Sombras, bifurcaciones, cruces, recortes laterales, pérdida de foco y perspectiva fuerte pueden producir elecciones incorrectas de componente. Esta versión sigue una sola línea y no decide rutas en cruces. La FFT no corrige una segmentación equivocada. La reducción de velocidad es una heurística inicial; el máximo seguro se determina con ensayos físicos y el controlador de motores.
