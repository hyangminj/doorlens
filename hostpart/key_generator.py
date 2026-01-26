"""
Key Generator Module (Refactored)
키 생성기 모듈 (리팩토링)

Enhanced key generation with UTC support, improved validation, and audit trail.
UTC 지원, 개선된 검증 및 감사 추적이 포함된 향상된 키 생성입니다.
"""

import json
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, asdict
from bson import ObjectId
import qrcode

from constants import (
    KeyGeneratorConfig,
    DATETIME_FORMAT,
    DATETIME_FORMAT_UTC,
    DEFAULT_EXPIRE_MINUTES
)


@dataclass
class GeneratedKey:
    """
    Generated key data structure.
    생성된 키 데이터 구조입니다.
    """
    door_id: str
    passwd: str
    start: str
    end: str
    start_utc: Optional[str] = None
    end_utc: Optional[str] = None
    key_id: Optional[str] = None

    def to_dict(self, include_utc: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        JSON 직렬화를 위해 딕셔너리로 변환합니다.
        """
        result = {
            'doorID': self.door_id,
            'passwd': self.passwd,
            'start': self.start,
            'end': self.end
        }

        if include_utc and self.start_utc and self.end_utc:
            result['start_utc'] = self.start_utc
            result['end_utc'] = self.end_utc

        return result

    def to_json(self, include_utc: bool = False) -> str:
        """Convert to JSON string / JSON 문자열로 변환"""
        return json.dumps(self.to_dict(include_utc))


class KeyGenerator:
    """
    QR Code Key Generator with enhanced features.
    향상된 기능을 갖춘 QR 코드 키 생성기입니다.

    Features:
    - Auto-generated secure passwords
    - UTC time support for cross-timezone deployments
    - Audit trail logging
    - Configurable expiration

    기능:
    - 자동 생성된 안전한 비밀번호
    - 교차 시간대 배포를 위한 UTC 시간 지원
    - 감사 추적 로깅
    - 설정 가능한 만료
    """

    def __init__(
        self,
        config: KeyGeneratorConfig,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize key generator.
        키 생성기를 초기화합니다.

        Args:
            config (KeyGeneratorConfig): Generator configuration / 생성기 설정
            logger (logging.Logger, optional): Logger instance / 로거 인스턴스
        """
        self.config = config
        self.logger = logger or self._setup_logger()
        self._generated_keys: list[GeneratedKey] = []

    def _setup_logger(self) -> logging.Logger:
        """Set up logger instance."""
        logger = logging.getLogger("KeyGenerator")
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '[%(levelname)s] %(asctime)s (%(filename)s:%(lineno)d) > %(message)s'
        )

        file_handler = logging.FileHandler(self.config.log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    def _generate_password(self) -> str:
        """
        Generate a secure random password.
        안전한 랜덤 비밀번호를 생성합니다.

        Returns:
            str: 24-character hex string from ObjectId / ObjectId의 24자 16진수 문자열
        """
        return str(ObjectId())

    def _get_current_time(self) -> datetime:
        """Get current time based on UTC setting."""
        if self.config.use_utc:
            return datetime.now(timezone.utc)
        return datetime.now()

    def generate_key(self) -> GeneratedKey:
        """
        Generate a new key.
        새 키를 생성합니다.

        Returns:
            GeneratedKey: Generated key data / 생성된 키 데이터
        """
        now = self._get_current_time()
        end = now + timedelta(minutes=self.config.expire_minutes)

        # Generate password if not provided
        # 제공되지 않은 경우 비밀번호 생성
        passwd = self.config.passwd or self._generate_password()

        # Generate unique key ID
        # 고유 키 ID 생성
        key_id = str(ObjectId())

        # Format times
        # 시간 포맷
        if self.config.use_utc:
            start_str = now.strftime(DATETIME_FORMAT_UTC)
            end_str = end.strftime(DATETIME_FORMAT_UTC)
            # Also provide local format for compatibility
            # 호환성을 위해 로컬 포맷도 제공
            start_local = now.replace(tzinfo=None).strftime(DATETIME_FORMAT)
            end_local = end.replace(tzinfo=None).strftime(DATETIME_FORMAT)
        else:
            start_str = now.strftime(DATETIME_FORMAT)
            end_str = end.strftime(DATETIME_FORMAT)
            start_local = start_str
            end_local = end_str

        key = GeneratedKey(
            door_id=self.config.door_id,
            passwd=passwd,
            start=start_local,  # Always use local format for backward compatibility
            end=end_local,
            start_utc=start_str if self.config.use_utc else None,
            end_utc=end_str if self.config.use_utc else None,
            key_id=key_id
        )

        self._generated_keys.append(key)
        self.logger.info(f"Generated key: {key_id} for door: {self.config.door_id}")

        return key

    def create_qr_image(
        self,
        key: GeneratedKey,
        output_dir: str = ".",
        include_utc: bool = False
    ) -> str:
        """
        Create QR code image from key.
        키에서 QR 코드 이미지를 생성합니다.

        Args:
            key (GeneratedKey): Key to encode / 인코딩할 키
            output_dir (str): Output directory / 출력 디렉토리
            include_utc (bool): Include UTC times in QR data / QR 데이터에 UTC 시간 포함

        Returns:
            str: Path to generated QR code image / 생성된 QR 코드 이미지 경로

        Raises:
            ValueError: If output_dir is invalid / output_dir가 유효하지 않을 경우
        """
        # Validate and create output directory if it doesn't exist
        # 출력 디렉토리가 존재하지 않으면 검증 및 생성
        if not output_dir:
            raise ValueError("output_dir cannot be empty / output_dir는 비워둘 수 없습니다")

        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                self.logger.info(f"Created output directory: {output_dir}")
            except OSError as e:
                raise ValueError(f"Failed to create output directory: {output_dir}. Error: {e}")

        # Create QR code
        # QR 코드 생성
        qr_data = key.to_json(include_utc=include_utc)
        img = qrcode.make(qr_data)

        # Save image
        # 이미지 저장
        filename = f"{key.key_id}.png"
        filepath = os.path.join(output_dir, filename)
        img.save(filepath)

        self.logger.info(f"QR code saved: {filepath}")
        return filepath

    def generate_and_create_qr(
        self,
        output_dir: str = "."
    ) -> Tuple[str, GeneratedKey]:
        """
        Generate key and create QR code image.
        키를 생성하고 QR 코드 이미지를 생성합니다.

        Args:
            output_dir (str): Output directory for QR image / QR 이미지 출력 디렉토리

        Returns:
            Tuple[str, GeneratedKey]: (QR image path, generated key) /
                                      (QR 이미지 경로, 생성된 키)
        """
        key = self.generate_key()
        qr_path = self.create_qr_image(key, output_dir)
        return qr_path, key

    def get_generated_keys(self) -> list[GeneratedKey]:
        """
        Get list of generated keys (audit trail).
        생성된 키 목록을 가져옵니다 (감사 추적).

        Returns:
            list[GeneratedKey]: List of generated keys / 생성된 키 목록
        """
        return self._generated_keys.copy()


# Backward compatibility with old DoorKey class
# 이전 DoorKey 클래스와의 하위 호환성
class DoorKey:
    """
    Legacy DoorKey class for backward compatibility.
    하위 호환성을 위한 레거시 DoorKey 클래스입니다.
    """

    def __init__(
        self,
        door_id: str = 'default',
        passwd: str = 'default',
        expire_minutes: int = 10
    ):
        """Initialize DoorKey (legacy interface)."""
        self.door_id = door_id
        self.passwd = passwd if passwd != 'default' else None
        self.expire_time = expire_minutes

        config = KeyGeneratorConfig(
            door_id=door_id,
            passwd=self.passwd,
            expire_minutes=expire_minutes
        )
        self._generator = KeyGenerator(config)

        # Set time attributes for backward compatibility
        # 하위 호환성을 위한 시간 속성 설정
        now = datetime.now()
        self.start_time_type = now
        self.end_time_type = now + timedelta(minutes=expire_minutes)
        self.start = now.strftime(DATETIME_FORMAT)
        self.end = self.end_time_type.strftime(DATETIME_FORMAT)

    def create_key(self) -> Tuple[str, str]:
        """
        Create key (legacy interface).
        키를 생성합니다 (레거시 인터페이스).

        Returns:
            Tuple[str, str]: (QR image path, key JSON) / (QR 이미지 경로, 키 JSON)
        """
        qr_path, key = self._generator.generate_and_create_qr()
        return qr_path, key.to_json()
