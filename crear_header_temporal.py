"""
Genera imágenes temporales para la carpeta Header/ mientras el equipo
de diseño termina las versiones en Canva.

Cuando tengan los JPG finales, reemplacen 1.jpg a 4.jpg y borren este script
si ya no lo necesitan.
"""

import os

import cv2
import numpy as np

HEADER_WIDTH = 1280
HEADER_HEIGHT = 125
OUTPUT_DIR = 'Header'

BAR_COLOR = (0, 180, 0)
BRUSH_COLORS = [
  (203, 192, 255),
  (0, 255, 0),
  (255, 0, 0),
  (80, 80, 80),
]
BRUSH_LABELS = ['Rosa', 'Verde', 'Azul', 'Borrador']
ICON_CENTERS = [180, 380, 580, 780]


def drawBrushIcon(canvas, centerX, color, selected=False):
  if selected:
    cv2.circle(canvas, (centerX, 70), 34, (160, 160, 160), -1)
  cv2.circle(canvas, (centerX, 70), 28, color, -1)
  cv2.rectangle(canvas, (centerX - 8, 88), (centerX + 8, 118), (200, 200, 200), -1)


def createHeader(selectedIndex):
  header = np.zeros((HEADER_HEIGHT, HEADER_WIDTH, 3), dtype=np.uint8)
  header[:] = BAR_COLOR

  cv2.putText(
    header,
    'HANC - Header temporal',
    (20, 30),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.7,
    (255, 255, 255),
    2,
  )

  for index, (centerX, color, label) in enumerate(
    zip(ICON_CENTERS, BRUSH_COLORS, BRUSH_LABELS)
  ):
    drawBrushIcon(header, centerX, color, selected=index == selectedIndex)
    cv2.putText(
      header,
      label,
      (centerX - 45, 118),
      cv2.FONT_HERSHEY_SIMPLEX,
      0.45,
      (255, 255, 255),
      1,
    )

  return header


def main():
  os.makedirs(OUTPUT_DIR, exist_ok=True)

  for index in range(4):
    image = createHeader(index)
    outputPath = os.path.join(OUTPUT_DIR, f'{index + 1}.jpg')
    cv2.imwrite(outputPath, image)
    print(f'Creado: {outputPath}')

  print('\nListo. Cuando diseño entregue los JPG de Canva, reemplaza estos archivos.')


if __name__ == '__main__':
  main()
