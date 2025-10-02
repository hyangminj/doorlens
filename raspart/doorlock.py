"""
Door Lock Control Module
도어락 제어 모듈

Direct GPIO control for testing door lock mechanism.
도어락 메커니즘 테스트를 위한 직접 GPIO 제어입니다.
"""

import RPi.GPIO as GPIO
import time

# Set GPIO mode to BCM (Broadcom SOC channel numbering)
# GPIO 모드를 BCM으로 설정 (Broadcom SOC 채널 번호 방식)
GPIO.setmode(GPIO.BCM)

# Configure GPIO pin 17 as output for door lock control
# 도어락 제어를 위해 GPIO 핀 17을 출력으로 설정
GPIO.setup(17, GPIO.OUT)


def dooropen():
    """
    Open door lock for 10 seconds.
    도어락을 10초간 엽니다.

    Returns:
        int: 0 on successful completion
            성공적으로 완료되면 0 반환
    """
    # Set GPIO 17 to HIGH to unlock door
    # GPIO 17을 HIGH로 설정하여 도어 잠금 해제
    GPIO.output(17, True)

    # Keep door unlocked for 10 seconds
    # 도어를 10초간 잠금 해제 상태로 유지
    time.sleep(10)

    # Set GPIO 17 to LOW to lock door
    # GPIO 17을 LOW로 설정하여 도어 잠금
    GPIO.output(17, False)

    # Clean up GPIO settings
    # GPIO 설정 정리
    GPIO.cleanup()

    return 0


if __name__ == "__main__":
    print("door opened!")
    dooropen()
