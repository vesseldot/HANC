# HANC — Virtual Painter

Pizarrón virtual controlado con la mano y la cámara web. Dibuja en el aire con gestos naturales: selecciona colores, borra, mueve figuras y deja que el programa corrija automáticamente círculos, cuadrados, rectángulos y corazones.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange.svg)

## Características

- Detección de mano en tiempo real con **MediaPipe**
- Menú visual con pinceles azul, rojo, verde y borrador
- Grosor de trazo dinámico según la velocidad del movimiento
- Reconocimiento y corrección automática de figuras cerradas
- Pinza para mover figuras individuales o todo el lienzo
- Guardado automático al salir (`mi_dibujo.png`)

## Requisitos

- Python 3.8 o superior
- Cámara web
- Windows / Linux / macOS

## Instalación

```powershell
git clone https://github.com/vesseldot/HANC.git
cd HANC
pip install -r requirements.txt
```

## Uso

```powershell
python VirtualPainter.py
```

Al cerrar con la tecla **Q**, el dibujo se guarda en `mi_dibujo.png`.

### Gestos

| Gesto | Acción |
|-------|--------|
| Índice + Medio | Seleccionar pincel o borrador en el menú |
| Solo Índice | Dibujar (figuras cerradas se corrigen solas) |
| 5 dedos arriba | Limpiar todo el lienzo |
| Pinza en figura | Mover esa figura |
| Pinza en vacío | Mover todo el dibujo |
| Borrador | Borrar trazos y figuras |
| Tecla Q | Salir y guardar |

## Estructura del proyecto

```
HANC/
├── VirtualPainter.py        # Aplicación principal
├── HandTrackingModule.py    # Detección de manos con MediaPipe
├── crear_header_temporal.py # Generador de imágenes del menú
├── header/                  # Imágenes del menú (1.jpg – 4.jpg)
├── requirements.txt
├── DOCUMENTACION.md         # Documentación técnica detallada
└── README.md
```

## Documentación

Para el detalle de cada módulo, gestos, reconocimiento de figuras y diagrama de flujo, consulta [DOCUMENTACION.md](DOCUMENTACION.md).

## Equipo

Proyecto del equipo **HANC** — Verano de Graficación.
