"""
QR Code Scanner and Validator Module
QR 코드 스캐너 및 검증기 모듈

Scans QR codes via camera and validates against stored key.
카메라를 통해 QR 코드를 스캔하고 저장된 키와 대조하여 검증합니다.
"""

import pyzbar.pyzbar as pyzbar
import cv2
import json
import os
import logger
import sys
from datetime import datetime, timedelta
import RPi.GPIO as GPIO
import time

# Configure GPIO for door lock control
# 도어락 제어를 위한 GPIO 설정
GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering / BCM 핀 번호 사용
GPIO.setup(17, GPIO.OUT)  # GPIO 17 as output / GPIO 17을 출력으로 설정

# Initialize logger
# 로거 초기화
log = logger.logger(log_path="./logs.txt")


def read_key(key_path):
    """
    Read key information from JSON file.
    JSON 파일에서 키 정보를 읽습니다.

    Args:
        key_path (str): Path to keyinfo.json file
                       keyinfo.json 파일 경로

    Returns:
        dict: Key information containing doorID, passwd, start, end times
             doorID, passwd, start, end 시간을 포함하는 키 정보

    Raises:
        SystemExit: If key file does not exist
                   키 파일이 존재하지 않을 경우
    """
    if os.path.isfile(key_path):
        with open(key_path, 'r') as f:
            exist_key = json.load(f)
    else:
        log.error(f"Key file not found: {key_path}")
        sys.exit()

    return exist_key


def validate_key(scanned_key, stored_key):
    """
    Validate scanned QR code against stored key.
    스캔된 QR 코드를 저장된 키와 대조하여 검증합니다.

    Args:
        scanned_key (dict): QR code data scanned from camera
                           카메라에서 스캔한 QR 코드 데이터
        stored_key (dict): Valid key data from keyinfo.json
                          keyinfo.json의 유효한 키 데이터

    Returns:
        bool: True if all fields match, False otherwise
             모든 필드가 일치하면 True, 그렇지 않으면 False
    """
    for key, value in stored_key.items():
        if scanned_key.get(key) != value:
            log.error(
                f"Key mismatch - Field: {key}, Expected: {value}, Got: {scanned_key.get(key)}"
            )
            return False
    return True


def unlock_door():
    """
    Unlock door by setting GPIO 17 to HIGH for 5 seconds.
    GPIO 17을 5초간 HIGH로 설정하여 도어를 잠금 해제합니다.
    """
    log.info("Door unlocked")
    print("doorOpen")

    # Set GPIO 17 to HIGH to unlock
    # GPIO 17을 HIGH로 설정하여 잠금 해제
    GPIO.output(17, True)

    # Keep door unlocked for 5 seconds
    # 도어를 5초간 잠금 해제 상태로 유지
    time.sleep(5)

    # Set GPIO 17 to LOW to lock
    # GPIO 17을 LOW로 설정하여 잠금
    GPIO.output(17, False)


def cleanup_and_exit():
    """
    Clean up resources and exit the program.
    리소스를 정리하고 프로그램을 종료합니다.
    """
    cap.release()
    cv2.destroyAllWindows()
    GPIO.cleanup()
    log.info("QR scanner terminated")
    sys.exit()


# Initialize camera
# 카메라 초기화
cap = cv2.VideoCapture(0)

# Read initial key information
# 초기 키 정보 읽기
exist_key = read_key("keyinfo.json")
pre_pass = exist_key["passwd"]  # Store initial password to detect key changes
                                # 키 변경을 감지하기 위해 초기 비밀번호 저장

# Parse start and end times
# 시작 및 종료 시간 파싱
starttime = datetime.strptime(exist_key['start'], "%Y-%m-%d, %H:%M:%S")
endtime = datetime.strptime(exist_key['end'], "%Y-%m-%d, %H:%M:%S")
now = datetime.now()

# Initialize state variables
# 상태 변수 초기화
key_test = False
pre_time = now - timedelta(minutes=10)  # Initialize to allow first unlock
                                        # 첫 번째 잠금 해제를 허용하도록 초기화

# Main scanning loop - runs while key is valid
# 메인 스캔 루프 - 키가 유효한 동안 실행
while starttime < now and endtime > now:
    # Capture frame from camera
    # 카메라에서 프레임 캡처
    ret, img = cap.read()

    if not ret:
        # Skip if frame capture failed
        # 프레임 캡처 실패 시 건너뛰기
        continue

    # Convert to grayscale for better QR code detection
    # 더 나은 QR 코드 감지를 위해 그레이스케일로 변환
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Decode QR codes in the frame
    # 프레임에서 QR 코드 디코딩
    decoded = pyzbar.decode(gray)

    # Process each detected QR code
    # 감지된 각 QR 코드 처리
    for d in decoded:
        x, y, w, h = d.rect  # QR code bounding box / QR 코드 경계 상자

        # Decode QR data from bytes to string
        # QR 데이터를 바이트에서 문자열로 디코딩
        barcode_data = d.data.decode("utf-8")
        barcode_type = d.type

        try:
            # Parse QR code data as JSON
            # QR 코드 데이터를 JSON으로 파싱
            read_key_data = json.loads(barcode_data)

            # Validate scanned key against stored key
            # 스캔한 키를 저장된 키와 대조하여 검증
            key_test = validate_key(read_key_data, exist_key)

        except json.JSONDecodeError:
            # Invalid QR code format
            # 잘못된 QR 코드 형식
            log.error(f"Invalid QR code format: {barcode_data}")
            key_test = False

    # Check if key is valid and rate limit not exceeded
    # Rate limit: max 1 unlock per minute
    # 키가 유효하고 속도 제한을 초과하지 않았는지 확인
    # 속도 제한: 분당 최대 1회 잠금 해제
    if key_test and (datetime.now() - pre_time) > timedelta(minutes=1):
        unlock_door()
        key_test = False
        pre_time = datetime.now()  # Update last unlock time / 마지막 잠금 해제 시간 업데이트
    else:
        key_test = False

    # Check if key has been updated (password changed)
    # 키가 업데이트되었는지 확인 (비밀번호 변경됨)
    exist_key = read_key("keyinfo.json")
    if exist_key['passwd'] != pre_pass:
        # Exit if new key has been issued
        # 새 키가 발급된 경우 종료
        log.info("New key detected, restarting scanner")
        cleanup_and_exit()

    # Update current time for loop condition check
    # 루프 조건 확인을 위해 현재 시간 업데이트
    now = datetime.now()

# Key expired, clean up and exit
# 키가 만료됨, 정리 후 종료
log.info("Key expired")
cleanup_and_exit()
