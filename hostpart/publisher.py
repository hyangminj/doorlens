"""
Pub/Sub Publisher Module (Refactored)
Pub/Sub 게시자 모듈 (리팩토링)

Enhanced Pub/Sub publisher with proper error handling.
적절한 에러 처리가 포함된 향상된 Pub/Sub 게시자입니다.
"""

import logging
from typing import Optional
from google.cloud import pubsub_v1
from google.api_core import exceptions as gcp_exceptions

from constants import PubSubConfig


class PublishError(Exception):
    """Exception for publish errors / 게시 오류 예외"""
    pass


class PubSubPublisher:
    """
    Pub/Sub publisher for key distribution.
    키 배포를 위한 Pub/Sub 게시자입니다.

    Features:
    - Proper error handling for GCP exceptions
    - Message ID tracking
    - Configurable timeout

    기능:
    - GCP 예외에 대한 적절한 에러 처리
    - 메시지 ID 추적
    - 설정 가능한 타임아웃
    """

    def __init__(
        self,
        config: PubSubConfig,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize publisher.
        게시자를 초기화합니다.

        Args:
            config (PubSubConfig): Publisher configuration / 게시자 설정
            logger (logging.Logger, optional): Logger instance / 로거 인스턴스
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._client: Optional[pubsub_v1.PublisherClient] = None
        self._topic_path: Optional[str] = None
        self._published_messages: list[str] = []

    def _get_client(self) -> pubsub_v1.PublisherClient:
        """
        Get or create publisher client.
        게시자 클라이언트를 가져오거나 생성합니다.
        """
        if self._client is None:
            self._client = pubsub_v1.PublisherClient()
            self._topic_path = self._client.topic_path(
                self.config.project_id,
                self.config.topic_name
            )
        return self._client

    def publish(
        self,
        message: bytes,
        timeout: float = 60.0,
        **attributes
    ) -> str:
        """
        Publish message to Pub/Sub topic.
        Pub/Sub 토픽에 메시지를 게시합니다.

        Args:
            message (bytes): Message data / 메시지 데이터
            timeout (float): Publish timeout in seconds / 게시 타임아웃(초)
            **attributes: Optional message attributes / 선택적 메시지 속성

        Returns:
            str: Published message ID / 게시된 메시지 ID

        Raises:
            PublishError: If publishing fails / 게시 실패 시
        """
        try:
            client = self._get_client()

            future = client.publish(
                self._topic_path,
                message,
                **attributes
            )

            message_id = future.result(timeout=timeout)
            self._published_messages.append(message_id)

            self.logger.info(
                f"Published message {message_id} to {self.config.topic_name}"
            )
            return message_id

        except gcp_exceptions.NotFound:
            self.logger.error(f"Topic not found: {self.config.topic_name}")
            raise PublishError(
                f"Topic not found: {self.config.topic_name}. "
                "Please create the topic in GCP Console."
            )

        except gcp_exceptions.PermissionDenied:
            self.logger.error("Permission denied for Pub/Sub")
            raise PublishError(
                "Permission denied. Please ensure your service account has "
                "roles/pubsub.publisher permission."
            )

        except Exception as e:
            self.logger.error(f"Publish error: {e}")
            raise PublishError(f"Failed to publish message: {e}")

    def publish_string(
        self,
        message: str,
        encoding: str = 'utf-8',
        **attributes
    ) -> str:
        """
        Publish string message to Pub/Sub topic.
        Pub/Sub 토픽에 문자열 메시지를 게시합니다.

        Args:
            message (str): Message string / 메시지 문자열
            encoding (str): String encoding / 문자열 인코딩
            **attributes: Optional message attributes / 선택적 메시지 속성

        Returns:
            str: Published message ID / 게시된 메시지 ID
        """
        return self.publish(message.encode(encoding), **attributes)

    def get_published_messages(self) -> list[str]:
        """
        Get list of published message IDs.
        게시된 메시지 ID 목록을 가져옵니다.

        Returns:
            list[str]: List of message IDs / 메시지 ID 목록
        """
        return self._published_messages.copy()

    def close(self) -> None:
        """
        Close publisher client.
        게시자 클라이언트를 닫습니다.
        """
        if self._client is not None:
            # PublisherClient doesn't have explicit close, but we reset
            # PublisherClient에는 명시적 close가 없지만 리셋
            self._client = None
            self._topic_path = None


# Backward compatibility function
# 하위 호환성 함수
def pub(project_id: str, topic_name: str, message: bytes) -> str:
    """
    Legacy function for backward compatibility.
    하위 호환성을 위한 레거시 함수입니다.

    Args:
        project_id (str): GCP project ID / GCP 프로젝트 ID
        topic_name (str): Pub/Sub topic name / Pub/Sub 토픽 이름
        message (bytes): Message data / 메시지 데이터

    Returns:
        str: Published message ID / 게시된 메시지 ID
    """
    config = PubSubConfig(
        project_id=project_id,
        topic_name=topic_name
    )
    publisher = PubSubPublisher(config)
    return publisher.publish(message)
