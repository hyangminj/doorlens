"""
Door Controller Module
도어 컨트롤러 모듈

Abstraction layer for GPIO-based door lock control.
GPIO 기반 도어락 제어를 위한 추상화 레이어입니다.
"""

import time
import signal
import logging
from typing import Optional, Callable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

from constants import (
    DEFAULT_GPIO_PIN,
    UNLOCK_DURATION_SECONDS,
    RATE_LIMIT_MINUTES,
    INITIAL_RATE_LIMIT_OFFSET_MINUTES
)


class DoorControllerBase(ABC):
    """
    Abstract base class for door controllers.
    도어 컨트롤러를 위한 추상 기본 클래스입니다.
    """

    @abstractmethod
    def unlock(self) -> bool:
        """Unlock the door. Returns True on success."""
        pass

    @abstractmethod
    def lock(self) -> bool:
        """Lock the door. Returns True on success."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass


class GPIODoorController(DoorControllerBase):
    """
    GPIO-based door controller for Raspberry Pi.
    라즈베리파이용 GPIO 기반 도어 컨트롤러입니다.

    Attributes:
        gpio_pin (int): GPIO pin number for door control / 도어 제어용 GPIO 핀 번호
        unlock_duration (int): Seconds to keep door unlocked / 도어 잠금 해제 유지 시간(초)
        rate_limit_minutes (int): Minimum minutes between unlocks / 잠금 해제 간 최소 시간(분)
        logger (logging.Logger): Logger instance / 로거 인스턴스
    """

    def __init__(
        self,
        gpio_pin: int = DEFAULT_GPIO_PIN,
        unlock_duration: int = UNLOCK_DURATION_SECONDS,
        rate_limit_minutes: int = RATE_LIMIT_MINUTES,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize GPIO door controller.
        GPIO 도어 컨트롤러를 초기화합니다.

        Args:
            gpio_pin (int): GPIO pin number / GPIO 핀 번호
            unlock_duration (int): Seconds to keep unlocked / 잠금 해제 유지 시간(초)
            rate_limit_minutes (int): Rate limit in minutes / 분 단위 속도 제한
            logger (logging.Logger, optional): Logger instance / 로거 인스턴스
        """
        self.gpio_pin = gpio_pin
        self.unlock_duration = unlock_duration
        self.rate_limit_minutes = rate_limit_minutes
        self.logger = logger or logging.getLogger(__name__)

        # Rate limiting state
        # 속도 제한 상태
        self._last_unlock_time: Optional[datetime] = None
        self._initialized = False

        # Initialize GPIO
        # GPIO 초기화
        self._initialize_gpio()

        # Register signal handlers for cleanup
        # 정리를 위한 신호 처리기 등록
        self._register_signal_handlers()

    def _initialize_gpio(self) -> None:
        """
        Initialize GPIO pin for output.
        출력용 GPIO 핀을 초기화합니다.

        Raises:
            RuntimeError: If GPIO is not available / GPIO를 사용할 수 없는 경우
        """
        if not GPIO_AVAILABLE:
            self.logger.warning("RPi.GPIO not available - running in simulation mode")
            self._initialized = True
            return

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, False)  # Start in locked state / 잠금 상태로 시작
            self._initialized = True
            self.logger.info(f"GPIO pin {self.gpio_pin} initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize GPIO: {e}")
            raise RuntimeError(f"GPIO initialization failed: {e}")

    def _register_signal_handlers(self) -> None:
        """
        Register signal handlers for graceful cleanup.
        정상적인 정리를 위한 신호 처리기를 등록합니다.
        """
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, cleaning up...")
            self.cleanup()
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def can_unlock(self) -> bool:
        """
        Check if unlock is allowed based on rate limiting.
        속도 제한에 따라 잠금 해제가 허용되는지 확인합니다.

        Returns:
            bool: True if unlock is allowed / 잠금 해제가 허용되면 True
        """
        if self._last_unlock_time is None:
            return True

        time_since_last = datetime.now() - self._last_unlock_time
        return time_since_last > timedelta(minutes=self.rate_limit_minutes)

    def unlock(self) -> bool:
        """
        Unlock the door with rate limiting.
        속도 제한을 적용하여 도어를 잠금 해제합니다.

        Returns:
            bool: True if door was unlocked, False if rate limited /
                  잠금 해제되면 True, 속도 제한되면 False
        """
        if not self._initialized:
            self.logger.error("GPIO not initialized")
            return False

        if not self.can_unlock():
            self.logger.warning(
                f"Rate limited - last unlock was at {self._last_unlock_time}"
            )
            return False

        try:
            self.logger.info("Unlocking door...")

            if GPIO_AVAILABLE:
                GPIO.output(self.gpio_pin, True)

            time.sleep(self.unlock_duration)

            if GPIO_AVAILABLE:
                GPIO.output(self.gpio_pin, False)

            self._last_unlock_time = datetime.now()
            self.logger.info("Door locked again")
            return True

        except Exception as e:
            self.logger.error(f"Error during unlock: {e}")
            # Try to ensure door is locked
            # 도어가 잠겨있는지 확인 시도
            self.lock()
            return False

    def lock(self) -> bool:
        """
        Lock the door immediately.
        도어를 즉시 잠급니다.

        Returns:
            bool: True if successful / 성공하면 True
        """
        if not self._initialized:
            return False

        try:
            if GPIO_AVAILABLE:
                GPIO.output(self.gpio_pin, False)
            self.logger.info("Door locked")
            return True
        except Exception as e:
            self.logger.error(f"Error locking door: {e}")
            return False

    def cleanup(self) -> None:
        """
        Clean up GPIO resources.
        GPIO 리소스를 정리합니다.
        """
        if not self._initialized:
            return

        try:
            if GPIO_AVAILABLE:
                GPIO.output(self.gpio_pin, False)  # Ensure door is locked / 도어 잠금 확인
                GPIO.cleanup()
            self._initialized = False
            self.logger.info("GPIO cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup: {e}")


class MockDoorController(DoorControllerBase):
    """
    Mock door controller for testing without hardware.
    하드웨어 없이 테스트하기 위한 모의 도어 컨트롤러입니다.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.is_locked = True
        self.unlock_count = 0

    def unlock(self) -> bool:
        self.is_locked = False
        self.unlock_count += 1
        self.logger.info(f"[MOCK] Door unlocked (count: {self.unlock_count})")
        return True

    def lock(self) -> bool:
        self.is_locked = True
        self.logger.info("[MOCK] Door locked")
        return True

    def cleanup(self) -> None:
        self.logger.info("[MOCK] Cleanup completed")
