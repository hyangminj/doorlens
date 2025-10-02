"""
DoorKey Generation and Distribution Module
도어 키 생성 및 배포 모듈

Main entry point for generating QR code keys and distributing them
via Pub/Sub and email.
QR 코드 키를 생성하고 Pub/Sub와 이메일로 배포하는 메인 진입점입니다.
"""

import qrcode
import json
import datetime
from bson import ObjectId
import logger as log
import pub
import config as cfg
import emailsend as em


class DoorKey:
    """
    Door Key class for managing QR code key generation.
    QR 코드 키 생성을 관리하는 도어 키 클래스입니다.

    Attributes:
        door_id (str): Identifier for the door
                      도어 식별자
        passwd (str): Password for the key (auto-generated if 'default')
                     키의 비밀번호 ('default'인 경우 자동 생성)
        start_time_type (datetime): Key validity start time
                                   키 유효 시작 시간
        start (str): Formatted start time string
                    포맷된 시작 시간 문자열
        expire_time (int): Key expiration time in minutes
                          키 만료 시간 (분)
        end_time_type (datetime): Key validity end time
                                 키 유효 종료 시간
        end (str): Formatted end time string
                  포맷된 종료 시간 문자열
        log_writter (Logger): Logger instance for logging
                             로깅을 위한 로거 인스턴스
    """

    def __init__(self, door_id='default', passwd='default', expire_minutes=10):
        """
        Initialize DoorKey instance.
        DoorKey 인스턴스를 초기화합니다.

        Args:
            door_id (str): Door identifier (defaults to 'default')
                          도어 식별자 (기본값: 'default')
            passwd (str): Password (defaults to 'default', auto-generated)
                         비밀번호 (기본값: 'default', 자동 생성됨)
            expire_minutes (int): Expiration time in minutes (defaults to 10)
                                만료 시간 (분) (기본값: 10)
        """
        self.door_id = door_id
        self.passwd = passwd

        # Calculate start and end times
        # 시작 및 종료 시간 계산
        self.start_time_type = datetime.datetime.now()
        self.start = self.start_time_type.strftime("%Y-%m-%d, %H:%M:%S")

        self.expire_time = expire_minutes
        self.end_time_type = datetime.datetime.now() + datetime.timedelta(minutes=self.expire_time)
        self.end = self.end_time_type.strftime("%Y-%m-%d, %H:%M:%S")

        # Initialize logger
        # 로거 초기화
        self.log_writter = log.logger("./log.txt")

    def create_key(self):
        """
        Generate QR code key image and return key information.
        QR 코드 키 이미지를 생성하고 키 정보를 반환합니다.

        Returns:
            tuple: (key_path, qr_info)
                - key_path (str): Path to saved QR code image
                                 저장된 QR 코드 이미지 경로
                - qr_info (str): JSON string of key information
                                키 정보의 JSON 문자열
        """
        # Create key information dictionary
        # 키 정보 딕셔너리 생성
        qr_info = {
            'doorID': self.door_id,
            'passwd': self.passwd,
            'start': self.start,
            'end': self.end
        }

        # Generate unique ObjectID for this key
        # 이 키에 대한 고유 ObjectID 생성
        file_id = ObjectId()
        self.log_writter.info(f"Generated key with ID: {file_id}")

        # Auto-generate password if default
        # 기본값인 경우 비밀번호 자동 생성
        if self.passwd == 'default':
            qr_info['passwd'] = str(file_id)

        # Convert to JSON string
        # JSON 문자열로 변환
        qr_info_json = json.dumps(qr_info)

        # Generate QR code image
        # QR 코드 이미지 생성
        img = qrcode.make(qr_info_json)

        # Save QR code image with ObjectID as filename
        # ObjectID를 파일명으로 하여 QR 코드 이미지 저장
        key_path = f"{file_id}.png"
        img.save(key_path)

        self.log_writter.info(f"QR code saved to: {key_path}")

        return key_path, qr_info_json


def main():
    """
    Main function to generate and distribute QR code key.
    QR 코드 키를 생성하고 배포하는 메인 함수입니다.

    Process:
    1. Create a new DoorKey instance
    2. Generate QR code image and key info
    3. Publish key info to Pub/Sub
    4. Send QR code image via email

    처리 과정:
    1. 새 DoorKey 인스턴스 생성
    2. QR 코드 이미지 및 키 정보 생성
    3. Pub/Sub에 키 정보 게시
    4. 이메일로 QR 코드 이미지 전송
    """
    # Create door key instance with topic name as door ID
    # 토픽 이름을 도어 ID로 하여 도어 키 인스턴스 생성
    one_key = DoorKey(door_id=cfg.topic_name)

    # Generate QR code and key information
    # QR 코드 및 키 정보 생성
    qr_image, qr_info = one_key.create_key()

    # Convert string to bytes for Pub/Sub
    # Pub/Sub를 위해 문자열을 바이트로 변환
    qr_info_bytes = bytes(qr_info, 'utf-8')

    # Publish to Pub/Sub
    # Pub/Sub에 게시
    pub.pub(cfg.project_id, cfg.topic_name, qr_info_bytes)

    # Send email with QR code image
    # QR 코드 이미지를 이메일로 전송
    em.key_sender(key_path=qr_image, owner_address=cfg.email_to)

    print(f"Key generated and distributed successfully: {qr_image}")


if __name__ == "__main__":
    main()
