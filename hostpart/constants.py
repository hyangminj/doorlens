"""
Host Part Constants and Configuration
호스트 파트 상수 및 설정

Defines configurable constants for key generation and distribution.
키 생성 및 배포를 위한 설정 가능한 상수를 정의합니다.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import timezone

# =============================================================================
# Time Configuration
# 시간 설정
# =============================================================================

DEFAULT_EXPIRE_MINUTES = 10  # Default key expiration time / 기본 키 만료 시간
DATETIME_FORMAT = "%Y-%m-%d, %H:%M:%S"  # Standard datetime format / 표준 날짜시간 포맷
DATETIME_FORMAT_UTC = "%Y-%m-%dT%H:%M:%SZ"  # UTC datetime format / UTC 날짜시간 포맷

# =============================================================================
# Email Configuration
# 이메일 설정
# =============================================================================

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SUBJECT = "[KEY] your room key is delivered."
EMAIL_BODY = "Please use the attached QR code to access your room."

# =============================================================================
# File Configuration
# 파일 설정
# =============================================================================

DEFAULT_LOG_FILE = "./log.txt"
QR_IMAGE_FORMAT = "png"


@dataclass
class KeyGeneratorConfig:
    """
    Configuration for key generator.
    키 생성기 설정입니다.
    """
    door_id: str
    passwd: Optional[str] = None  # None = auto-generate / None = 자동 생성
    expire_minutes: int = DEFAULT_EXPIRE_MINUTES
    use_utc: bool = False  # Whether to use UTC for times / 시간에 UTC 사용 여부
    log_file: str = DEFAULT_LOG_FILE


@dataclass
class EmailConfig:
    """
    Configuration for email sending.
    이메일 전송 설정입니다.
    """
    smtp_host: str = SMTP_HOST
    smtp_port: int = SMTP_PORT
    sender_id: str = ""
    sender_password: str = ""
    subject: str = EMAIL_SUBJECT
    body: str = EMAIL_BODY


@dataclass
class PubSubConfig:
    """
    Configuration for Pub/Sub publishing.
    Pub/Sub 게시 설정입니다.
    """
    project_id: str
    topic_name: str
