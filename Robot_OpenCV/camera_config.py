"""Configuración común para la cámara en modo STA (IP asignada por el hotspot)."""
import argparse
import os
from urllib.parse import urlsplit


def stream_url(value):
    value = value.strip()
    if not value:
        raise ValueError("Indica la IP que muestra 'Direccion IP' en el monitor serie.")
    parsed = urlsplit(value if "://" in value else "http://" + value)
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Usa una IP/host o una URL HTTP sin credenciales.")
    if parsed.query or parsed.fragment or parsed.path not in ("", "/", "/stream"):
        raise ValueError("La ruta del firmware es /stream, sin parámetros.")
    port = parsed.port
    if port not in (None, 80, 81):
        raise ValueError("El firmware transmite en el puerto 81.")
    host = parsed.hostname
    if ":" in host:
        host = "[" + host + "]"
    return f"http://{host}:81/stream"


def get_stream_url():
    parser = argparse.ArgumentParser(
        description="ESP32-CAM en el mismo hotspot que el PC; un cliente de video a la vez.")
    parser.add_argument("--ip", "--url", dest="camera", default=os.getenv("ROBOT_CAMERA_IP", ""),
                        help="IP del monitor serie o URL del stream; también ROBOT_CAMERA_IP.")
    args = parser.parse_args()
    value = args.camera
    if not value:
        try:
            value = input("IP de la cámara (Direccion IP del monitor serie): ")
        except (EOFError, KeyboardInterrupt):
            parser.error("Indica --ip o configura ROBOT_CAMERA_IP.")
    try:
        url = stream_url(value)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Video: {url}")
    print("PC y cámara deben estar en el mismo hotspot. Cierra el video del navegador.")
    return url


def open_capture(url):
    import cv2
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG, [
        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000,
        cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000,
    ])
    if not cap.isOpened():
        cap.release()
        raise SystemExit("No se pudo abrir el video. Revisa IP, hotspot y clientes duplicados.")
    return cap


def detector_frame(frame):
    """Conservar ROI/anchos/centro originales sobre VGA o QVGA, sin volver a rotar."""
    import cv2
    return cv2.resize(frame, (160, 120), interpolation=cv2.INTER_AREA)
