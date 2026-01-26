"""
Email Sender Module (Refactored)
이메일 전송 모듈 (리팩토링)

Enhanced email sending with proper error handling and configuration.
적절한 에러 처리 및 설정이 포함된 향상된 이메일 전송입니다.
"""

import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
from typing import Optional
from dataclasses import dataclass

from constants import EmailConfig, SMTP_HOST, SMTP_PORT, EMAIL_SUBJECT, EMAIL_BODY


class EmailSendError(Exception):
    """Exception for email sending errors / 이메일 전송 오류 예외"""
    pass


class EmailSender:
    """
    Email sender for QR code key distribution.
    QR 코드 키 배포를 위한 이메일 전송기입니다.

    Features:
    - Proper SMTP connection management (context manager)
    - Detailed error handling
    - Configurable templates

    기능:
    - 적절한 SMTP 연결 관리 (컨텍스트 관리자)
    - 상세한 에러 처리
    - 설정 가능한 템플릿
    """

    def __init__(
        self,
        config: EmailConfig,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize email sender.
        이메일 전송기를 초기화합니다.

        Args:
            config (EmailConfig): Email configuration / 이메일 설정
            logger (logging.Logger, optional): Logger instance / 로거 인스턴스
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Validate email configuration.
        이메일 설정을 검증합니다.

        Raises:
            ValueError: If configuration is invalid / 설정이 유효하지 않을 경우
        """
        if not self.config.sender_id:
            raise ValueError("sender_id cannot be empty / sender_id는 비워둘 수 없습니다")
        if not self.config.sender_password:
            raise ValueError("sender_password cannot be empty / sender_password는 비워둘 수 없습니다")

    def send_key(
        self,
        key_path: str,
        recipient_address: str,
        subject: Optional[str] = None,
        body: Optional[str] = None
    ) -> bool:
        """
        Send QR code key to recipient.
        수신자에게 QR 코드 키를 전송합니다.

        Args:
            key_path (str): Path to QR code image / QR 코드 이미지 경로
            recipient_address (str): Recipient email address / 수신자 이메일 주소
            subject (str, optional): Email subject / 이메일 제목
            body (str, optional): Email body / 이메일 본문

        Returns:
            bool: True if sent successfully / 전송 성공 시 True

        Raises:
            EmailSendError: If sending fails / 전송 실패 시
        """
        if not os.path.isfile(key_path):
            raise EmailSendError(f"Key file not found: {key_path}")

        # Security: Validate path to prevent path traversal attacks
        # 보안: 경로 탐색 공격을 방지하기 위한 경로 검증
        abs_key_path = os.path.abspath(key_path)
        # Ensure the file is within the current working directory or explicitly allowed paths
        # 파일이 현재 작업 디렉토리 또는 명시적으로 허용된 경로 내에 있는지 확인
        cwd = os.path.abspath(os.getcwd())
        if not abs_key_path.startswith(cwd + os.sep) and not abs_key_path == cwd:
            # Check if it's a direct file in cwd
            if os.path.dirname(abs_key_path) != cwd:
                self.logger.warning(f"Potential path traversal attempt: {key_path}")
                raise EmailSendError(
                    f"Invalid key path: file must be within the working directory. "
                    f"잘못된 키 경로: 파일은 작업 디렉토리 내에 있어야 합니다."
                )

        subject = subject or self.config.subject
        body = body or self.config.body

        server = None
        try:
            # Create message
            # 메시지 생성
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = self.config.sender_id
            msg['To'] = recipient_address

            # Add body
            # 본문 추가
            msg.attach(MIMEText(body, 'plain'))

            # Attach QR code image
            # QR 코드 이미지 첨부
            with open(key_path, 'rb') as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)

                filename = os.path.basename(key_path)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"'
                )
                msg.attach(part)

            # Connect and send
            # 연결 및 전송
            self.logger.info(f"Connecting to SMTP server {self.config.smtp_host}:{self.config.smtp_port}")

            server = smtplib.SMTP(
                host=self.config.smtp_host,
                port=self.config.smtp_port
            )
            server.ehlo()
            server.starttls()
            server.login(self.config.sender_id, self.config.sender_password)

            server.sendmail(
                from_addr=msg['From'],
                to_addrs=[recipient_address],
                msg=msg.as_string()
            )

            self.logger.info(f"Email sent successfully to {recipient_address}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP authentication failed: {e}")
            raise EmailSendError(
                "Authentication failed. Please check your email credentials. "
                "If using Gmail, ensure you're using an App Password. "
                "인증 실패. 이메일 자격 증명을 확인하세요. "
                "Gmail을 사용하는 경우 앱 비밀번호를 사용하고 있는지 확인하세요."
            )

        except smtplib.SMTPConnectError as e:
            self.logger.error(f"SMTP connection failed: {e}")
            raise EmailSendError(
                f"Failed to connect to SMTP server: {self.config.smtp_host}:{self.config.smtp_port}"
            )

        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP error: {e}")
            raise EmailSendError(f"SMTP error: {e}")

        except Exception as e:
            self.logger.error(f"Email send error: {e}")
            raise EmailSendError(f"Failed to send email: {e}")

        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass


# Backward compatibility function
# 하위 호환성 함수
def key_sender(key_path: str, owner_address: str) -> None:
    """
    Legacy function for backward compatibility.
    하위 호환성을 위한 레거시 함수입니다.

    Args:
        key_path (str): Path to QR code image / QR 코드 이미지 경로
        owner_address (str): Recipient email address / 수신자 이메일 주소
    """
    try:
        import config as cfg

        email_config = EmailConfig(
            sender_id=cfg.email_id,
            sender_password=cfg.email_passwd
        )

        sender = EmailSender(email_config)
        sender.send_key(key_path, owner_address)

    except ImportError:
        raise EmailSendError(
            "config.py not found. Please create config.py with email_id and email_passwd"
        )
