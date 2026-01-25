"""
DoorLens Host Main Entry Point
DoorLens 호스트 메인 진입점

Main entry point for generating and distributing QR code keys.
QR 코드 키를 생성하고 배포하기 위한 메인 진입점입니다.
"""

import argparse
import sys
import logging
from typing import Optional

from constants import (
    KeyGeneratorConfig,
    EmailConfig,
    PubSubConfig,
    DEFAULT_EXPIRE_MINUTES
)
from key_generator import KeyGenerator
from email_sender import EmailSender, EmailSendError
from publisher import PubSubPublisher, PublishError


def setup_logging(log_file: str = "./log.txt") -> logging.Logger:
    """
    Set up logging for the application.
    애플리케이션을 위한 로깅을 설정합니다.
    """
    logger = logging.getLogger("DoorLens")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s (%(filename)s:%(lineno)d) > %(message)s'
    )

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def generate_and_distribute_key(
    project_id: str,
    topic_name: str,
    email_id: str,
    email_passwd: str,
    email_to: str,
    expire_minutes: int = DEFAULT_EXPIRE_MINUTES,
    use_utc: bool = False,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Generate and distribute a QR code key.
    QR 코드 키를 생성하고 배포합니다.

    Args:
        project_id (str): GCP project ID / GCP 프로젝트 ID
        topic_name (str): Pub/Sub topic name / Pub/Sub 토픽 이름
        email_id (str): Gmail sender ID / Gmail 발신자 ID
        email_passwd (str): Gmail app password / Gmail 앱 비밀번호
        email_to (str): Recipient email / 수신자 이메일
        expire_minutes (int): Key expiration time / 키 만료 시간
        use_utc (bool): Use UTC for times / 시간에 UTC 사용
        logger (logging.Logger, optional): Logger instance / 로거 인스턴스

    Returns:
        bool: True if successful / 성공 시 True
    """
    logger = logger or setup_logging()

    try:
        # 1. Generate key and QR code
        # 1. 키 및 QR 코드 생성
        logger.info("Generating key...")

        key_config = KeyGeneratorConfig(
            door_id=topic_name,
            expire_minutes=expire_minutes,
            use_utc=use_utc
        )
        generator = KeyGenerator(key_config, logger)
        qr_path, key = generator.generate_and_create_qr()

        logger.info(f"Key generated: {qr_path}")

        # 2. Publish to Pub/Sub
        # 2. Pub/Sub에 게시
        logger.info("Publishing to Pub/Sub...")

        pubsub_config = PubSubConfig(
            project_id=project_id,
            topic_name=topic_name
        )
        publisher = PubSubPublisher(pubsub_config, logger)
        message_id = publisher.publish_string(key.to_json(include_utc=use_utc))

        logger.info(f"Published message: {message_id}")

        # 3. Send email
        # 3. 이메일 전송
        logger.info("Sending email...")

        email_config = EmailConfig(
            sender_id=email_id,
            sender_password=email_passwd
        )
        email_sender = EmailSender(email_config, logger)
        email_sender.send_key(qr_path, email_to)

        logger.info(f"Email sent to: {email_to}")
        logger.info("Key generation and distribution completed successfully!")

        return True

    except PublishError as e:
        logger.error(f"Pub/Sub error: {e}")
        return False

    except EmailSendError as e:
        logger.error(f"Email error: {e}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def main():
    """
    Main function with command line argument support.
    명령줄 인자 지원이 포함된 메인 함수입니다.
    """
    parser = argparse.ArgumentParser(
        description="Generate and distribute DoorLens QR code keys"
    )
    parser.add_argument(
        "--expire",
        type=int,
        default=DEFAULT_EXPIRE_MINUTES,
        help=f"Key expiration time in minutes (default: {DEFAULT_EXPIRE_MINUTES})"
    )
    parser.add_argument(
        "--utc",
        action="store_true",
        help="Use UTC for time values"
    )

    args = parser.parse_args()

    try:
        import config as cfg

        success = generate_and_distribute_key(
            project_id=cfg.project_id,
            topic_name=cfg.topic_name,
            email_id=cfg.email_id,
            email_passwd=cfg.email_passwd,
            email_to=cfg.email_to,
            expire_minutes=args.expire,
            use_utc=args.utc
        )

        sys.exit(0 if success else 1)

    except ImportError:
        print("Error: config.py not found. Please create config.py with:")
        print("  project_id = 'your-gcp-project-id'")
        print("  topic_name = 'your-pubsub-topic'")
        print("  email_id = 'your-gmail-username'")
        print("  email_passwd = 'your-gmail-app-password'")
        print("  email_to = 'recipient@example.com'")
        sys.exit(1)


if __name__ == "__main__":
    main()
