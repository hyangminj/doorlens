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
Google Cloud Pub/Sub Publisher Module
Google Cloud Pub/Sub 게시자 모듈

Publishes QR code key data to Google Cloud Pub/Sub topic.
QR 코드 키 데이터를 Google Cloud Pub/Sub 토픽에 게시합니다.
"""

import argparse
import time
from google.cloud import pubsub_v1


def get_callback(api_future, data, ref):
    """
    Wrap message data in the context of the callback function.
    콜백 함수의 컨텍스트에서 메시지 데이터를 래핑합니다.

    Args:
        api_future: The future returned by the publish call
                   게시 호출에서 반환된 future 객체
        data: The message data being published
             게시되는 메시지 데이터
        ref: Dictionary to track number of messages published
            게시된 메시지 수를 추적하는 딕셔너리

    Returns:
        function: Callback function to be called when publish completes
                 게시가 완료되면 호출될 콜백 함수
    """
    def callback(api_future):
        try:
            # Log successful message publication
            # 성공적인 메시지 게시 로그
            print(
                "Published message {} now has message ID {}".format(
                    data, api_future.result()
                )
            )
            ref["num_messages"] += 1
        except Exception:
            # Log any errors during publication
            # 게시 중 발생한 오류 로그
            print(
                "A problem occurred when publishing {}: {}\n".format(
                    data, api_future.exception()
                )
            )
            raise

    return callback


def pub(project_id, topic_name, data):
    """
    Publishes a message to a Pub/Sub topic.
    Pub/Sub 토픽에 메시지를 게시합니다.

    Args:
        project_id (str): Google Cloud project ID
                         Google Cloud 프로젝트 ID
        topic_name (str): Name of the Pub/Sub topic
                         Pub/Sub 토픽 이름
        data (bytes): Message data to publish (must be bytes)
                     게시할 메시지 데이터 (바이트여야 함)
    """
    # Initialize a Publisher client
    # Publisher 클라이언트 초기화
    client = pubsub_v1.PublisherClient()

    # Create fully qualified topic path
    # 완전한 형식의 토픽 경로 생성
    # Format: projects/{project_id}/topics/{topic_name}
    topic_path = client.topic_path(project_id, topic_name)

    # Track the number of published messages
    # 게시된 메시지 수 추적
    ref = dict({"num_messages": 0})

    # Publish the message
    # When you publish a message, the client returns a future
    # 메시지 게시
    # 메시지를 게시하면 클라이언트가 future를 반환합니다
    api_future = client.publish(topic_path, data=data)
    api_future.add_done_callback(get_callback(api_future, data, ref))

    # Keep the main thread from exiting while the message future
    # gets resolved in the background
    # 백그라운드에서 메시지 future가 해결되는 동안
    # 메인 스레드가 종료되지 않도록 유지
    while api_future.running():
        time.sleep(0.5)
        print("Published {} message(s).".format(ref["num_messages"]))


if __name__ == "__main__":
    # Parse command line arguments
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_id", help="Google Cloud project ID")
    parser.add_argument("topic_name", help="Pub/Sub topic name")

    args = parser.parse_args()

    pub(args.project_id, args.topic_name)
