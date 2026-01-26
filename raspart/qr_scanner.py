"""
QR Code Scanner Module
QR 코드 스캐너 모듈

Class-based QR code scanner with proper encapsulation and error handling.
적절한 캡슐화 및 에러 처리를 갖춘 클래스 기반 QR 코드 스캐너입니다.
"""

import json
import os
import sys
import signal
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pyzbar.pyzbar as pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

from constants import (
    DEFAULT_KEY_FILE,
    DEFAULT_LOG_FILE,
    DEFAULT_CAMERA_INDEX,
    DATETIME_FORMAT,
    DATETIME_FORMAT_UTC,
    DoorConfig
)
from door_controller import GPIODoorController, MockDoorController, DoorControllerBase


class ScannerState(Enum):
    """Scanner state enumeration / 스캐너 상태 열거형"""
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ScanResult:
    """
    Result of a QR code scan.
    QR 코드 스캔 결과입니다.
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class AccessAttempt:
    """
    Record of an access attempt for audit trail.
    감사 추적을 위한 출입 시도 기록입니다.
    """
    timestamp: datetime
    door_id: str
    key_id: Optional[str]
    success: bool
    reason: str
    qr_data: Optional[str] = None


class QRScanner:
    """
    QR Code Scanner with validation and door control.
    검증 및 도어 제어 기능을 갖춘 QR 코드 스캐너입니다.

    This class encapsulates all QR scanning functionality including:
    - Camera initialization and frame capture
    - QR code detection and decoding
    - Key validation against stored credentials
    - Door control with rate limiting
    - Audit trail logging

    이 클래스는 다음을 포함한 모든 QR 스캔 기능을 캡슐화합니다:
    - 카메라 초기화 및 프레임 캡처
    - QR 코드 감지 및 디코딩
    - 저장된 자격 증명에 대한 키 검증
    - 속도 제한이 있는 도어 제어
    - 감사 추적 로깅
    """

    def __init__(
        self,
        config: DoorConfig,
        door_controller: Optional[DoorControllerBase] = None,
        logger: Optional[logging.Logger] = None,
        on_access_attempt: Optional[Callable[[AccessAttempt], None]] = None,
        use_utc: bool = False
    ):
        """
        Initialize QR Scanner.
        QR 스캐너를 초기화합니다.

        Args:
            config (DoorConfig): Door configuration / 도어 설정
            door_controller (DoorControllerBase, optional): Door controller instance / 도어 컨트롤러 인스턴스
            logger (logging.Logger, optional): Logger instance / 로거 인스턴스
            on_access_attempt (Callable, optional): Callback for access attempts / 출입 시도 콜백
            use_utc (bool): Whether to use UTC for time validation / 시간 검증에 UTC 사용 여부
        """
        self.config = config
        self.logger = logger or self._setup_logger()
        self.on_access_attempt = on_access_attempt
        self.use_utc = use_utc

        # State
        # 상태
        self._state = ScannerState.IDLE
        self._camera: Optional[Any] = None
        self._current_key: Optional[Dict[str, Any]] = None
        self._initial_password: Optional[str] = None
        self._access_attempts: list[AccessAttempt] = []

        # Door controller
        # 도어 컨트롤러
        self.door_controller = door_controller or self._create_door_controller()

        # Register signal handlers
        # 신호 처리기 등록
        self._register_signal_handlers()

    def _setup_logger(self) -> logging.Logger:
        """
        Set up logger instance.
        로거 인스턴스를 설정합니다.
        """
        logger = logging.getLogger(f"QRScanner-{self.config.door_id}")
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '[%(levelname)s] %(asctime)s (%(filename)s:%(lineno)d) > %(message)s'
        )

        # File handler
        # 파일 핸들러
        file_handler = logging.FileHandler(self.config.log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    def _create_door_controller(self) -> DoorControllerBase:
        """
        Create appropriate door controller.
        적절한 도어 컨트롤러를 생성합니다.
        """
        try:
            return GPIODoorController(
                gpio_pin=self.config.gpio_pin,
                unlock_duration=self.config.unlock_duration,
                rate_limit_minutes=self.config.rate_limit_minutes,
                logger=self.logger
            )
        except RuntimeError:
            self.logger.warning("GPIO not available, using mock controller")
            return MockDoorController(logger=self.logger)

    def _register_signal_handlers(self) -> None:
        """
        Register signal handlers for graceful shutdown.
        정상적인 종료를 위한 신호 처리기를 등록합니다.
        """
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, stopping scanner...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _initialize_camera(self) -> bool:
        """
        Initialize camera for QR scanning.
        QR 스캔을 위해 카메라를 초기화합니다.

        Returns:
            bool: True if camera initialized successfully / 카메라 초기화 성공 시 True
        """
        if not CV2_AVAILABLE:
            self.logger.error("OpenCV (cv2) not available")
            return False

        try:
            self._camera = cv2.VideoCapture(self.config.camera_index)

            if not self._camera.isOpened():
                self.logger.error(
                    f"Failed to open camera at index {self.config.camera_index}"
                )
                return False

            self.logger.info(f"Camera initialized at index {self.config.camera_index}")
            return True

        except Exception as e:
            self.logger.error(f"Camera initialization error: {e}")
            return False

    def _release_camera(self) -> None:
        """
        Release camera resources.
        카메라 리소스를 해제합니다.
        """
        if self._camera is not None:
            try:
                self._camera.release()
                if CV2_AVAILABLE:
                    cv2.destroyAllWindows()
                self.logger.info("Camera released")
            except Exception as e:
                self.logger.error(f"Error releasing camera: {e}")
            finally:
                self._camera = None

    def load_key(self, key_path: Optional[str] = None) -> bool:
        """
        Load key information from file.
        파일에서 키 정보를 로드합니다.

        Args:
            key_path (str, optional): Path to key file / 키 파일 경로

        Returns:
            bool: True if key loaded successfully / 키 로드 성공 시 True
        """
        path = key_path or self.config.key_file

        if not os.path.isfile(path):
            self.logger.error(f"Key file not found: {path}")
            return False

        try:
            with open(path, 'r') as f:
                self._current_key = json.load(f)

            self._initial_password = self._current_key.get('passwd')
            self.logger.info(f"Key loaded from {path}")
            return True

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in key file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error reading key file: {e}")
            return False

    def _get_current_time(self) -> datetime:
        """
        Get current time based on UTC setting.
        UTC 설정에 따라 현재 시간을 가져옵니다.
        """
        if self.use_utc:
            return datetime.now(timezone.utc).replace(tzinfo=None)
        return datetime.now()

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """
        Parse time string with format detection.
        포맷 감지와 함께 시간 문자열을 파싱합니다.
        """
        formats = [DATETIME_FORMAT, DATETIME_FORMAT_UTC, "%Y-%m-%d %H:%M:%S"]

        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue

        self.logger.error(f"Unable to parse time: {time_str}")
        return None

    def is_key_valid(self) -> bool:
        """
        Check if current key is within valid time window.
        현재 키가 유효한 시간 범위 내에 있는지 확인합니다.

        Returns:
            bool: True if key is valid / 키가 유효하면 True
        """
        if not self._current_key:
            return False

        now = self._get_current_time()

        start_time = self._parse_time(self._current_key.get('start', ''))
        end_time = self._parse_time(self._current_key.get('end', ''))

        if start_time is None or end_time is None:
            return False

        return start_time < now < end_time

    def has_key_changed(self) -> bool:
        """
        Check if key has been updated (password changed).
        키가 업데이트되었는지 확인합니다 (비밀번호 변경).

        Returns:
            bool: True if key has changed / 키가 변경되면 True
        """
        if not os.path.isfile(self.config.key_file):
            return False

        try:
            with open(self.config.key_file, 'r') as f:
                current_key = json.load(f)

            return current_key.get('passwd') != self._initial_password

        except Exception:
            return False

    def validate_qr_data(self, qr_data: str) -> ScanResult:
        """
        Validate scanned QR code data against stored key.
        스캔된 QR 코드 데이터를 저장된 키와 대조하여 검증합니다.

        Args:
            qr_data (str): Raw QR code data / 원시 QR 코드 데이터

        Returns:
            ScanResult: Validation result / 검증 결과
        """
        try:
            scanned_key = json.loads(qr_data)
        except json.JSONDecodeError:
            return ScanResult(
                success=False,
                error=f"Invalid QR code format: {qr_data}"
            )

        if not self._current_key:
            return ScanResult(
                success=False,
                error="No stored key to validate against"
            )

        # Validate all fields
        # 모든 필드 검증
        for key, value in self._current_key.items():
            if scanned_key.get(key) != value:
                return ScanResult(
                    success=False,
                    data=scanned_key,
                    error=f"Key mismatch - Field: {key}"
                )

        return ScanResult(success=True, data=scanned_key)

    def _record_access_attempt(
        self,
        success: bool,
        reason: str,
        key_id: Optional[str] = None,
        qr_data: Optional[str] = None
    ) -> None:
        """
        Record access attempt for audit trail.
        감사 추적을 위해 출입 시도를 기록합니다.
        """
        attempt = AccessAttempt(
            timestamp=datetime.now(),
            door_id=self.config.door_id,
            key_id=key_id,
            success=success,
            reason=reason,
            qr_data=qr_data
        )

        self._access_attempts.append(attempt)

        # Log the attempt
        # 시도 로깅
        log_msg = f"Access {'GRANTED' if success else 'DENIED'}: {reason}"
        if success:
            self.logger.info(log_msg)
        else:
            self.logger.warning(log_msg)

        # Call callback if registered
        # 등록된 경우 콜백 호출
        if self.on_access_attempt:
            try:
                self.on_access_attempt(attempt)
            except Exception as e:
                self.logger.error(f"Error in access attempt callback: {e}")

    def _process_frame(self, frame) -> bool:
        """
        Process a single camera frame for QR codes.
        단일 카메라 프레임에서 QR 코드를 처리합니다.

        Args:
            frame: Camera frame / 카메라 프레임

        Returns:
            bool: True if valid QR code found and door unlocked /
                  유효한 QR 코드 발견 및 도어 잠금 해제 시 True
        """
        if not PYZBAR_AVAILABLE:
            return False

        # Convert to grayscale
        # 그레이스케일로 변환
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Decode QR codes
        # QR 코드 디코딩
        decoded = pyzbar.decode(gray)

        for d in decoded:
            qr_data = d.data.decode("utf-8")

            result = self.validate_qr_data(qr_data)

            if result.success:
                # Check rate limiting
                # 속도 제한 확인
                if self.door_controller.can_unlock():
                    if self.door_controller.unlock():
                        self._record_access_attempt(
                            success=True,
                            reason="Valid QR code",
                            key_id=result.data.get('passwd'),
                            qr_data=qr_data
                        )
                        return True
                    else:
                        self._record_access_attempt(
                            success=False,
                            reason="Door unlock failed",
                            qr_data=qr_data
                        )
                else:
                    self._record_access_attempt(
                        success=False,
                        reason="Rate limited",
                        qr_data=qr_data
                    )
            else:
                self._record_access_attempt(
                    success=False,
                    reason=result.error or "Invalid QR code",
                    qr_data=qr_data
                )

        return False

    def run(self) -> None:
        """
        Main scanning loop.
        메인 스캔 루프입니다.
        """
        self.logger.info("Starting QR scanner...")

        # Load key
        # 키 로드
        if not self.load_key():
            self.logger.error("Failed to load key, exiting")
            return

        # Initialize camera
        # 카메라 초기화
        if not self._initialize_camera():
            self.logger.error("Failed to initialize camera, exiting")
            return

        self._state = ScannerState.RUNNING
        self.logger.info("Scanner running...")

        try:
            while self._state == ScannerState.RUNNING:
                # Check if key is still valid
                # 키가 아직 유효한지 확인
                if not self.is_key_valid():
                    self.logger.info("Key expired")
                    break

                # Check if key has been updated
                # 키가 업데이트되었는지 확인
                if self.has_key_changed():
                    self.logger.info("Key changed, restarting required")
                    break

                # Capture frame
                # 프레임 캡처
                ret, frame = self._camera.read()

                if not ret:
                    continue

                # Process frame
                # 프레임 처리
                self._process_frame(frame)

        except Exception as e:
            self.logger.error(f"Scanner error: {e}")
            self._state = ScannerState.ERROR
        finally:
            self.stop()

    def stop(self) -> None:
        """
        Stop the scanner and clean up resources.
        스캐너를 중지하고 리소스를 정리합니다.
        """
        self.logger.info("Stopping scanner...")
        self._state = ScannerState.STOPPED

        self._release_camera()
        self.door_controller.cleanup()

        self.logger.info("Scanner stopped")

    def get_access_log(self) -> list[AccessAttempt]:
        """
        Get access attempt log.
        출입 시도 로그를 가져옵니다.

        Returns:
            list[AccessAttempt]: List of access attempts / 출입 시도 목록
        """
        return self._access_attempts.copy()

    @property
    def state(self) -> ScannerState:
        """Get current scanner state / 현재 스캐너 상태 가져오기"""
        return self._state


def main():
    """
    Main entry point for QR scanner.
    QR 스캐너의 메인 진입점입니다.
    """
    import logger as log_module

    # Create configuration
    # 설정 생성
    config = DoorConfig(
        door_id="default",
        key_file="keyinfo.json",
        log_file="./logs.txt"
    )

    # Create and run scanner
    # 스캐너 생성 및 실행
    scanner = QRScanner(config)
    scanner.run()


if __name__ == "__main__":
    main()
