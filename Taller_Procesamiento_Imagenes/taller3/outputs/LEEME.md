# Taller de Visión Artificial - Control 2

Continuación del trabajo existente, preparada el 14 de octubre de 2026.

## Abrir el resultado

- `outputs/Informe_Taller_Control_2.pdf`: informe de 15 páginas, incluidas las cuatro páginas de investigación original sin modificaciones.
- `outputs/informe.md`: texto editable, con figuras enlazadas.
- `outputs/cuadros`: 40 cuadros reales binarios y 40 versiones con centros dibujados.
- `outputs/figuras`: contacto, máscaras, propuesta de control, figuras geométricas y atlas de Fourier de los 40 cuadros.
- `outputs/datos/resultados_40.csv`: medidas y comandos propuestos por cuadro.
- `outputs/datos/centros_por_fila.csv`: extremos, centros, anchos y errores por fila.
- `outputs/datos/seleccion_40.csv`: índices base cero, tiempos nominales y criterio de selección.
- `outputs/fourier`: matrices numéricas NPZ, sin el desplazamiento visual fftshift.

## Reproducir

Recomendado: Python 3.12 y entorno virtual independiente. Desde esta carpeta, ejecutar por separado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe validar.py
.\.venv\Scripts\python.exe taller.py
```

El proceso no necesita internet después de instalar las dependencias. No abre cámaras, ventanas interactivas ni conexiones con el robot. Escribe sus resultados en `outputs/`, reemplazando los archivos generados con los mismos nombres. Para conservar una ejecución:

```powershell
.\.venv\Scripts\python.exe taller.py --out outputs_nuevos
```

El video incluido ya está umbralizado Otsu-inverso. `--video` espera esa polaridad: blanco para la línea. No pasar un video RGB sin adaptar el preprocesamiento. El código exige al menos 40 cuadros decodificables. Los parámetros de detección se documentan en `lane()` y los de control en `pwm()`; `informe.py` explica los valores predeterminados, por lo que debe actualizarse también si se cambian.

## Evidencia y procedencia

La fuente es `../resultados/taller2/clip_original_otsu_inv.mp4`, copiada a `entradas/video_otsu_inverso.mp4`. Se decodificaron 458 cuadros, 320x240 px, 30.537 FPS. Se seleccionaron 20 muestras uniformes y 20 por curvatura aparente. El video original y los scripts del taller anterior no se modificaron; `previo/` conserva copias de los scripts consultados.

`entradas/consigna.pdf` contiene las instrucciones. `entradas/investigacion_original.pdf` conserva el PDF aportado. Su contenido se incorpora al final del informe generado mediante anexado de páginas, no reescritura.

`outputs/datos/ejecucion.json` registra SHA-256 del video, versiones, parámetros, índices seleccionados y cifras del análisis. `outputs/datos/validacion.json` registra las verificaciones de la entrega. `validar.py` utiliza casos sintéticos únicamente para comprobar algoritmos; no se presentan como medidas de video.

## Límites que siguen abiertos

- **Centímetros:** no se dispone de calibración real. El CSV indica `SIN_CALIBRACION`. El informe describe cómo medir escala local o una homografía métrica; no se supone un ancho físico de cinta.
- **PWM:** valores ilustrativos offline, sin sintonización ni ensayo físico. No se enviaron a motores. Deben verificarse polaridad, zona muerta, frecuencia PWM y respuesta del robot.
- **Movimiento Fourier:** desplazamiento aparente de imagen, sensible a perspectiva, deformación y ventana. No se interpreta como avance físico del móvil.
- **Exactitud del detector:** no hay centros anotados manualmente. Que los dos métodos coincidan no demuestra exactitud física.

## Lectura de matrices

```python
import numpy as np
d = np.load('outputs/fourier/cuadro_0316.npz')
F = d['magnitud'] * np.exp(1j * d['fase'])
imagen_reconstruida = np.fft.ifft2(F).real
```

Las figuras del punto 9 son sintéticas por consigna. Las operaciones del punto 10 usan los cuadros reales 316 y 320, con tres cuadros intermedios. `operaciones_par.npz` incluye el cociente regularizado, soporte de frecuencias, ambas diferencias de fase, inversa compleja y correlación de fase.
