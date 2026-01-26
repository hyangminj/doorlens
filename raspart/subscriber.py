"""
Pub/Sub Subscriber Module (Refactored)
Pub/Sub 구독자 모듈 (리팩토링)

Secure, robust Pub/Sub subscriber with proper process management.
적절한 프로세스 관리를 갖춘 안전하고 견고한 Pub/Sub 구독자입니다.
"""

import json
import os
import signal
import subprocess
import sys
import logging
import threading
import time
from typing import Optional, Callable
from datetime import datetime
from dataclasses import dataclass

from google.cloud import pubsub_v1

from constants import DEFAULT_KEY_FILE, DEFAULT_LOG_FILE


# Constants for process monitoring
# 프로세스 모니터링 상수
PROCESS_CHECK_INTERVAL_SECONDS = 5
PROCESS_TERMINATION_TIMEOUT = 5


@dataclass
class SubscriberConfig:
    """
    Configuration for Pub/Sub subscriber.
    Pub/Sub 구독자 설정입니다.
    """
    project_id: str
    subscription_name: str
    key_file: str = DEFAULT_KEY_FILE
    log_file: str = DEFAULT_LOG_FILE
    scanner_script: str = "qr_scanner.py"
    monitor_scanner: bool = True  # Enable scanner process monitoring / 스캐너 프로세스 모니터링 활성화


class DoorLensSubscriber:
    """
    Pub/Sub subscriber for DoorLens system.
    DoorLens 시스템용 Pub/Sub 구독자입니다.

    Features:
    - Secure subprocess execution (no shell injection)
    - Process lifecycle management with health monitoring
    - Graceful shutdown handling
    - Message deduplication
    - Scanner process crash detection and logging

    기능:
    - 안전한 서브프로세스 실행 (쉘 인젝션 없음)
    - 상태 모니터링을 포함한 프로세스 수명 관리
    - 정상적인 종료 처리
    - 메시지 중복 제거
    - 스캐너 프로세스 충돌 감지 및 로깅
    """

    def __init__(
        self,
        config: SubscriberConfig,
        logger: Optional[logging.Logger] = None,
        on_message: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize subscriber.
        구독자를 초기화합니다.

        Args:
            config (SubscriberConfig): Subscriber configuration / 구독자 설정
            logger (logging.Logger, optional): Logger instance / 로거 인스턴스
            on_message (Callable, optional): Message callback / 메시지 콜백
        """
        self.config = config
        self.logger = logger or self._setup_logger()
        self.on_message = on_message

        self._subscriber_client: Optional[pubsub_v1.SubscriberClient] = None
        self._streaming_pull_future = None
        self._scanner_process: Optional[subprocess.Popen] = None
        self._running = False
        self._last_message_id: Optional[str] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False

        self._register_signal_handlers()

    def _setup_logger(self) -> logging.Logger:
        """Set up logger instance."""
        logger = logging.getLogger("DoorLensSubscriber")
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

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _stop_process_monitor(self) -> None:
        """
        Stop the process monitor thread.
        프로세스 모니터 스레드를 중지합니다.
        """
        self._monitor_running = False
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
            self._monitor_thread = None

    def _start_process_monitor(self) -> None:
        """
        Start a background thread to monitor the scanner process health.
        스캐너 프로세스 상태를 모니터링하는 백그라운드 스레드를 시작합니다.
        """
        if not self.config.monitor_scanner:
            return

        self._stop_process_monitor()
        self._monitor_running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_scanner_process,
            daemon=True,
            name="ScannerProcessMonitor"
        )
        self._monitor_thread.start()
        self.logger.debug("Process monitor thread started")

    def _monitor_scanner_process(self) -> None:
        """
        Monitor scanner process and log if it crashes.
        스캐너 프로세스를 모니터링하고 충돌 시 로그를 기록합니다.

        This runs in a background thread and checks process status periodically.
        백그라운드 스레드에서 실행되며 주기적으로 프로세스 상태를 확인합니다.
        """
        while self._monitor_running and self._scanner_process is not None:
            time.sleep(PROCESS_CHECK_INTERVAL_SECONDS)

            if self._scanner_process is None:
                break

            # Check if process has terminated
            # 프로세스가 종료되었는지 확인
            return_code = self._scanner_process.poll()
            if return_code is not None:
                # Process has terminated
                # 프로세스가 종료됨
                if return_code == 0:
                    self.logger.info("Scanner process exited normally (code 0)")
                else:
                    self.logger.error(
                        f"Scanner process crashed unexpectedly (exit code: {return_code})"
                    )
                    # Try to capture stderr for debugging
                    # 디버깅을 위해 stderr 캡처 시도
                    try:
                        if self._scanner_process.stderr:
                            stderr_output = self._scanner_process.stderr.read()
                            if stderr_output:
                                stderr_text = stderr_output.decode('utf-8', errors='replace')
                                self.logger.error(f"Scanner stderr: {stderr_text[:500]}")
                    except Exception as e:
                        self.logger.debug(f"Could not read scanner stderr: {e}")

                self._scanner_process = None
                break

    def _stop_scanner_process(self) -> None:
        """
        Stop any running scanner process.
        실행 중인 스캐너 프로세스를 중지합니다.
        """
        # Stop the monitor first
        # 먼저 모니터 중지
        self._stop_process_monitor()

        if self._scanner_process is not None:
            try:
                self._scanner_process.terminate()
                self._scanner_process.wait(timeout=PROCESS_TERMINATION_TIMEOUT)
                self.logger.info("Scanner process terminated")
            except subprocess.TimeoutExpired:
                self._scanner_process.kill()
                self.logger.warning("Scanner process killed")
            except Exception as e:
                self.logger.error(f"Error stopping scanner: {e}")
            finally:
                self._scanner_process = None

    def _start_scanner_process(self) -> bool:
        """
        Start scanner process using subprocess.run (secure).
        subprocess.run을 사용하여 스캐너 프로세스를 시작합니다 (안전).

        Returns:
            bool: True if process started successfully / 프로세스 시작 성공 시 True
        """
        # Stop any existing scanner
        # 기존 스캐너 중지
        self._stop_scanner_process()

        try:
            # Use subprocess.Popen for non-blocking execution
            # 비차단 실행을 위해 subprocess.Popen 사용
            script_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                self.config.scanner_script
            )

            if not os.path.exists(script_path):
                self.logger.error(f"Scanner script not found: {script_path}")
                return False

            self._scanner_process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

            self.logger.info(f"Scanner process started (PID: {self._scanner_process.pid})")

            # Start process monitor
            # 프로세스 모니터 시작
            self._start_process_monitor()

            return True

        except Exception as e:
            self.logger.error(f"Failed to start scanner: {e}")
            return False

    def _save_key(self, key_data: str) -> bool:
        """
        Save key data to file.
        키 데이터를 파일에 저장합니다.

        Args:
            key_data (str): Key data as JSON string / JSON 문자열로 된 키 데이터

        Returns:
            bool: True if saved successfully / 저장 성공 시 True
        """
        try:
            # Validate JSON before saving
            # 저장 전 JSON 검증
            json.loads(key_data)

            with open(self.config.key_file, 'w') as f:
                f.write(key_data)

            # Set restrictive file permissions (owner read/write only)
            # 제한적 파일 권한 설정 (소유자 읽기/쓰기만 허용)
            os.chmod(self.config.key_file, 0o600)

            self.logger.info(f"Key saved to {self.config.key_file}")
            return True

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid key data (not JSON): {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to save key: {e}")
            return False

    def _handle_message(self, message) -> None:
        """
        Handle incoming Pub/Sub message.
        수신된 Pub/Sub 메시지를 처리합니다.

        Args:
            message: Pub/Sub message / Pub/Sub 메시지
        """
        try:
            message_id = message.message_id

            # Check for duplicate message
            # 중복 메시지 확인
            if message_id == self._last_message_id:
                self.logger.warning(f"Duplicate message ignored: {message_id}")
                message.ack()
                return

            self._last_message_id = message_id

            self.logger.info(f"Received message: {message_id}")

            # Decode message data
            # 메시지 데이터 디코딩
            key_data = message.data.decode("utf-8")

            # Acknowledge message first
            # 먼저 메시지 확인
            message.ack()
            self.logger.info(f"Acknowledged message: {message_id}")

            # Save key to file
            # 파일에 키 저장
            if self._save_key(key_data):
                # Start scanner process
                # 스캐너 프로세스 시작
                self._start_scanner_process()

            # Call message callback if registered
            # 등록된 경우 메시지 콜백 호출
            if self.on_message:
                try:
                    self.on_message(key_data)
                except Exception as e:
                    self.logger.error(f"Error in message callback: {e}")

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            # Don't ack the message so it will be redelivered
            # 재전송을 위해 메시지를 확인하지 않음

    def start(self) -> None:
        """
        Start the subscriber.
        구독자를 시작합니다.
        """
        self.logger.info("Starting subscriber...")

        try:
            self._subscriber_client = pubsub_v1.SubscriberClient()

            subscription_path = self._subscriber_client.subscription_path(
                self.config.project_id,
                self.config.subscription_name
            )

            self._streaming_pull_future = self._subscriber_client.subscribe(
                subscription_path,
                callback=self._handle_message
            )

            self._running = True
            self.logger.info(f"Listening for messages on {subscription_path}")

            # Block until exception
            # 예외 발생까지 차단
            self._streaming_pull_future.result()

        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error(f"Subscriber error: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        """
        Stop the subscriber.
        구독자를 중지합니다.
        """
        self.logger.info("Stopping subscriber...")
        self._running = False

        # Stop streaming pull
        # 스트리밍 풀 중지
        if self._streaming_pull_future is not None:
            self._streaming_pull_future.cancel()

        # Stop scanner process
        # 스캐너 프로세스 중지
        self._stop_scanner_process()

        # Close subscriber client
        # 구독자 클라이언트 종료
        if self._subscriber_client is not None:
            self._subscriber_client.close()

        self.logger.info("Subscriber stopped")


def main():
    """Main entry point."""
    try:
        import config as cfg

        subscriber_config = SubscriberConfig(
            project_id=cfg.project_id,
            subscription_name=cfg.subscription_name
        )

        subscriber = DoorLensSubscriber(subscriber_config)
        subscriber.start()

    except ImportError:
        print("Error: config.py not found. Please create config.py with:")
        print("  project_id = 'your-gcp-project-id'")
        print("  subscription_name = 'your-pubsub-subscription'")
        sys.exit(1)


if __name__ == "__main__":
    main()
