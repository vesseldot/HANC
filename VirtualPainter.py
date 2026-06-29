# Pizarrón virtual con cámara: dibuja con el dedo y corrige figuras cerradas.
import math
import os
import sys
import time

import cv2
import numpy as np

import HandTrackingModule as htm

# Parámetros de pincel, menú y reconocimiento de formas.
brushThickness = 15
eraserThickness = brushThickness * 8
headerHeight = 125
canvasWidth = 1280
canvasHeight = 720

minThickness = 3
maxThickness = 20
maxSpeed = 60
selectionCooldown = 0.8
clearCooldown = 1.0
pinchThreshold = 40
pinchReleaseThreshold = 55
shapeMinSize = 50
shapeHitPadding = 25
minStrokePoints = 20

brushColors = [
  (255, 0, 0),
  (0, 0, 255),
  (0, 255, 0),
  (0, 0, 0),
]

toolNames = ['Azul', 'Rojo', 'Verde', 'Borrador']

menuZones = [
  (200, 420),
  (420, 620),
  (620, 820),
  (820, 1100),
]

cameraFlipCode = 1


# Figura geométrica reconocida; se puede mover y borrar como un objeto.
class Shape:
  def __init__(self, shapeType, name, x1, y1, x2, y2, color, thickness=3):
    self.shapeType = shapeType
    self.name = name
    self.color = color
    self.thickness = thickness
    self.setBounds(x1, y1, x2, y2)

  def setBounds(self, x1, y1, x2, y2):
    self.x1 = min(x1, x2)
    self.y1 = min(y1, y2)
    self.x2 = max(x1, x2)
    self.y2 = max(y1, y2)

    # Fuerza lados iguales centrando el cuadrado en el trazo del usuario.
    if self.shapeType == 'cuadrado':
      size = min(self.x2 - self.x1, self.y2 - self.y1)
      centerX = (self.x1 + self.x2) // 2
      centerY = (self.y1 + self.y2) // 2
      self.x1 = centerX - size // 2
      self.y1 = centerY - size // 2
      self.x2 = self.x1 + size
      self.y2 = self.y1 + size

  def move(self, dx, dy):
    self.x1 += dx
    self.y1 += dy
    self.x2 += dx
    self.y2 += dy

  def containsPoint(self, x, y, padding=shapeHitPadding):
    return (
      self.x1 - padding <= x <= self.x2 + padding
      and self.y1 - padding <= y <= self.y2 + padding
    )

  def intersectsLine(self, x1, y1, x2, y2, radius):
    steps = max(int(math.hypot(x2 - x1, y2 - y1)), 1)
    for step in range(steps + 1):
      t = step / steps
      x = int(x1 + (x2 - x1) * t)
      y = int(y1 + (y2 - y1) * t)
      if self.containsPoint(x, y, padding=radius):
        return True
    return False


def loadHeaderImages(folderPath):
  if not os.path.isdir(folderPath):
    os.makedirs(folderPath)
    print(f'Carpeta "{folderPath}" creada.')
    print('Coloca las imágenes 1.jpg, 2.jpg, 3.jpg y 4.jpg y vuelve a ejecutar.')
    sys.exit(0)

  imageFiles = sorted(
    f
    for f in os.listdir(folderPath)
    if f.lower().endswith(('.jpg', '.jpeg', '.png'))
  )

  if len(imageFiles) < 4:
    print(f'Se necesitan 4 imágenes en {folderPath}/. Encontradas: {len(imageFiles)}')
    print('Ejecuta: python crear_header_temporal.py')
    sys.exit(1)

  overlayList = []
  for imageName in imageFiles[:4]:
    imagePath = os.path.join(folderPath, imageName)
    image = cv2.imread(imagePath)
    if image is None:
      print(f'No se pudo leer: {imagePath}')
      sys.exit(1)
    overlayList.append(image)

  return overlayList


def isOpenHand(fingers):
  return len(fingers) == 5 and all(fingers)


def selectTool(x, y, overlayList):
  if y >= headerHeight:
    return None, None, None

  for index, (xMin, xMax) in enumerate(menuZones):
    if xMin < x < xMax:
      return overlayList[index], brushColors[index], index

  return None, None, None


# Grosor inverso a la velocidad del dedo: más lento = trazo más grueso.
def getDynamicThickness(x1, y1, x2, y2):
  speed = math.hypot(x2 - x1, y2 - y1)
  ratio = min(speed / maxSpeed, 1.0)
  return int(maxThickness - ratio * (maxThickness - minThickness))


def strokeBounds(points):
  xs = [point[0] for point in points]
  ys = [point[1] for point in points]
  return min(xs), min(ys), max(xs), max(ys)


# Comprueba si el trazo vuelve cerca del punto inicial (figura cerrada).
def isClosedStroke(points, x1, y1, x2, y2):
  width = max(x2 - x1, 1)
  height = max(y2 - y1, 1)
  gap = math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1])
  return gap < max(width, height) * 0.28


def contourFromStroke(points):
  array = np.array(points, dtype=np.int32).reshape(-1, 1, 2)
  return array


# 1.0 = círculo perfecto; valores bajos indican formas irregulares.
def circularityScore(contour):
  area = cv2.contourArea(contour)
  perimeter = cv2.arcLength(contour, True)
  if perimeter <= 0 or area <= 0:
    return 0.0
  return 4 * math.pi * area / (perimeter * perimeter)


def looksLikeHeart(points, x1, y1, x2, y2):
  width = max(x2 - x1, 1)
  height = max(y2 - y1, 1)
  aspect = height / width
  if not (0.75 < aspect < 1.35):
    return False

  centerX = (x1 + x2) / 2
  midY = y1 + height * 0.45
  topPoints = [point for point in points if point[1] < midY]
  bottomPoints = [point for point in points if point[1] >= midY]

  if len(topPoints) < 8 or len(bottomPoints) < 5:
    return False

  leftLobe = [point for point in topPoints if point[0] < centerX - width * 0.05]
  rightLobe = [point for point in topPoints if point[0] > centerX + width * 0.05]
  bottomTip = [
    point for point in bottomPoints
    if abs(point[0] - centerX) < width * 0.22
  ]

  return len(leftLobe) >= 4 and len(rightLobe) >= 4 and len(bottomTip) >= 3


# Clasifica un trazo cerrado en cuadrado, rectángulo, círculo o corazón.
def recognizeStroke(points, color, thickness):
  if len(points) < minStrokePoints:
    return None

  x1, y1, x2, y2 = strokeBounds(points)
  width = x2 - x1
  height = y2 - y1

  if width < shapeMinSize or height < shapeMinSize:
    return None

  if not isClosedStroke(points, x1, y1, x2, y2):
    return None

  contour = contourFromStroke(points)
  approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True)
  aspect = width / max(height, 1)

  if len(approx) == 4:
    if 0.82 < aspect < 1.18:
      return Shape('cuadrado', 'Cuadrado', x1, y1, x2, y2, color, thickness)
    return Shape('rectangulo', 'Rectangulo', x1, y1, x2, y2, color, thickness)

  circleScore = circularityScore(contour)
  if circleScore > 0.72 and 0.65 < aspect < 1.45:
    return Shape('circulo', 'Circulo', x1, y1, x2, y2, color, thickness)

  if looksLikeHeart(points, x1, y1, x2, y2):
    return Shape('corazon', 'Corazon', x1, y1, x2, y2, color, thickness)

  return None


# Pinta en negro sobre el lienzo para quitar el trazo libre antes de la figura.
def eraseStrokeFromCanvas(imgCanvas, points, thickness):
  for index in range(1, len(points)):
    cv2.line(
      imgCanvas,
      points[index - 1],
      points[index],
      (0, 0, 0),
      thickness + 8,
    )


# Curva paramétrica clásica del corazón, escalada al tamaño detectado.
def heartPoints(centerX, centerY, size):
  points = []
  for angle in np.linspace(0, 2 * math.pi, 80):
    x = 16 * math.sin(angle) ** 3
    y = (
      13 * math.cos(angle)
      - 5 * math.cos(2 * angle)
      - 2 * math.cos(3 * angle)
      - math.cos(4 * angle)
    )
    points.append([
      int(centerX + x * size / 34),
      int(centerY - y * size / 34),
    ])
  return np.array(points, dtype=np.int32)


def drawShape(canvas, shape):
  color = shape.color
  thickness = max(shape.thickness, 3)
  x1, y1, x2, y2 = shape.x1, shape.y1, shape.x2, shape.y2
  centerX = (x1 + x2) // 2
  centerY = (y1 + y2) // 2

  if shape.shapeType == 'circulo':
    radius = min(x2 - x1, y2 - y1) // 2
    cv2.circle(canvas, (centerX, centerY), max(radius, 1), color, thickness)

  elif shape.shapeType in ('rectangulo', 'cuadrado'):
    cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)

  elif shape.shapeType == 'corazon':
    size = min(x2 - x1, y2 - y1)
    points = heartPoints(centerX, centerY, size)
    cv2.polylines(canvas, [points], True, color, thickness)

  labelY = max(y1 - 10, headerHeight + 20)
  cv2.putText(
    canvas,
    shape.name,
    (x1, labelY),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.7,
    color,
    2,
  )


def renderCanvas(imgCanvas, shapes):
  composed = imgCanvas.copy()
  for shape in shapes:
    drawShape(composed, shape)
  return composed


def findShapeAt(shapes, x, y):
  for index in range(len(shapes) - 1, -1, -1):
    if shapes[index].containsPoint(x, y):
      return shapes[index]
  return None


def eraseShapesWithStroke(shapes, x1, y1, x2, y2, radius):
  return [
    shape
    for shape in shapes
    if not shape.intersectsLine(x1, y1, x2, y2, radius)
  ]


def finalizeStroke(imgCanvas, shapes, currentStroke, strokeThickness, drawColor):
  if len(currentStroke) < 2:
    return shapes, ''

  recognized = recognizeStroke(currentStroke, drawColor, strokeThickness)
  if recognized is None:
    return shapes, ''

  eraseStrokeFromCanvas(imgCanvas, currentStroke, strokeThickness)
  shapes.append(recognized)
  return shapes, f'{recognized.name.upper()} CORREGIDO'


# Superpone el dibujo sobre el video: negro del lienzo = transparente.
def mergeCanvasWithCamera(img, imgCanvas):
  imgGray = cv2.cvtColor(imgCanvas, cv2.COLOR_BGR2GRAY)
  _, imgInv = cv2.threshold(imgGray, 50, 255, cv2.THRESH_BINARY_INV)
  imgInv = cv2.cvtColor(imgInv, cv2.COLOR_GRAY2BGR)
  img = cv2.bitwise_and(img, imgInv)
  return cv2.bitwise_or(img, imgCanvas)


def overlayHeader(img, header):
  if header.shape[0] >= headerHeight and header.shape[1] >= canvasWidth:
    headerCrop = header[0:headerHeight, 0:canvasWidth]
  else:
    headerCrop = cv2.resize(header, (canvasWidth, headerHeight))

  img[0:headerHeight, 0:canvasWidth] = headerCrop


def drawHud(img, color, toolName, statusText):
  h, _, _ = img.shape
  hudY = headerHeight + 15

  cv2.rectangle(img, (10, hudY), (50, hudY + 40), color, -1)
  cv2.rectangle(img, (10, hudY), (50, hudY + 40), (255, 255, 255), 2)
  cv2.putText(
    img,
    toolName,
    (60, hudY + 28),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.8,
    (255, 255, 255),
    2,
  )

  gestures = [
    'Indice+medio = Seleccionar herramienta',
    'Solo indice = Dibujar (figuras cerradas se corrigen)',
    'Pinza sobre figura = Mover | Pinza vacia = Mover lienzo',
    'Borrador = Borrar trazos y figuras',
    '5 dedos = Limpiar todo',
  ]
  for index, text in enumerate(gestures):
    cv2.putText(
      img,
      text,
      (10, h - 110 + index * 22),
      cv2.FONT_HERSHEY_SIMPLEX,
      0.45,
      (200, 200, 200),
      1,
    )

  if statusText:
    cv2.putText(
      img,
      statusText,
      (img.shape[1] - 340, hudY + 25),
      cv2.FONT_HERSHEY_SIMPLEX,
      0.7,
      (0, 255, 255),
      2,
    )

  return img


def saveDrawing(imgCanvas, shapes):
  output = renderCanvas(imgCanvas, shapes)
  cv2.imwrite('mi_dibujo.png', output)
  print('Dibujo guardado en mi_dibujo.png')


def main():
  # Bucle principal: gestos de mano → dibujo, borrado, mover figuras o lienzo.
  folderPath = 'Header'
  overlayList = loadHeaderImages(folderPath)

  drawColor = brushColors[0]
  header = overlayList[0]
  toolIndex = 0

  cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
  cap.set(3, canvasWidth)
  cap.set(4, canvasHeight)

  detector = htm.handDetector(detectionCon=0.65, maxHands=1)

  xp, yp = 0, 0
  pinchPrevX, pinchPrevY = 0, 0
  lastToolChange = 0.0
  lastClear = 0.0
  statusText = ''
  statusUntil = 0.0
  shapes = []
  currentStroke = []
  strokeThickness = brushThickness
  isDrawing = False
  imgCanvas = np.zeros((canvasHeight, canvasWidth, 3), np.uint8)

  print('Dibuja figuras cerradas con el pincel y se corrigen automaticamente.')

  while True:
    success, img = cap.read()
    if not success:
      print('No se pudo leer la cámara.')
      break

    if cameraFlipCode is not None:
      img = cv2.flip(img, cameraFlipCode)

    img = detector.findHands(img)
    lmList, _ = detector.findPosition(img, draw=False)

    if time.time() > statusUntil:
      statusText = ''

    wasDrawing = isDrawing
    isDrawing = False

    if len(lmList) != 0:
      x1, y1 = lmList[8][1], lmList[8][2]
      fingers = detector.fingersUp()

      # Mano abierta (5 dedos): limpiar todo; va primero para no confundirse con índice+medio.
      if isOpenHand(fingers):
        xp, yp = 0, 0
        pinchPrevX, pinchPrevY = 0, 0
        now = time.time()
        if now - lastClear > clearCooldown:
          imgCanvas[:] = 0
          shapes = []
          currentStroke = []
          lastClear = now
          statusText = 'LIENZO LIMPIO'
          statusUntil = now + 1.5

      # Índice + medio: seleccionar herramienta en la barra superior.
      elif fingers[1] == 1 and fingers[2] == 1:
        xp, yp = 0, 0
        pinchPrevX, pinchPrevY = 0, 0
        selectedHeader, selectedColor, selectedIndex = selectTool(x1, y1, overlayList)

        if selectedHeader is not None:
          now = time.time()
          if now - lastToolChange > selectionCooldown:
            header = selectedHeader
            drawColor = selectedColor
            toolIndex = selectedIndex
            lastToolChange = now

      # Solo índice: dibujar o borrar según el color activo.
      elif fingers[1] == 1 and fingers[2] == 0:
        cv2.circle(img, (x1, y1), 15, drawColor, cv2.FILLED)
        pinchPrevX, pinchPrevY = 0, 0
        isDrawing = True

        if xp == 0 and yp == 0:
          xp, yp = x1, y1
          currentStroke = [(x1, y1)]
        else:
          currentStroke.append((x1, y1))

        if drawColor == (0, 0, 0):
          strokeThickness = eraserThickness
          shapes = eraseShapesWithStroke(shapes, xp, yp, x1, y1, eraserThickness)
        else:
          strokeThickness = getDynamicThickness(xp, yp, x1, y1)

        cv2.line(imgCanvas, (xp, yp), (x1, y1), drawColor, strokeThickness)
        xp, yp = x1, y1

      else:
        xp, yp = 0, 0
        isPinch, pinchX, pinchY = detector.detectPinch(
          pinchThreshold,
          releaseThreshold=pinchReleaseThreshold,
        )

        # Pinza: mover una figura o desplazar el lienzo completo.
        if isPinch and pinchY >= headerHeight:
          selectedShape = findShapeAt(shapes, pinchX, pinchY)

          if selectedShape is not None:
            statusText = f'MOVIENDO {selectedShape.name.upper()}'
            statusUntil = time.time() + 0.2
            if pinchPrevX == 0 and pinchPrevY == 0:
              pinchPrevX, pinchPrevY = pinchX, pinchY
            else:
              dx = pinchX - pinchPrevX
              dy = pinchY - pinchPrevY
              selectedShape.move(dx, dy)
              pinchPrevX, pinchPrevY = pinchX, pinchY
          else:
            statusText = 'MOVIENDO LIENZO'
            statusUntil = time.time() + 0.2
            if pinchPrevX == 0 and pinchPrevY == 0:
              pinchPrevX, pinchPrevY = pinchX, pinchY
            else:
              dx = pinchX - pinchPrevX
              dy = pinchY - pinchPrevY
              imgCanvas = np.roll(imgCanvas, dx, axis=1)
              imgCanvas = np.roll(imgCanvas, dy, axis=0)
              for shape in shapes:
                shape.move(dx, dy)
              pinchPrevX, pinchPrevY = pinchX, pinchY
        else:
          pinchPrevX, pinchPrevY = 0, 0

    # Al soltar el dedo, intentar convertir el trazo en figura geométrica.
    if wasDrawing and not isDrawing and drawColor != (0, 0, 0):
      shapes, message = finalizeStroke(
        imgCanvas,
        shapes,
        currentStroke,
        strokeThickness,
        drawColor,
      )
      if message:
        statusText = message
        statusUntil = time.time() + 1.8
      currentStroke = []

    if not isDrawing and not wasDrawing:
      currentStroke = []

    composedCanvas = renderCanvas(imgCanvas, shapes)
    img = mergeCanvasWithCamera(img, composedCanvas)
    overlayHeader(img, header)
    img = drawHud(img, drawColor, toolNames[toolIndex], statusText)

    cv2.imshow('HANC - Virtual Painter', img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
      break

  saveDrawing(imgCanvas, shapes)
  cap.release()
  cv2.destroyAllWindows()


if __name__ == '__main__':
  main()
