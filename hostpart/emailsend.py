import smtplib
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
import io
import config as cfg

def key_sender(key_path, owner_address):
    server = smtplib.SMTP(host="smtp.gmail.com", port=587)
    server.ehlo()
    server.starttls()
    
    server.login(cfg.email_id, cfg.email_passwd)
    
    msg = MIMEBase('multipart', 'mixed')
    msg['Subject'] = '[KEY] your room key is delivered.'
    msg['From'] = cfg.email_id+"@gmail.com"
    msg['To'] = owner_address 
    #msg['Cc'] = cfg.email_cc
    
    msg.attach(MIMEText("Please use below key."))
    with open(key_path, 'rb') as f :
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", 'attachment', filename=key_path)
        msg.attach(part)
    server.sendmail(from_addr=msg['From'], to_addrs=msg['To'], msg=msg.as_string() )
