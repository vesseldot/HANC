# Detección de manos con MediaPipe: landmarks, dedos y gesto de pinza.
import cv2
import mediapipe as mp
import time
import math


class handDetector:
  # tipIds: punta de pulgar, índice, medio, anular y meñique.
  def __init__(self, mode=False, maxHands=2, detectionCon=0.5, trackCon=0.5):
    self.mode = mode
    self.maxHands = maxHands
    self.detectionCon = detectionCon
    self.trackCon = trackCon

    self.mpHands = mp.solutions.hands
    self.hands = self.mpHands.Hands(
      static_image_mode=self.mode,
      max_num_hands=self.maxHands,
      min_detection_confidence=self.detectionCon,
      min_tracking_confidence=self.trackCon,
    )
    self.mpDraw = mp.solutions.drawing_utils
    self.tipIds = [4, 8, 12, 16, 20]
    self.results = None
    self.lmList = []

  def findHands(self, img, draw=True):
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    self.results = self.hands.process(imgRGB)

    if self.results.multi_hand_landmarks:
      for handLms in self.results.multi_hand_landmarks:
        if draw:
          self.mpDraw.draw_landmarks(
            img, handLms, self.mpHands.HAND_CONNECTIONS
          )

    return img

  def findPosition(self, img, handNo=0, draw=True):
    xList = []
    yList = []
    bbox = []
    self.lmList = []

    if self.results and self.results.multi_hand_landmarks:
      myHand = self.results.multi_hand_landmarks[handNo]
      h, w, _ = img.shape

      for id, lm in enumerate(myHand.landmark):
        cx, cy = int(lm.x * w), int(lm.y * h)
        xList.append(cx)
        yList.append(cy)
        self.lmList.append([id, cx, cy])

        if draw:
          cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)

      xmin, xmax = min(xList), max(xList)
      ymin, ymax = min(yList), max(yList)
      bbox = xmin, ymin, xmax, ymax

      if draw:
        cv2.rectangle(
          img,
          (xmin - 20, ymin - 20),
          (xmax + 20, ymax + 20),
          (0, 255, 0),
          2,
        )

    return self.lmList, bbox

  # Devuelve [pulgar, índice, medio, anular, meñique]; 1 = levantado.
  def fingersUp(self):
    fingers = []

    if not self.lmList:
      return fingers

    # El pulgar se compara en X; el resto de dedos en Y (eje vertical).
    if self.lmList[self.tipIds[0]][1] > self.lmList[self.tipIds[0] - 1][1]:
      fingers.append(1)
    else:
      fingers.append(0)

    for id in range(1, 5):
      if self.lmList[self.tipIds[id]][2] < self.lmList[self.tipIds[id] - 2][2]:
        fingers.append(1)
      else:
        fingers.append(0)

    return fingers

  def findDistance(self, p1, p2, img, draw=True, r=15, t=3):
    x1, y1 = self.lmList[p1][1:]
    x2, y2 = self.lmList[p2][1:]
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

    if draw:
      cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), t)
      cv2.circle(img, (x1, y1), r, (255, 0, 255), cv2.FILLED)
      cv2.circle(img, (x2, y2), r, (255, 0, 255), cv2.FILLED)
      cv2.circle(img, (cx, cy), r, (0, 0, 255), cv2.FILLED)

    length = math.hypot(x2 - x1, y2 - y1)
    return length, img, [x1, y1, x2, y2, cx, cy]

  # True si pulgar e índice están lo bastante cerca (gesto de pinza).
  def detectPinch(self, threshold=40):
    if len(self.lmList) < 9:
      return False, 0, 0

    thumbX, thumbY = self.lmList[4][1], self.lmList[4][2]
    indexX, indexY = self.lmList[8][1], self.lmList[8][2]
    distance = math.hypot(indexX - thumbX, indexY - thumbY)
    centerX = (thumbX + indexX) // 2
    centerY = (thumbY + indexY) // 2

    return distance < threshold, centerX, centerY

  def findAllHandPositions(self, img, draw=False):
    handsData = []

    if not self.results or not self.results.multi_hand_landmarks:
      return handsData

    for handNo in range(len(self.results.multi_hand_landmarks)):
      lmList, bbox = self._extractLandmarks(img, handNo, draw)
      handsData.append({
        'lmList': lmList,
        'bbox': bbox,
        'fingers': self.fingersUpFromLmList(lmList),
      })

    if handsData:
      self.lmList = handsData[0]['lmList']

    return handsData

  def _extractLandmarks(self, img, handNo=0, draw=False):
    xList = []
    yList = []
    bbox = []
    lmList = []
    myHand = self.results.multi_hand_landmarks[handNo]
    h, w, _ = img.shape

    for id, lm in enumerate(myHand.landmark):
      cx, cy = int(lm.x * w), int(lm.y * h)
      xList.append(cx)
      yList.append(cy)
      lmList.append([id, cx, cy])

      if draw:
        cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)

    xmin, xmax = min(xList), max(xList)
    ymin, ymax = min(yList), max(yList)
    bbox = xmin, ymin, xmax, ymax

    if draw:
      cv2.rectangle(
        img,
        (xmin - 20, ymin - 20),
        (xmax + 20, ymax + 20),
        (0, 255, 0),
        2,
      )

    return lmList, bbox

  def fingersUpFromLmList(self, lmList):
    fingers = []

    if not lmList:
      return fingers

    if lmList[self.tipIds[0]][1] > lmList[self.tipIds[0] - 1][1]:
      fingers.append(1)
    else:
      fingers.append(0)

    for id in range(1, 5):
      if lmList[self.tipIds[id]][2] < lmList[self.tipIds[id] - 2][2]:
        fingers.append(1)
      else:
        fingers.append(0)

    return fingers


def main():
  pTime = 0
  cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
  detector = handDetector()

  while True:
    success, img = cap.read()
    if not success:
      break

    img = cv2.flip(img, 1)
    img = detector.findHands(img)
    lmList, bbox = detector.findPosition(img)

    if len(lmList) != 0:
      print(lmList[8])

    cTime = time.time()
    fps = 1 / (cTime - pTime) if cTime - pTime > 0 else 0
    pTime = cTime
    cv2.putText(
      img,
      str(int(fps)),
      (10, 70),
      cv2.FONT_HERSHEY_PLAIN,
      3,
      (255, 0, 255),
      3,
    )

    cv2.imshow("Image", img)
    if cv2.waitKey(1) & 0xFF == ord("q"):
      break

  cap.release()
  cv2.destroyAllWindows()


if __name__ == "__main__":
  main()
