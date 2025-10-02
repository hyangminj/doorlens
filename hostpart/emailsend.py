"""
Email Sender Module
이메일 전송 모듈

Sends QR code key images to users via Gmail SMTP.
Gmail SMTP를 통해 사용자에게 QR 코드 키 이미지를 전송합니다.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
import io
import config as cfg


def key_sender(key_path, owner_address):
    """
    Send QR code key image to user via email.
    이메일을 통해 사용자에게 QR 코드 키 이미지를 전송합니다.

    Args:
        key_path (str): Path to the QR code image file
                       QR 코드 이미지 파일 경로
        owner_address (str): Email address of the recipient
                            수신자의 이메일 주소

    Raises:
        SMTPException: If email sending fails
                      이메일 전송이 실패할 경우
    """
    # Connect to Gmail SMTP server
    # Gmail SMTP 서버에 연결
    server = smtplib.SMTP(host="smtp.gmail.com", port=587)
    server.ehlo()

    # Start TLS encryption
    # TLS 암호화 시작
    server.starttls()

    # Login with Gmail credentials from config
    # config의 Gmail 인증 정보로 로그인
    server.login(cfg.email_id, cfg.email_passwd)

    # Create multipart message
    # 멀티파트 메시지 생성
    msg = MIMEBase('multipart', 'mixed')
    msg['Subject'] = '[KEY] your room key is delivered.'
    msg['From'] = cfg.email_id + "@gmail.com"
    msg['To'] = owner_address

    # Add text body to message
    # 메시지에 텍스트 본문 추가
    msg.attach(MIMEText("Please use below key."))

    # Attach QR code image file
    # QR 코드 이미지 파일 첨부
    with open(key_path, 'rb') as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", 'attachment', filename=key_path)
        msg.attach(part)

    # Send email
    # 이메일 전송
    server.sendmail(
        from_addr=msg['From'],
        to_addrs=msg['To'],
        msg=msg.as_string()
    )

    # Close server connection
    # 서버 연결 종료
    server.quit()
