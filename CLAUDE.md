# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Note on Line Number References**: This documentation includes specific line number references (e.g., `rasberryQR.py:125-126`) that are accurate as of commit `d36c2e5` (2025-10-06). These references may become outdated if code changes. When in doubt, search for function names or use the described functionality as the primary reference.

## Project Overview

DoorLens is an IoT smart door lock system that uses QR code authentication. The system consists of two main components:

- **hostpart**: Server-side key generation and distribution (runs on any machine with Python)
- **raspart**: Raspberry Pi QR scanner and door controller (requires Raspberry Pi with camera and GPIO)

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
- Defines `DoorKey` class for creating time-limited keys
- `DoorKey.__init__(door_id, passwd, expire_minutes)` - Initialize with optional parameters
- `DoorKey.create_key()` - Generates QR image and returns (key_path, qr_info_json)
- Auto-generates password using MongoDB ObjectId if passwd='default'
- Saves QR codes as `<ObjectID>.png` in current directory
- `main()` function orchestrates: key creation → Pub/Sub publish → email send

**hostpart/pub.py** - Google Cloud Pub/Sub publisher
- `pub(project_id, topic_name, message_bytes)` - Publishes key data to topic

**hostpart/emailsend.py** - Email delivery via Gmail SMTP
- `key_sender(key_path, owner_address)` - Sends QR code image as email attachment
- Uses Gmail SMTP (smtp.gmail.com:587) with TLS

**hostpart/logger.py** - Logging utility
- `logger(log_path)` - Returns configured logger instance named 'snowdeer_log'
- Logs to both file and console with format: `[LEVEL] (filename:line) > message`

**raspart/sub.py** - Pub/Sub subscriber daemon
- Listens for new key messages from Pub/Sub
- Writes received key to `keyinfo.json`
- Launches `rasberryQR.py` as subprocess when new key arrives
- Runs continuously until manually stopped

**raspart/rasberryQR.py** - QR code scanner and validator (main logic)
- Captures video from camera (`cv2.VideoCapture(0)`)
- Decodes QR codes using pyzbar in real-time
- Validates scanned QR against `keyinfo.json`:
  - `validate_key(scanned, stored)` - Checks all fields match (doorID, passwd, start, end)
  - `read_key(path)` - Loads key from JSON file
- Controls GPIO pin 17 for door lock (5 second activation via `unlock_door()`)
- **Rate limiting**: Maximum 1 unlock per minute (uses timedelta comparison)
- **Auto-restart**: Monitors keyinfo.json for password changes, exits to allow sub.py to restart
- **Time validation**: Only runs while `starttime < now < endtime`
- **Cleanup**: Releases camera, destroys CV2 windows, calls GPIO.cleanup() on exit

**raspart/doorlock.py** - Direct door control utility for testing
- `dooropen()` - Activates GPIO 17 for 10 seconds then cleanup

### Dependencies

See `requirements.txt` for complete list. Key dependencies:
- `google-cloud-pubsub` - Pub/Sub communication
- `opencv-python` - Camera and image processing
- `pyzbar` - QR code decoding
- `qrcode` + `Pillow` - QR code generation
- `pymongo` - For bson.ObjectId (random password generation)
- `RPi.GPIO` - Raspberry Pi GPIO control (Pi only)
- `pytest`, `pytest-cov`, `pytest-mock` - Testing framework

## Configuration Requirements

Both hostpart and raspart require a `config.py` file (not included in repository for security reasons).

### Setting Up Configuration Files

**hostpart/config.py**:
```python
project_id = "your-gcp-project-id"
topic_name = "your-pubsub-topic"
email_id = "your-gmail-username"
email_passwd = "your-gmail-app-password"  # See security note below
email_to = "recipient@example.com"
```

**raspart/config.py**:
```python
project_id = "your-gcp-project-id"
subscription_name = "your-pubsub-subscription"
```

### Security Notes

⚠️ **Important Security Considerations**:

1. **Gmail App Passwords**:
   - `email_passwd` must be a Gmail App-Specific Password, NOT your regular Gmail password
   - Generate at: https://myaccount.google.com/apppasswords (requires 2FA enabled)
   - Never commit actual passwords to version control

2. **Google Cloud Credentials**:
   - Ensure Google Cloud service account JSON key is configured
   - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable or use default credentials
   - Service account needs `roles/pubsub.publisher` (host) and `roles/pubsub.subscriber` (Pi)

3. **Config File Protection**:
   - Config files are in `.gitignore` to prevent accidental commits
   - Set appropriate file permissions: `chmod 600 config.py`
   - Never share config files or include them in documentation/screenshots

4. **GPIO Pin Selection**:
   - Pin 17 (BCM numbering) is hardcoded for door lock control
   - To use a different pin, modify `GPIO.setup()` calls in rasberryQR.py and doorlock.py
   - BCM pin 17 = Physical pin 11 on Raspberry Pi header

## Running the System

### Generate and distribute a new key (on host):
```bash
cd hostpart
python3 testpart.py
```

### Start the door lock listener (on Raspberry Pi):
```bash
cd raspart
python3 sub.py
```

### Test door lock directly (on Raspberry Pi):
```bash
cd raspart
python3 doorlock.py
```

## Testing

The project includes comprehensive unit tests for both components:

### Run all tests:
```bash
pytest
```

### Run tests with coverage:
```bash
pytest --cov=hostpart --cov=raspart --cov-report=html
```

### Run specific test file:
```bash
# Test host part only
python3 -m pytest hostpart/test_hostpart.py -v

# Test Raspberry Pi part only
python3 -m pytest raspart/test_raspart.py -v
```

### Run a single test:
```bash
python3 -m pytest hostpart/test_hostpart.py::TestDoorKey::test_create_key_generates_qr_code -v
```

## Important Implementation Details

### QR Code Data Format
The QR code contains JSON with 4 fields:
```json
{
  "doorID": "topic-name-from-config",
  "passwd": "auto-generated-objectid-string",
  "start": "2025-01-01, 10:00:00",
  "end": "2025-01-01, 10:10:00"
}
```

### Time Validation Logic
- Times are stored as strings in format: `"%Y-%m-%d, %H:%M:%S"`
- Parsed with `datetime.strptime()` in rasberryQR.py:125-126
- Scanner only runs while `starttime < now < endtime` (rasberryQR.py:137)
- Loop updates `now = datetime.now()` each iteration (rasberryQR.py:202)
- **Timezone**: All times use local system time (no timezone conversion)
  - Host and Pi should be in same timezone or times may be incorrect
  - Consider using UTC for distributed deployments

### Rate Limiting Implementation
- Prevents door from unlocking more than once per minute
- Uses `pre_time` variable initialized to `now - timedelta(minutes=10)` (rasberryQR.py:132)
  - Initial value of 10 minutes in the past allows immediate unlock on first valid scan
  - This prevents waiting 1 minute after scanner starts
- Check: `if key_test and (datetime.now() - pre_time) > timedelta(minutes=1)` (rasberryQR.py:184)
- Updates `pre_time = datetime.now()` after each unlock (rasberryQR.py:187)

### Auto-Restart Mechanism
- Scanner monitors keyinfo.json for password changes every loop iteration (rasberryQR.py:193-198)
- Stores initial password in `pre_pass` variable (rasberryQR.py:120)
- If `exist_key['passwd'] != pre_pass`, calls `cleanup_and_exit()` (rasberryQR.py:194-198)
- This allows sub.py to restart scanner with new key

### GPIO Configuration
- Uses BCM pin numbering: `GPIO.setmode(GPIO.BCM)` (rasberryQR.py:21)
- Pin 17 configured as output: `GPIO.setup(17, GPIO.OUT)` (rasberryQR.py:22)
- Unlock sequence: `GPIO.output(17, True)` → sleep(5) → `GPIO.output(17, False)` (rasberryQR.py:90-98)
- Always call `GPIO.cleanup()` before exit (rasberryQR.py:108)

### Logger Usage
- Logger instance is named 'snowdeer_log' (logger.py:28)
- Both components use logger for debugging and audit trail
- hostpart logs to `./log.txt` (testpart.py:71)
- raspart logs to `./logs.txt` (rasberryQR.py:26)

## Key Security Features

- Time-based key expiration (default 10 minutes, configurable via `expire_minutes` parameter)
- Random password generation using MongoDB ObjectID (24-character hex string)
- Keys automatically invalidate outside time window
- QR scanner exits when password changes in keyinfo.json
- Rate limiting prevents repeated door activations (max 1/minute)

## Error Handling and Common Failure Scenarios

### Camera Initialization Failure
**Symptom**: `cv2.VideoCapture(0)` fails or returns None
- **Check**: Camera device exists with `ls -l /dev/video*`
- **Fix**: Ensure camera is connected and enabled in `raspi-config`
- **Behavior**: Scanner will run but `cap.read()` returns `(False, None)`, causing continuous loop skipping
- **Code**: No explicit error handling - loop continues with `continue` when `ret` is False (rasberryQR.py:143-145)

### Pub/Sub Connection Failure
**Symptom**: Messages not published/received
- **hostpart**: `pub.pub()` may raise exceptions if project_id or topic_name is invalid
- **raspart**: `sub.py` subscriber will block indefinitely waiting for messages
- **Check**: Verify GCP credentials with `gcloud auth application-default login`
- **Check**: Ensure topic and subscription exist in GCP console
- **Logs**: Check logs.txt for authentication or permission errors

### Missing keyinfo.json
**Symptom**: Scanner exits immediately with SystemExit
- **Cause**: `read_key()` calls `sys.exit()` if file doesn't exist (rasberryQR.py:50-51)
- **Fix**: Ensure `sub.py` has received at least one message to create keyinfo.json
- **Prevention**: Run `python3 hostpart/testpart.py` before starting scanner

### Invalid QR Code Format
**Symptom**: QR codes scanned but door doesn't unlock
- **Cause**: JSON parsing fails or fields don't match
- **Behavior**: `json.JSONDecodeError` caught, `key_test` set to False (rasberryQR.py:174-178)
- **Logs**: Error logged with message "Invalid QR code format: {data}"
- **Debug**: Check that QR contains valid JSON with all required fields

### GPIO Permission Denied
**Symptom**: `GPIO.setup()` raises permission error
- **Fix**: Run as root (`sudo python3`) or add user to gpio group
- **Fix**: `sudo usermod -a -G gpio $USER` then logout/login
- **Note**: Production deployments should use systemd service running as privileged user

### Email Sending Failures
**Symptom**: Key generated but email not received
- **Common causes**:
  - Using regular Gmail password instead of App Password
  - Gmail account doesn't have 2FA enabled (required for App Passwords)
  - SMTP port 587 blocked by firewall
  - Incorrect recipient address
- **Debug**: Check host logs for SMTP errors
- **Test**: Try manual SMTP connection: `telnet smtp.gmail.com 587`

### Time Synchronization Issues
**Symptom**: Valid QR code rejected due to time mismatch
- **Cause**: Host and Pi system clocks out of sync
- **Check**: Compare times with `date` command on both machines
- **Fix**: Enable NTP on both systems:
  - `sudo timedatectl set-ntp true`
  - `sudo systemctl restart systemd-timesyncd`
- **Verify**: `timedatectl status` shows "System clock synchronized: yes"
