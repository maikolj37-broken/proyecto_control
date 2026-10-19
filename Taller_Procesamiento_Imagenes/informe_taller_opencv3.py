"""Genera el informe a partir de resultados calculados, sin cifras manuales."""
from pathlib import Path
from html import escape
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from pypdf import PdfReader, PdfWriter

ROOT=Path(__file__).resolve().parent / "taller3"

def build_report(out, info, rows):
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyES',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=9))
    styles['Title'].textColor=colors.HexColor('#16334b')
    styles['Heading1'].textColor=colors.HexColor('#16334b')
    story=[]; md=[]
    def p(text):
        story.append(Paragraph(escape(text),styles['BodyES'])); md.append(text+'\n')
    def title(text):
        story.append(Paragraph(escape(text),styles['Heading1'])); md.append('## '+text+'\n')
    def pic(name,width=480):
        from PIL import Image as PILImage
        path=out/'figuras'/name
        with PILImage.open(path) as im: w,h=im.size
        story.append(Image(str(path),width=width,height=width*h/w)); story.append(Spacer(1,8)); md.append(f'![{name}](figuras/{name})\n')
    def page(): story.append(PageBreak())
    valid=[r for r in rows if r['error_medio_px'] is not None]
    errors=[r['error_medio_px'] for r in valid]
    i,j=info['par']
    story.append(Paragraph('Taller de Visión Artificial<br/>Control 2',styles['Title']))
    story.append(Spacer(1,16))
    p('Maikol Julián Pulido | Ingeniería Electrónica | Escuela Colombiana de Ingeniería Julio Garavito')
    p('Continuación práctica y evidencia reproducible | 14 de octubre de 2026')
    title('Alcance y estado de entrega')
    p('Se implementan los puntos 1, 2, 6, 7, 9 y 10 con Python/OpenCV y NumPy. Se conserva íntegra la investigación aportada: su PDF original aparece al final como anexo, sin reescritura. Las figuras geométricas del punto 9 son entradas sintéticas solicitadas por la consigna; los cuadros de los puntos 2 y 10 proceden del video real existente.')
    p(f"El clip Otsu-inverso original contiene {info['cuadros_decodificados']} cuadros decodificados, {info['ancho']} × {info['alto']} píxeles y {info['fps']:.3f} cuadros/s; duración nominal {info['cuadros_decodificados']/info['fps']:.3f} s. Se extraen 40 cuadros distintos y se calcula la DFT completa de cada uno.")
    table=[['Punto','Evidencia / estado'],['1','Dos métodos por fila y comparación numérica'],['2','40 PNG, índices y tiempos; 20 muestras orientadas a curvas'],['6','Máscaras 3x3 y distancias en px; cm pendientes de calibración'],['7','Error lateral y PWM propuesto; sin prueba en motores'],['9','Círculo, cuadrado, línea: magnitud, fase y ejemplo unwrap'],['10','40 DFT; cociente, diferencia de fase, inversa y desplazamiento']]
    t=Table([[Paragraph(escape(c),styles['BodyES']) for c in row] for row in table],colWidths=[45,435]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7eef4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.4,colors.lightgrey)])); story.append(t)
    p('No hay una referencia métrica de dimensiones conocidas ni calibración de cámara en los materiales utilizados. Por tanto, no se presentan centímetros, velocidad real ni distancia recorrida. El PWM es una propuesta offline y no demuestra que el robot siga la pista.')
    page(); title('Trabajo previo, entradas y trazabilidad')
    p('Se inspeccionó Taller_Procesamiento_Imagenes: punto1.py recorta ideal.mp4 desde t=0 durante 15 s y genera gris/RGB; punto1_otsu.py genera las versiones Otsu original e inversa y sus variantes con gamma 2.2. También existen scripts de diferencias, filtrado y máscaras. Estos scripts se preservan en previo/. No se confunde su numeración con los puntos del nuevo taller.')
    p('Se revisó adicionalmente Robot_OpenCV/deteccion_camino.py: implementa segmentos por filas para un stream de ESP32-CAM. No se ejecutó esa conexión ni se modificó ese proyecto. La continuación se aloja exclusivamente en Taller_Procesamiento_Imagenes/taller3.')
    p('Se compararon visualmente los cuadros 0, 90, 180, 270, 360 y 450 del RGB, Otsu-inverso original y Otsu-inverso con gamma. Se eligió la versión original porque la variante gamma incorpora más fondo blanco en esas muestras. La elección es visual y no una evaluación de exactitud con anotaciones de referencia.')
    p('Entrada de cálculo: entradas/video_otsu_inverso.mp4, copia de resultados/taller2/clip_original_otsu_inv.mp4. Se vuelve a binarizar a 127 únicamente para quitar niveles grises introducidos por la compresión del MP4; no se aplica un segundo Otsu inverso, que invertiría nuevamente la polaridad. Blanco representa la línea oscura de la escena.')
    p('SHA-256 de la entrada: '+info['sha256'])
    p(f"Entorno ejecutado: Python {info['python']}; OpenCV {info['opencv']}; NumPy {info['numpy']}; Matplotlib {info['matplotlib']}. Índices base cero, x crece a la derecha e y hacia abajo. Los tiempos i/FPS se refieren al clip y son nominales.")
    p('La investigación original usa “transformada de distancia” al discutir distancia entre dos puntos. Precisión complementaria: distanceTransform entrega la distancia de cada píxel no nulo al cero más cercano; la distancia entre dos coordenadas especificadas se obtiene directamente con sus diferencias. Esta aclaración no modifica el anexo.')
    page(); title('1. Centro del carril por fila: dos opciones')
    p('Opción A, transiciones de borde: se filtra la máscara con Sobel X de 3x3. En cada fila se localiza un tramo blanco continuo delimitado por una transición de entrada y una de salida. Con extremos inclusivos xL y xR, el centro es c(y)=(xL+xR)/2 y el ancho es xR-xL+1. Si hay varios tramos, se escoge el centro más próximo al de la fila inferior; al iniciar se usa el centro de imagen.')
    p('Opción B, momento de primer orden: sobre la componente seleccionada, cM(y)=sum(x B(x,y))/sum(B(x,y)), con B binaria. Es el centroide de los píxeles blancos de la fila. Si no hay píxeles, el centro es indefinido y no se sustituye por cero. En un único tramo uniforme ambos métodos coinciden; agujeros y múltiples tramos pueden separarlos.')
    p('La implementación aplica apertura y cierre con unos 3x3 y bordes replicados. Selecciona la mayor componente conectada que alcanza el 20% inferior, dentro de y>=0.25H. Rechaza tramos que tocan los laterales, anchos fuera de [3,0.65W] y saltos de centro superiores a 0.12W. Esta hipótesis es adecuada para la cinta única observada; cruces, bifurcaciones o una sombra conectada pueden invalidarla.')
    disagreement=[r['diferencia_metodos_px'] for r in rows if r['diferencia_metodos_px'] is not None]
    p(f"Resultado: diferencia absoluta media entre ambos centros, promediada primero por cuadro y luego sobre los 40 cuadros: {sum(disagreement)/len(disagreement):.4f} px. La concordancia entre métodos no equivale a exactitud respecto al centro físico; no existe anotación manual de referencia.")
    pic('06_mascaras.png')
    page(); title('2. Extracción de 40 cuadros, con énfasis en curvas')
    p('Se decodifica secuencialmente todo el clip. Se eligen 20 índices uniformes y 20 adicionales por curvatura aparente, con separación mínima de 3 índices respecto a los ya elegidos. Para cada trayectoria se ajusta x=a(y/H)^2+b(y/H)+c. El puntaje |a|·(rango(y/H))²/4 aproxima la desviación respecto a la cuerda; es un indicador en píxeles, no curvatura física. Se exige cobertura de al menos 0.3H filas para puntuar.')
    p('Los índices seleccionados son: '+', '.join(map(str,info['seleccion']))+'.')
    p('Se conservan PNG binarios sin pérdida y otros PNG con centros naranjas y referencia vertical azul. datos/seleccion_40.csv registra índice, tiempo y criterio; datos/exploracion_458.csv contiene el puntaje de todos los cuadros. Las siguientes dos hojas permiten revisar visualmente la selección.')
    pic('02_contacto_1.png',width=400)
    page(); title('2. Hoja de contacto: cuadros 21 a 40'); pic('02_contacto_2.png',width=450)
    p('La numeración de cada imagen corresponde al índice original del clip; las 40 imágenes no son una secuencia a cadencia uniforme. No se calcula velocidad diferenciando su posición en la lista.')
    page(); title('6. Máscaras 3x3, ROI y distancias')
    p('Se usan K=unos(3,3) para apertura, cierre y gradiente morfológico, y Kx=[[-1,0,1],[-2,0,2],[-1,0,1]] para validar las transiciones horizontales. BORDER_REPLICATE extiende el valor del píxel del borde. La ROI empieza en 25% de la altura; la banda de medida/control comprende del 65% al 90%.')
    p('La referencia es x0=(W-1)/2=159.5 px. En cada fila: dL=x0-xL; dR=xR-x0; e=c-x0. Son distancias horizontales con signo y error lateral, no longitud recorrida. El ancho inclusivo difiere en un píxel de la separación geométrica entre extremos. centros_por_fila.csv conserva los valores para cada fila válida.')
    p('Se calcula además distancia euclidiana al borde más cercano con distanceTransform(255-borde, DIST_L2, DIST_MASK_PRECISE), evaluada en (floor((W-1)/2), round(0.8H)). Es una medida distinta del error horizontal: puede apuntar a un borde situado en otra fila. El borde tiene espesor discreto de la máscara 3x3; no hay precisión subpíxel.')
    p(f"En la banda de control hubo medida válida en {len(valid)}/40 cuadros. El error lateral medio por cuadro varió entre {min(errors):.2f} y {max(errors):.2f} px. El signo negativo indica línea a la izquierda. La tabla completa está en datos/resultados_40.csv.")
    p('Conversión a centímetros pendiente: colocar una regla o patrón de tamaño conocido sobre el mismo plano de la pista, con la cámara en su montaje final. Para una sola fila, medir una longitud L_cm cuya proyección sea L_px y usar s(y)=L_cm/L_px; entonces e_cm=s(y)e_px. La escala cambia con la profundidad. Para un plano completo, usar al menos cuatro correspondencias no colineales y homografía a coordenadas métricas; corregir antes la distorsión mediante calibración intrínseca. No es válido asignar un ancho supuesto a la cinta.')
    p('La distancia de la línea se interpreta aquí como separación lateral respecto al eje de cámara y distancia al borde, coherente con la finalidad de guiado. Para interpretar longitud de trayectoria o avance del móvil se necesita geometría y calibración adicionales.')
    title('7. Propuesta de PWM para los dos motores')
    p('Se promedia e(y) en la banda cercana y se normaliza en=e/159.5. Propuesta: base=110·(1-0.5·min(|en|,1)); u=70·en; PWM_L=clip(base+u,0,255), PWM_R=clip(base-u,0,255). Si la línea aparece a la derecha, se aumenta la rueda izquierda para girar a la derecha, suponiendo motores orientados para avance positivo. Verificar esa convención físicamente antes de usarla.')
    p('Los parámetros 110 y 70 son valores ilustrativos sin sintonización experimental. Si hay menos de 0.15H filas válidas en la banda, ambos PWM son cero. La reducción de base al crecer el error es una propuesta de moderación de velocidad; no prueba estabilidad ni mide velocidad. Añadir posteriormente límite de aceleración, compensación de zona muerta y control con encoders según el hardware.')
    page(); title('7. Resultado de la propuesta, sin accionar motores'); pic('07_control.png')
    p('La gráfica muestra comandos calculados de los cuadros seleccionados. Las líneas conectan muestras no uniformes y no representan un ensayo continuo de control. No se comunica por puerto serial, red ni GPIO.')
    title('Calidad, supuestos y fallos posibles')
    p('La selección de la componente no resuelve automáticamente cruces, oclusiones ni sombras conectadas. Los umbrales de anchura y salto son heurísticos para 320×240. El recorte de ROI elimina el horizonte pero también ignora la pista lejana. Las filas descartadas no se interpolan y el archivo de resultados registra la cantidad de filas válidas.')
    p('La perspectiva transforma el movimiento de una cámara sobre el piso en algo más complejo que una traslación uniforme. Por eso Fourier permite estimar desplazamiento aparente entre imágenes, pero no directamente distancia recorrida por el móvil. Hace falta validación con marcas conocidas, homografía métrica y/o odometría.')
    page(); title('9. Fourier de figuras geométricas')
    p('Se generan imágenes monocromáticas de 256×256: círculo lleno de radio 45 px, cuadrado de 91×91 px y segmento inclinado de grosor 3 px. La intensidad es 0/1 para la DFT. Se guardan magnitud y fase numéricas en fourier/*.npz, sin desplazar sus índices. fftshift se aplica solo para visualizar el origen en el centro; la magnitud se muestra como log(1+|F|).')
    pic('09_circulo.png'); pic('09_cuadrado.png')
    p('El círculo presenta simetría aproximadamente radial y lóbulos/anillos, alterados por el muestreo discreto. El cuadrado alineado con los ejes genera la estructura separable tipo sinc. La magnitud describe el contenido de frecuencias; no determina por sí sola la posición del objeto.')
    page(); title('9. Línea inclinada, fase y unwrapping'); pic('09_linea_inclinada.png')
    p('El segmento finito produce concentración espectral en la dirección normal al segmento, con lóbulos por su longitud y grosor finitos. No es una delta ideal ni una línea infinitamente delgada. La fase conserva información de posición y estructura espacial, definida módulo 2π. La fase donde la magnitud es casi cero no es fiable: se ocultan esos valores en las figuras geométricas.')
    pic('09_unwrap.png')
    p(f"Ejemplo sintético explícito: se desplaza circularmente el cuadrado 17 px a la derecha. La diferencia máxima entre magnitudes es {info['invariancia_magnitud_sintetica_error']:.3g}; la fase relativa sigue una rampa -2πu·17/256 módulo 2π. np.unwrap sobre el eje de frecuencia recupera la continuidad de esa rampa. Este desplazamiento conocido no se presenta como resultado del video.")
    p('Unwrapping añade múltiplos de 2π para quitar saltos convencionales. No crea información donde la magnitud es nula, no elimina ruido y aplicar unwrap sucesivamente por filas y columnas no garantiza una solución bidimensional única. Para reconstruir con exp(j·fase) no se necesita desenvolver la fase.')
    page(); title('10. Fourier de 40 cuadros y operaciones entre un par')
    p('Para cada PNG binario se calcula F=fft2(B/255), M=abs(F) y fase=angle(F). Hay 40 archivos de matrices y dos atlas con magnitud/fase de todos los cuadros. No se usa la imagen logarítmica para operar: los cálculos usan matrices sin normalización visual.')
    p(f"Se usa i={i} y j={j}, separados {j-i} índices ({info['separacion_s']:.4f} s). Cumplen al menos tres cuadros intermedios. El par se elige entre los 40 extraídos, priorizando cercanía temporal y después el puntaje de curva de i.")
    p(f"a) R=Mi/Mj solo donde Mj>epsilon, con epsilon=10^-6·max(Mj)={info['epsilon']:.6g}; en los otros bins R=0. La fracción descartada es {info['fraccion_frecuencias_descartadas']:.4%}. Esta regularización evita divisiones por cero y amplificación arbitraria. La máscara de soporte también se guarda.")
    p('b) Se guarda fase_i-fase_j directa y también su equivalente envuelta angle(Fi·conj(Fj)). c) Se forma H=R·exp(j·delta_fase) y h=ifft2(H). H coincide con Fi/Fj en los bins admitidos: h es un núcleo de transferencia/deconvolución circular; no es automáticamente una imagen de la pista ni un mapa de distancias.')
    pic('10_par.png')
    p(f"Comprobación numérica: reconstruir i mediante ifft2(H·Fj) da RMSE={info['error_reconstruccion_rmse']:.6g} en intensidad [0,1]. El residuo imaginario máximo de h es {info['residuo_imaginario_max']:.3g}. No se interpreta la parte imaginaria como una distancia.")
    page(); title('10.d. Método para estimar desplazamiento')
    p('Se utiliza el teorema del desplazamiento: para j trasladado respecto a i, la fase cruzada contiene una rampa. Se calcula C=(Fj·conj(Fi))/|Fj·conj(Fi)| en frecuencias con energía y r=ifft2(C). El máximo de r da el desplazamiento circular de i hacia j, con coordenadas mayores a media imagen convertidas a signo negativo.')
    p(f"Pico sin ventana: dx={info['desplazamiento_pico_px'][0]} px, dy={info['desplazamiento_pico_px'][1]} px. OpenCV phaseCorrelate con ventana Hann y estimación subpíxel: dx={info['desplazamiento_hann_px'][0]:.3f} px, dy={info['desplazamiento_hann_px'][1]:.3f} px; respuesta={info['respuesta_hann']:.4f}. Son desplazamientos aparentes de imagen y no medidas del recorrido físico. Las diferencias entre estimaciones evidencian sensibilidad a ventana, bordes y deformación de la escena.")
    p('La respuesta de phaseCorrelate es una medida de concentración del pico, no una probabilidad de acierto. Una pista repetitiva, curvada o con perspectiva puede producir máximos ambiguos. Para estimar distancia física: rectificar al plano del piso con homografía métrica, estimar traslación en regiones coherentes, rechazar pares con poca respuesta o residuos grandes y contrastar con una referencia independiente. También debe tenerse en cuenta que movimiento de escena y de cámara tienen sentidos opuestos.')
    title('Reproducción y archivos de evidencia')
    p('Desde taller3: python -m pip install -r requirements.txt ; luego python validar.py ; luego python taller.py. Cada comando se ejecuta por separado. Para otra salida: python taller.py --out outputs_nuevos. --video acepta un video ya umbralizado Otsu-inverso con blanco como línea; no acepta indistintamente video RGB crudo.')
    p('outputs/datos contiene selección, centros por fila, resultados, exploración y metadatos. outputs/cuadros contiene 40 binarios y 40 imágenes anotadas. outputs/fourier contiene magnitudes/fases de los 40 cuadros, las tres figuras y operaciones_par.npz. outputs/figuras contiene hojas de contacto, máscaras, control y atlas espectrales. informe.md es la versión editable generada de este texto.')
    title('Fuentes')
    p('Consigna: Taller_opencv3 (1).pdf, Control 2, dos páginas. Investigación previa: opencv_taller.pdf, Maikol Julián Pulido, 1 de octubre de 2026, cuatro páginas; se conserva a continuación.')
    p('OpenCV, Image Filtering (máscaras y bordes): https://docs.opencv.org/2.4.13.7/modules/imgproc/doc/filtering.html')
    p('OpenCV, Miscellaneous Image Transformations (distancia al cero más próximo): https://docs.opencv.org/doc/doxygen/html/d7/d1b/group__imgproc__misc.html')
    p('OpenCV, Motion Analysis and Object Tracking (phaseCorrelate): https://docs.opencv.org/4.0.1/d7/df3/group__imgproc__motion.html')
    p('La documentación de versiones anteriores se utiliza para las definiciones matemáticas; las llamadas se ejecutaron y comprobaron en la versión de OpenCV indicada en este informe.')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#526779')); canvas.drawString(42,24,'Control 2 | Evidencia offline | 14/10/2026'); canvas.drawRightString(553,24,str(doc.page))
    temp=ROOT/'work'
    if not temp.is_dir(): raise FileNotFoundError(f'Falta la carpeta existente {temp}')
    draft=temp/'informe_practico.pdf'
    SimpleDocTemplate(str(draft),pagesize=(595,842),rightMargin=42,leftMargin=42,topMargin=40,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
    writer=PdfWriter(); writer.append(str(draft)); writer.append(str(ROOT/'entradas/investigacion_original.pdf'))
    with open(out/'Informe_Taller_Control_2.pdf','wb') as f: writer.write(f)
    (out/'informe.md').write_text('# Taller de Visión Artificial - Control 2\n\n'+'\n'.join(md)+'\nAnexo sin modificaciones: ../entradas/investigacion_original.pdf\n',encoding='utf-8')
