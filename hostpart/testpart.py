import qrcode
import json
import datetime
from bson import ObjectId
import logger as log
import pub
import config as cfg
import emailsend as em

class doorkey:
    doorID = 'default'
    passwd = 'default' 
    startTimetype = datetime.datetime.now()
    start = startTimetype.strftime("%Y-%m-%d, %H:%M:%S")
    expire_time = 10
    #endTimetype = datetime.datetime.now()+datetime.timedelta(days=1)
    endTimetype = datetime.datetime.now()+datetime.timedelta(minutes=expire_time)
    end = endTimetype.strftime("%Y-%m-%d, %H:%M:%S")
    logWritter = log.logger("./log.txt")

    def createKey(self):
        qrinfo = dict()
        qrinfo['doorID']=self.doorID
        qrinfo['passwd']=self.passwd
        qrinfo['start']=self.start
        qrinfo['end']=self.end

        #fileid = ObjectId.from_datetime(self.startTimetype)
        fileid = ObjectId()
        self.logWritter.info(fileid)
        if self.passwd == 'default':
            qrinfo['passwd']=str(fileid)

        qrinfo = json.dumps(qrinfo)

        img = qrcode.make(qrinfo)
        keypath=str(fileid)+'.png'
        img.save(keypath)
        return keypath, qrinfo

def main():
    oneKey = doorkey()
    oneKey.doorID = cfg.topic_name
    qrImage, qrInfo = oneKey.createKey()
    qrInfo = bytes(qrInfo, 'utf-8')
    pub.pub(cfg.project_id,cfg.topic_name,qrInfo)
    em.key_sender(key_path=qrImage, owner_address=cfg.email_to)

def test():
    oneKey = doorkey()

if __name__ == "__main__":
    main()