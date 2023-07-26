import cv2
import pandas as pd
from ultralytics import YOLO
from tracker import *
import cvzone

model = YOLO('model/model.pt')
tracker = Tracker()

Class_M = ['person']

persondown = {}
counter1 = []
personup = {}
counter2 = []
cy1 = 199
cy2 = 230
offset = 6

def v_count(cap):
    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if count % 3 == 0:
            frame = cv2.resize(frame, (1020, 500))
            results = model.predict(frame)
            a = results[0].boxes.data
            px = pd.DataFrame(a).astype("float")

            list = []
            for index, row in px.iterrows():
                x1 = int(row[0])
                y1 = int(row[1])
                x2 = int(row[2])
                y2 = int(row[3])
                d = int(row[5])

                c = Class_M[d]
                if 'person' in c:
                    list.append([x1, y1, x2, y2])

            bbox_id = tracker.update(list)
            for bbox in bbox_id:
                x3, y3, x4, y4, id = bbox
                cx = int(x3 + x4) // 2
                cy = int(y3 + y4) // 2
                cv2.circle(frame, (cx, cy), 4, (255, 0, 255), -1)

                if cy1 < (cy + offset) and cy1 > (cy - offset):
                    cv2.rectangle(frame, (x3, y3), (x4, y4), (0, 0, 255), 2)
                    cvzone.putTextRect(frame, f'{id}', (x3, y3), 1, 2)
                    persondown[id] = (cx, cy)

                if id in persondown:
                    if cy2 < (cy + offset) and cy2 > (cy - offset):
                        cv2.rectangle(frame, (x3, y3), (x4, y4), (0, 255, 255), 2)
                        cvzone.putTextRect(frame, f'{id}', (x3, y3), 1, 2)
                        if counter1.count(id) == 0:
                            counter1.append(id)

                if cy2 < (cy + offset) and cy2 > (cy - offset):
                    cv2.rectangle(frame, (x3, y3), (x4, y4), (0, 0, 255), 2)
                    cvzone.putTextRect(frame, f'{id}', (x3, y3), 1, 2)
                    personup[id] = (cx, cy)

                if id in personup:
                    if cy1 < (cy + offset) and cy1 > (cy - offset):
                        cv2.rectangle(frame, (x3, y3), (x4, y4), (0, 255, 255), 2)
                        cvzone.putTextRect(frame, f'{id}', (x3, y3), 1, 2)
                        if counter2.count(id) == 0:
                            counter2.append(id)

            cv2.line(frame, (3, cy1), (1018, cy1), (0, 255, 0), 2)
            cv2.line(frame, (5, cy2), (1019, cy2), (0, 255, 255), 2)

            down = len(counter1)
            up = len(counter2)
            total = down - up
            cvzone.putTextRect(frame, f'Masuk={down}', (50, 60), 2, 2)
            cvzone.putTextRect(frame, f'Keluar={up}', (50, 160), 2, 2)
            cvzone.putTextRect(frame, f'total={total}', (50, 300), 2, 2)

            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

        count += 1

def get_counter():
    down = len(counter1)
    up = len(counter2)
    total = down - up

    return down, up, total