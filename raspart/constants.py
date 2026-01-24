"""
Constants and Configuration Module
상수 및 설정 모듈

Defines all configurable constants for the DoorLens system.
DoorLens 시스템의 모든 설정 가능한 상수를 정의합니다.
"""

from dataclasses import dataclass
from typing import Optional
import os

# =============================================================================
# GPIO Configuration
# GPIO 설정
# =============================================================================

DEFAULT_GPIO_PIN = 17  # Default GPIO pin for door lock / 도어락용 기본 GPIO 핀
GPIO_MODE_BCM = "BCM"  # Use BCM pin numbering / BCM 핀 번호 사용

# =============================================================================
# Timing Configuration
# 타이밍 설정
# =============================================================================

UNLOCK_DURATION_SECONDS = 5  # How long to keep door unlocked / 도어 잠금 해제 유지 시간
RATE_LIMIT_MINUTES = 1  # Minimum time between unlocks / 잠금 해제 간 최소 시간
INITIAL_RATE_LIMIT_OFFSET_MINUTES = 10  # Initial offset to allow first unlock / 첫 잠금 해제 허용을 위한 초기 오프셋

# =============================================================================
# File Paths
# 파일 경로
# =============================================================================

DEFAULT_KEY_FILE = "keyinfo.json"  # Default key info file / 기본 키 정보 파일
DEFAULT_LOG_FILE = "./logs.txt"  # Default log file / 기본 로그 파일

# =============================================================================
# Camera Configuration
# 카메라 설정
# =============================================================================

DEFAULT_CAMERA_INDEX = 0  # Default camera device index / 기본 카메라 장치 인덱스
CAMERA_RETRY_DELAY_SECONDS = 1  # Delay before retrying camera / 카메라 재시도 전 대기 시간

# =============================================================================
# Time Format
# 시간 포맷
# =============================================================================

DATETIME_FORMAT = "%Y-%m-%d, %H:%M:%S"  # Standard datetime format / 표준 날짜시간 포맷
DATETIME_FORMAT_UTC = "%Y-%m-%dT%H:%M:%SZ"  # UTC datetime format / UTC 날짜시간 포맷


@dataclass
class DoorConfig:
    """
    Configuration for a single door.
    단일 도어에 대한 설정입니다.

    Attributes:
        door_id (str): Unique identifier for the door / 도어의 고유 식별자
        gpio_pin (int): GPIO pin number for this door / 이 도어의 GPIO 핀 번호
        unlock_duration (int): Seconds to keep door unlocked / 도어 잠금 해제 유지 시간(초)
        rate_limit_minutes (int): Minimum minutes between unlocks / 잠금 해제 간 최소 시간(분)
        key_file (str): Path to key info file / 키 정보 파일 경로
        log_file (str): Path to log file / 로그 파일 경로
    """
    door_id: str
    gpio_pin: int = DEFAULT_GPIO_PIN
    unlock_duration: int = UNLOCK_DURATION_SECONDS
    rate_limit_minutes: int = RATE_LIMIT_MINUTES
    key_file: str = DEFAULT_KEY_FILE
    log_file: str = DEFAULT_LOG_FILE
    camera_index: int = DEFAULT_CAMERA_INDEX


def load_door_config(door_id: str, config_path: Optional[str] = None) -> DoorConfig:
    """
    Load door configuration from file or return defaults.
    파일에서 도어 설정을 로드하거나 기본값을 반환합니다.

    Args:
        door_id (str): Door identifier / 도어 식별자
        config_path (str, optional): Path to config file / 설정 파일 경로

    Returns:
        DoorConfig: Door configuration object / 도어 설정 객체
    """
    # For now, return default config with door_id
    # 현재는 door_id로 기본 설정 반환
    return DoorConfig(door_id=door_id)


def validate_config(config: DoorConfig) -> bool:
    """
    Validate door configuration.
    도어 설정을 검증합니다.

    Args:
        config (DoorConfig): Configuration to validate / 검증할 설정

    Returns:
        bool: True if valid, False otherwise / 유효하면 True, 아니면 False

    Raises:
        ValueError: If configuration is invalid / 설정이 유효하지 않을 경우
    """
    if not config.door_id:
        raise ValueError("door_id cannot be empty / door_id는 비워둘 수 없습니다")

    if config.gpio_pin < 0 or config.gpio_pin > 27:
        raise ValueError(f"Invalid GPIO pin: {config.gpio_pin}. Must be 0-27 / 잘못된 GPIO 핀: {config.gpio_pin}. 0-27이어야 합니다")

    if config.unlock_duration <= 0:
        raise ValueError(f"unlock_duration must be positive / unlock_duration은 양수여야 합니다")

    if config.rate_limit_minutes < 0:
        raise ValueError(f"rate_limit_minutes cannot be negative / rate_limit_minutes는 음수일 수 없습니다")

    return True
