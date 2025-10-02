#!/usr/bin/env python

# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Google Cloud Pub/Sub Subscriber Module
Google Cloud Pub/Sub 구독자 모듈

Listens for new QR code keys and launches the QR scanner.
새로운 QR 코드 키를 수신하고 QR 스캐너를 실행합니다.
"""

import argparse
import config as cfg
import os
from google.cloud import pubsub_v1


def sub(project_id, subscription_name):
    """
    Receives messages from a Pub/Sub subscription.
    Pub/Sub 구독에서 메시지를 수신합니다.

    Args:
        project_id (str): Google Cloud project ID
                         Google Cloud 프로젝트 ID
        subscription_name (str): Pub/Sub subscription name
                                Pub/Sub 구독 이름

    Process:
    1. Listen for messages on the subscription
    2. When message received, save key to keyinfo.json
    3. Acknowledge the message
    4. Launch rasberryQR.py to start scanning

    처리 과정:
    1. 구독에서 메시지 수신 대기
    2. 메시지 수신 시 키를 keyinfo.json에 저장
    3. 메시지 확인
    4. rasberryQR.py를 실행하여 스캔 시작
    """
    # Initialize a Subscriber client
    # Subscriber 클라이언트 초기화
    subscriber_client = pubsub_v1.SubscriberClient()

    # Create fully qualified subscription path
    # 완전한 형식의 구독 경로 생성
    # Format: projects/{project_id}/subscriptions/{subscription_name}
    subscription_path = subscriber_client.subscription_path(
        project_id, subscription_name
    )

    def callback(message):
        """
        Callback function to handle received messages.
        수신된 메시지를 처리하는 콜백 함수입니다.

        Args:
            message: Pub/Sub message containing key data
                    키 데이터를 포함하는 Pub/Sub 메시지
        """
        print(
            "Received message {} of message ID {}\n".format(
                message, message.message_id
            )
        )

        # Decode message data from bytes to string
        # 메시지 데이터를 바이트에서 문자열로 디코딩
        keystring = message.data.decode("utf-8")

        # Save key information to JSON file
        # 키 정보를 JSON 파일에 저장
        with open("keyinfo.json", 'w') as f:
            f.write(keystring)

        # Acknowledge the message (confirms receipt to Pub/Sub)
        # Unacknowledged messages will be redelivered
        # 메시지 확인 (Pub/Sub에 수신 확인)
        # 확인되지 않은 메시지는 재전송됩니다
        message.ack()
        print("Acknowledged message {}\n".format(message.message_id))

        # Launch QR scanner to start validating codes
        # QR 스캐너를 실행하여 코드 검증 시작
        os.system("python3 ./rasberryQR.py")

    # Start streaming subscription
    # 스트리밍 구독 시작
    streaming_pull_future = subscriber_client.subscribe(
        subscription_path, callback=callback
    )
    print("Listening for messages on {}..\n".format(subscription_path))

    try:
        # Keep main thread alive while messages are processed in callbacks
        # Calling result() blocks until an exception occurs
        # 콜백에서 메시지가 처리되는 동안 메인 스레드 유지
        # result()를 호출하면 예외가 발생할 때까지 차단됩니다
        streaming_pull_future.result()
    except Exception as e:
        # Cancel streaming pull on any exception
        # 예외 발생 시 스트리밍 풀 취소
        print(f"Streaming stopped due to: {e}")
        streaming_pull_future.cancel()

    # Close subscriber client
    # 구독자 클라이언트 종료
    subscriber_client.close()


if __name__ == "__main__":
    # Use config values instead of command line arguments
    # 명령줄 인자 대신 config 값 사용
    sub(cfg.project_id, cfg.subscription_name)
