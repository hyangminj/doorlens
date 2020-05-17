import pyzbar.pyzbar as pyzbar
import cv2
import json
import os
import logger
import sys
from datetime import datetime

log = logger.logger(log_path="./logs.txt")

cap = cv2.VideoCapture(0)

#text = '%s (%s)' % (barcode_data, barcode_type)
#print(barcode_data)
def read_key(key_path):
  if os.path.isfile(key_path):
    with open(key_path,'r') as f:
      existKey=json.load(f)
  else:
    log.error("keyfile is not exist")
    sys.exit()
  return existKey

existKey = read_key("keyinfo.json")
pre_pass = existKey["passwd"]
      
i = 0
#while(cap.isOpened()):
starttime = datetime.strptime(existKey['start'], "%Y-%m-%d, %H:%M:%S")
endtime = datetime.strptime(existKey['end'], "%Y-%m-%d, %H:%M:%S")
now = datetime.now()

while(starttime < now and endtime > now):
  ret, img = cap.read()

  if not ret:
    continue

  gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
     
  decoded = pyzbar.decode(gray)

  for d in decoded: 
    x, y, w, h = d.rect

    barcode_data = d.data.decode("utf-8")
    barcode_type = d.type

    #cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

    readKey = json.loads(barcode_data)
    for k,v in existKey.items():
      if readKey[k] == v:
        continue
      else:
        log.error("key is not matched, key : %s, value : %s, readed key : %s" % (k,v,readKey[k]))
        break
    #doorOpen()
    print("doorOpen")

    existKey = read_key("keyinfo.json")
    if existKey['passwd'] != pre_pass:
      sys.exit()
    #cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA)

  now = datetime.now()
  #cv2.imshow('img', img)

##  key = cv2.waitKey(1)
##  if key == ord('q'):
##    break
##  elif key == ord('s'):
##    i += 1
##    cv2.imwrite('c_%03d.jpg' % i, img)

cap.release()
cv2.destroyAllWindows()
sys.exit()