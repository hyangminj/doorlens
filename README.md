# DoorLens

An IoT smart door lock system using QR code authentication with Google Cloud Pub/Sub.

## Overview

DoorLens is a distributed IoT system that enables secure door access through time-limited QR codes. The system consists of a host server that generates QR keys and a Raspberry Pi controller that validates codes and operates the door lock.

## Architecture

### Components

- **hostpart**: Server-side key generation and distribution
- **raspart**: Raspberry Pi QR scanner and door controller

### Communication Flow

1. Host server generates temporary QR code key with expiration time
2. Key is published to Google Cloud Pub/Sub topic
3. QR code image is emailed to authorized user
4. Raspberry Pi subscribes to Pub/Sub and receives key updates
5. Pi continuously scans QR codes via camera
6. Valid QR code within time window triggers GPIO pin 17 to unlock door

## Features

- Time-based key expiration (default: 10 minutes, configurable)
- Random password generation using MongoDB ObjectID
- Automatic key invalidation outside time window
- Real-time key distribution via Google Cloud Pub/Sub
- Email delivery of QR code images
- Rate limiting (max 1 door activation per minute)
- Automatic scanner restart on key changes

## Requirements

### Hardware
- Raspberry Pi (with camera module or USB camera)
- GPIO-controlled door lock mechanism
- Network connectivity

### Software Dependencies
```
google-cloud-pubsub
opencv-python (cv2)
pyzbar
qrcode
RPi.GPIO
```

## Configuration

Both components require a `config.py` file (not included in repository for security).

### hostpart/config.py
```python
project_id = "your-gcp-project-id"
topic_name = "your-pubsub-topic"
email_id = "your-gmail-username"
email_passwd = "your-gmail-app-password"
email_to = "recipient@example.com"
```

### raspart/config.py
```python
project_id = "your-gcp-project-id"
subscription_name = "your-pubsub-subscription"
```

## Installation

### Host Server Setup
```bash
cd hostpart
pip install google-cloud-pubsub qrcode pillow
# Create config.py with your credentials
```

### Raspberry Pi Setup
```bash
cd raspart
pip install google-cloud-pubsub opencv-python pyzbar RPi.GPIO
# Create config.py with your credentials
```

## Usage

### Generate and Distribute New Key (Host Server)
```bash
python3 hostpart/testpart.py
```

This will:
- Generate a new time-limited QR code
- Save QR image as `<ObjectID>.png`
- Publish key to Pub/Sub
- Email QR code to configured recipient

### Start Door Lock System (Raspberry Pi)
```bash
python3 raspart/sub.py
```

The system will:
- Listen for new keys from Pub/Sub
- Launch QR scanner when key is received
- Validate scanned codes against current key
- Trigger door lock (GPIO pin 17) for 5 seconds on valid scan
- Automatically restart when new key is published

### Test Door Lock Directly (Raspberry Pi)
```bash
python3 raspart/doorlock.py
```

Activates door lock for 10 seconds (testing purposes).

## File Structure

```
doorlens/
├── hostpart/
│   ├── testpart.py      # Key generation entry point
│   ├── pub.py           # Pub/Sub publisher
│   ├── emailsend.py     # Email delivery
│   ├── doorkey.py       # Key data model
│   └── config.py        # Configuration (not in repo)
├── raspart/
│   ├── sub.py           # Pub/Sub subscriber
│   ├── rasberryQR.py    # QR scanner and validator
│   ├── doorlock.py      # GPIO door control
│   ├── keyinfo.json     # Current key storage
│   └── config.py        # Configuration (not in repo)
└── README.md
```

## Security Features

- **Time-based expiration**: Keys only valid within configured time window
- **Random password generation**: Cryptographically secure ObjectID
- **Automatic invalidation**: Keys expire outside time window
- **Real-time updates**: Scanner exits when password changes
- **Rate limiting**: Prevents rapid repeated activations
- **No hardcoded credentials**: All sensitive data in config files

## GPIO Configuration

- **Pin 17**: Door lock control
- **Activation time**: 5 seconds (QR scanner) / 10 seconds (test mode)
- **Logic**: HIGH to unlock, LOW to lock

## Troubleshooting

### Camera not detected
```bash
ls -l /dev/video*
# Ensure camera device exists
```

### Pub/Sub authentication errors
- Verify Google Cloud credentials are properly configured
- Ensure service account has Pub/Sub permissions

### QR codes not scanning
- Check camera focus and lighting
- Verify pyzbar installation: `python3 -c "import pyzbar"`

### Door lock not activating
- Verify GPIO permissions
- Check physical wiring to pin 17
- Test with `doorlock.py`

## License

[Specify your license here]

---

# DoorLens (한국어)

Google Cloud Pub/Sub를 활용한 QR 코드 인증 기반 IoT 스마트 도어락 시스템입니다.

## 개요

DoorLens는 시간 제한이 있는 QR 코드를 통해 안전한 출입을 가능하게 하는 분산형 IoT 시스템입니다. QR 키를 생성하는 호스트 서버와 코드를 검증하고 도어락을 작동하는 라즈베리파이 컨트롤러로 구성됩니다.

## 아키텍처

### 구성요소

- **hostpart**: 서버측 키 생성 및 배포
- **raspart**: 라즈베리파이 QR 스캐너 및 도어 컨트롤러

### 통신 흐름

1. 호스트 서버가 만료 시간이 있는 임시 QR 코드 키 생성
2. 키를 Google Cloud Pub/Sub 토픽에 게시
3. QR 코드 이미지를 인증된 사용자에게 이메일 전송
4. 라즈베리파이가 Pub/Sub을 구독하고 키 업데이트 수신
5. 파이가 카메라를 통해 지속적으로 QR 코드 스캔
6. 시간 범위 내 유효한 QR 코드가 GPIO 핀 17을 트리거하여 도어락 해제

## 기능

- 시간 기반 키 만료 (기본값: 10분, 설정 가능)
- MongoDB ObjectID를 사용한 랜덤 비밀번호 생성
- 시간 범위 외 자동 키 무효화
- Google Cloud Pub/Sub를 통한 실시간 키 배포
- QR 코드 이미지 이메일 전송
- 속도 제한 (분당 최대 1회 도어 활성화)
- 키 변경 시 자동 스캐너 재시작

## 요구사항

### 하드웨어
- 라즈베리파이 (카메라 모듈 또는 USB 카메라 포함)
- GPIO 제어 도어락 장치
- 네트워크 연결

### 소프트웨어 의존성
```
google-cloud-pubsub
opencv-python (cv2)
pyzbar
qrcode
RPi.GPIO
```

## 설정

두 구성요소 모두 `config.py` 파일이 필요합니다 (보안상 저장소에 미포함).

### hostpart/config.py
```python
project_id = "your-gcp-project-id"
topic_name = "your-pubsub-topic"
email_id = "your-gmail-username"
email_passwd = "your-gmail-app-password"
email_to = "recipient@example.com"
```

### raspart/config.py
```python
project_id = "your-gcp-project-id"
subscription_name = "your-pubsub-subscription"
```

## 설치

### 호스트 서버 설정
```bash
cd hostpart
pip install google-cloud-pubsub qrcode pillow
# 인증 정보가 포함된 config.py 생성
```

### 라즈베리파이 설정
```bash
cd raspart
pip install google-cloud-pubsub opencv-python pyzbar RPi.GPIO
# 인증 정보가 포함된 config.py 생성
```

## 사용법

### 새 키 생성 및 배포 (호스트 서버)
```bash
python3 hostpart/testpart.py
```

실행 내용:
- 시간 제한이 있는 새 QR 코드 생성
- QR 이미지를 `<ObjectID>.png`로 저장
- Pub/Sub에 키 게시
- 설정된 수신자에게 QR 코드 이메일 전송

### 도어락 시스템 시작 (라즈베리파이)
```bash
python3 raspart/sub.py
```

시스템 동작:
- Pub/Sub에서 새 키 수신 대기
- 키 수신 시 QR 스캐너 실행
- 스캔된 코드를 현재 키와 대조하여 검증
- 유효한 스캔 시 도어락 트리거 (GPIO 핀 17, 5초간)
- 새 키 게시 시 자동 재시작

### 도어락 직접 테스트 (라즈베리파이)
```bash
python3 raspart/doorlock.py
```

도어락을 10초간 활성화 (테스트 목적).

## 파일 구조

```
doorlens/
├── hostpart/
│   ├── testpart.py      # 키 생성 진입점
│   ├── pub.py           # Pub/Sub 게시자
│   ├── emailsend.py     # 이메일 전송
│   ├── doorkey.py       # 키 데이터 모델
│   └── config.py        # 설정 (저장소 미포함)
├── raspart/
│   ├── sub.py           # Pub/Sub 구독자
│   ├── rasberryQR.py    # QR 스캐너 및 검증기
│   ├── doorlock.py      # GPIO 도어 제어
│   ├── keyinfo.json     # 현재 키 저장소
│   └── config.py        # 설정 (저장소 미포함)
└── README.md
```

## 보안 기능

- **시간 기반 만료**: 설정된 시간 범위 내에서만 키 유효
- **랜덤 비밀번호 생성**: 암호학적으로 안전한 ObjectID
- **자동 무효화**: 시간 범위 외 키 만료
- **실시간 업데이트**: 비밀번호 변경 시 스캐너 종료
- **속도 제한**: 빠른 반복 활성화 방지
- **하드코딩된 인증 정보 없음**: 모든 민감한 데이터는 config 파일에 저장

## GPIO 설정

- **핀 17**: 도어락 제어
- **활성화 시간**: 5초 (QR 스캐너) / 10초 (테스트 모드)
- **로직**: HIGH는 잠금 해제, LOW는 잠금

## 문제 해결

### 카메라 감지 안 됨
```bash
ls -l /dev/video*
# 카메라 장치가 존재하는지 확인
```

### Pub/Sub 인증 오류
- Google Cloud 인증 정보가 올바르게 설정되었는지 확인
- 서비스 계정에 Pub/Sub 권한이 있는지 확인

### QR 코드 스캔 안 됨
- 카메라 초점 및 조명 확인
- pyzbar 설치 확인: `python3 -c "import pyzbar"`

### 도어락 활성화 안 됨
- GPIO 권한 확인
- 핀 17 물리적 배선 확인
- `doorlock.py`로 테스트

## 라이선스

[라이선스를 여기에 명시하세요]
