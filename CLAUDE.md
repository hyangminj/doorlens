# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DoorLens is an IoT smart door lock system that uses QR code authentication. The system consists of two main components:

- **hostpart**: Runs on a server/host machine to generate and distribute QR code keys
- **raspart**: Runs on a Raspberry Pi at the door location to scan QR codes and control the door lock

## Architecture

### Communication Flow

1. Host generates a temporary QR code key with time-based expiration
2. Key data is published to Google Cloud Pub/Sub topic
3. Key is also emailed to the user as a PNG image
4. Raspberry Pi subscribes to Pub/Sub and receives key updates
5. Raspberry Pi continuously scans QR codes via camera
6. When valid QR code is scanned within time window, GPIO pin 17 triggers door lock

### Key Components

**hostpart/testpart.py** - Main entry point for key generation
- Creates `doorkey` objects with configurable expiration time
- Generates QR code images saved as `<ObjectID>.png`
- Publishes key to Pub/Sub via `pub.py`
- Sends key via email using `emailsend.py`
- Requires `config.py` with: `project_id`, `topic_name`, `email_id`, `email_passwd`, `email_to`

**raspart/sub.py** - Pub/Sub subscriber that runs continuously on Raspberry Pi
- Listens for new key messages from Pub/Sub
- Writes received key to `keyinfo.json`
- Launches `rasberryQR.py` when new key arrives
- Requires `config.py` with: `project_id`, `subscription_name`

**raspart/rasberryQR.py** - QR code scanner and door controller
- Captures video from camera (cv2.VideoCapture(0))
- Decodes QR codes using pyzbar
- Validates QR against `keyinfo.json` (checks doorID, passwd, start/end times)
- Controls GPIO pin 17 for door lock (5 second activation)
- Monitors for key changes and exits if password updated
- Rate-limited to open door max once per minute

**raspart/doorlock.py** - Direct door control utility
- Simple GPIO control for testing (10 second activation)

### Dependencies

The project requires:
- Google Cloud Pub/Sub SDK (`google-cloud-pubsub`)
- OpenCV (`cv2`)
- pyzbar (QR code decoding)
- qrcode (QR code generation)
- RPi.GPIO (Raspberry Pi GPIO control)
- Standard libraries: smtplib, json, datetime, logging

## Configuration Requirements

Both hostpart and raspart require a `config.py` file (not in repository) with:

**hostpart config.py**:
```python
project_id = "your-gcp-project-id"
topic_name = "your-pubsub-topic"
email_id = "your-gmail-username"
email_passwd = "your-gmail-app-password"
email_to = "recipient@example.com"
```

**raspart config.py**:
```python
project_id = "your-gcp-project-id"
subscription_name = "your-pubsub-subscription"
```

## Running the System

### Generate and distribute a new key (on host):
```bash
python3 hostpart/testpart.py
```

### Start the door lock listener (on Raspberry Pi):
```bash
python3 raspart/sub.py
```

### Test door lock directly (on Raspberry Pi):
```bash
python3 raspart/doorlock.py
```

## Key Security Features

- Time-based key expiration (default 10 minutes, configurable in `doorkey.expire_time`)
- Random password generation using MongoDB ObjectID
- Keys automatically invalidate outside time window
- QR scanner exits when password changes in keyinfo.json
- Rate limiting prevents repeated door activations
