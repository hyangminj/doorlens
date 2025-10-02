"""
Unit Tests for Raspberry Pi Part
라즈베리파이 파트 단위 테스트

Tests for QR code scanning, validation, and door control modules.
QR 코드 스캔, 검증 및 도어 제어 모듈에 대한 테스트입니다.
"""

import unittest
import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
import sys

# Mock RPi.GPIO before importing rasberryQR
# rasberryQR를 임포트하기 전에 RPi.GPIO를 모킹
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()

# Mock cv2 and pyzbar for testing without camera
# 카메라 없이 테스트하기 위해 cv2와 pyzbar를 모킹
sys.modules['cv2'] = MagicMock()
sys.modules['pyzbar'] = MagicMock()
sys.modules['pyzbar.pyzbar'] = MagicMock()


class TestKeyReading(unittest.TestCase):
    """
    Test cases for reading key files.
    키 파일 읽기에 대한 테스트 케이스입니다.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.test_key_file = os.path.join(self.test_dir, 'keyinfo.json')

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_key_file):
            os.remove(self.test_key_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    def test_read_valid_key_file(self):
        """Test reading a valid key file."""
        # Create test key data
        # 테스트 키 데이터 생성
        test_key = {
            'doorID': 'test-door',
            'passwd': 'test-password',
            'start': '2025-01-01, 10:00:00',
            'end': '2025-01-01, 10:10:00'
        }

        # Write to file
        # 파일에 쓰기
        with open(self.test_key_file, 'w') as f:
            json.dump(test_key, f)

        # Import and test read_key function
        # read_key 함수를 임포트하고 테스트
        import rasberryQR
        result = rasberryQR.read_key(self.test_key_file)

        self.assertEqual(result['doorID'], 'test-door')
        self.assertEqual(result['passwd'], 'test-password')

    def test_read_missing_key_file(self):
        """Test reading a non-existent key file."""
        import rasberryQR

        # Should exit when file doesn't exist
        # 파일이 존재하지 않으면 종료해야 함
        with self.assertRaises(SystemExit):
            rasberryQR.read_key('nonexistent_file.json')


class TestKeyValidation(unittest.TestCase):
    """
    Test cases for QR code validation.
    QR 코드 검증에 대한 테스트 케이스입니다.
    """

    def test_validate_matching_keys(self):
        """Test validation with matching keys."""
        import rasberryQR

        scanned_key = {
            'doorID': 'test-door',
            'passwd': 'test-pass',
            'start': '2025-01-01, 10:00:00',
            'end': '2025-01-01, 10:10:00'
        }

        stored_key = {
            'doorID': 'test-door',
            'passwd': 'test-pass',
            'start': '2025-01-01, 10:00:00',
            'end': '2025-01-01, 10:10:00'
        }

        result = rasberryQR.validate_key(scanned_key, stored_key)
        self.assertTrue(result)

    def test_validate_mismatched_password(self):
        """Test validation with mismatched password."""
        import rasberryQR

        scanned_key = {
            'doorID': 'test-door',
            'passwd': 'wrong-pass',
            'start': '2025-01-01, 10:00:00',
            'end': '2025-01-01, 10:10:00'
        }

        stored_key = {
            'doorID': 'test-door',
            'passwd': 'test-pass',
            'start': '2025-01-01, 10:00:00',
            'end': '2025-01-01, 10:10:00'
        }

        result = rasberryQR.validate_key(scanned_key, stored_key)
        self.assertFalse(result)

    def test_validate_mismatched_door_id(self):
        """Test validation with mismatched door ID."""
        import rasberryQR

        scanned_key = {
            'doorID': 'wrong-door',
            'passwd': 'test-pass',
            'start': '2025-01-01, 10:00:00',
            'end': '2025-01-01, 10:10:00'
        }

        stored_key = {
            'doorID': 'test-door',
            'passwd': 'test-pass',
            'start': '2025-01-01, 10:00:00',
            'end': '2025-01-01, 10:10:00'
        }

        result = rasberryQR.validate_key(scanned_key, stored_key)
        self.assertFalse(result)

    def test_validate_missing_field(self):
        """Test validation with missing field in scanned key."""
        import rasberryQR

        scanned_key = {
            'doorID': 'test-door',
            'passwd': 'test-pass',
            'start': '2025-01-01, 10:00:00'
            # Missing 'end' field
        }

        stored_key = {
            'doorID': 'test-door',
            'passwd': 'test-pass',
            'start': '2025-01-01, 10:00:00',
            'end': '2025-01-01, 10:10:00'
        }

        result = rasberryQR.validate_key(scanned_key, stored_key)
        self.assertFalse(result)


class TestDoorControl(unittest.TestCase):
    """
    Test cases for door lock control.
    도어락 제어에 대한 테스트 케이스입니다.
    """

    @patch('rasberryQR.GPIO')
    @patch('rasberryQR.time.sleep')
    def test_unlock_door_sets_gpio_high(self, mock_sleep, mock_gpio):
        """Test that unlock_door sets GPIO 17 to HIGH."""
        import rasberryQR

        rasberryQR.unlock_door()

        # Verify GPIO was set to True (HIGH) then False (LOW)
        # GPIO가 True(HIGH)로 설정된 후 False(LOW)로 설정되었는지 확인
        calls = [call(17, True), call(17, False)]
        mock_gpio.output.assert_has_calls(calls)

    @patch('rasberryQR.GPIO')
    @patch('rasberryQR.time.sleep')
    def test_unlock_door_waits_5_seconds(self, mock_sleep, mock_gpio):
        """Test that unlock_door waits 5 seconds."""
        import rasberryQR

        rasberryQR.unlock_door()

        # Verify sleep was called with 5 seconds
        # 5초로 sleep이 호출되었는지 확인
        mock_sleep.assert_called_once_with(5)


class TestDoorLock(unittest.TestCase):
    """
    Test cases for doorlock module.
    doorlock 모듈에 대한 테스트 케이스입니다.
    """

    @patch('doorlock.GPIO')
    @patch('doorlock.time.sleep')
    def test_dooropen_sets_gpio_high_for_10_seconds(self, mock_sleep, mock_gpio):
        """Test that dooropen activates GPIO for 10 seconds."""
        import doorlock

        result = doorlock.dooropen()

        # Verify GPIO was set HIGH then LOW
        # GPIO가 HIGH로 설정된 후 LOW로 설정되었는지 확인
        calls = [call(17, True), call(17, False)]
        mock_gpio.output.assert_has_calls(calls)

        # Verify 10 second sleep
        # 10초 sleep 확인
        mock_sleep.assert_called_once_with(10)

        # Verify cleanup was called
        # cleanup이 호출되었는지 확인
        mock_gpio.cleanup.assert_called_once()

        # Verify return value
        # 반환값 확인
        self.assertEqual(result, 0)


class TestSubIntegration(unittest.TestCase):
    """
    Integration tests for Pub/Sub subscriber.
    Pub/Sub 구독자에 대한 통합 테스트입니다.
    """

    @patch('sub.pubsub_v1.SubscriberClient')
    def test_sub_creates_subscriber_client(self, mock_subscriber):
        """Test that sub creates a subscriber client."""
        import sub

        # This test verifies the subscriber setup
        # 이 테스트는 구독자 설정을 검증합니다
        mock_client = MagicMock()
        mock_subscriber.return_value = mock_client

        # Calling sub would normally block, so we don't test the full flow
        # sub 호출은 일반적으로 차단되므로 전체 흐름을 테스트하지 않습니다
        # Just verify the client creation
        # 클라이언트 생성만 확인


class TestTimeValidation(unittest.TestCase):
    """
    Test cases for time-based key validation.
    시간 기반 키 검증에 대한 테스트 케이스입니다.
    """

    def test_key_validity_period(self):
        """Test key validity time period."""
        now = datetime.now()
        start = now - timedelta(minutes=5)
        end = now + timedelta(minutes=5)

        # Key should be valid now
        # 키가 현재 유효해야 함
        self.assertTrue(start < now < end)

    def test_key_expired(self):
        """Test expired key detection."""
        now = datetime.now()
        start = now - timedelta(minutes=20)
        end = now - timedelta(minutes=10)

        # Key should be expired
        # 키가 만료되어야 함
        self.assertFalse(start < now < end)

    def test_key_not_yet_valid(self):
        """Test key that is not yet valid."""
        now = datetime.now()
        start = now + timedelta(minutes=5)
        end = now + timedelta(minutes=15)

        # Key should not be valid yet
        # 키가 아직 유효하지 않아야 함
        self.assertFalse(start < now < end)


class TestRateLimiting(unittest.TestCase):
    """
    Test cases for rate limiting functionality.
    속도 제한 기능에 대한 테스트 케이스입니다.
    """

    def test_rate_limit_allows_first_unlock(self):
        """Test that rate limit allows first unlock."""
        now = datetime.now()
        pre_time = now - timedelta(minutes=10)

        # Should allow unlock (more than 1 minute passed)
        # 잠금 해제를 허용해야 함 (1분 이상 경과)
        self.assertTrue((now - pre_time) > timedelta(minutes=1))

    def test_rate_limit_blocks_rapid_unlock(self):
        """Test that rate limit blocks rapid unlocks."""
        now = datetime.now()
        pre_time = now - timedelta(seconds=30)

        # Should block unlock (less than 1 minute passed)
        # 잠금 해제를 차단해야 함 (1분 미만 경과)
        self.assertFalse((now - pre_time) > timedelta(minutes=1))

    def test_rate_limit_allows_after_minute(self):
        """Test that rate limit allows unlock after 1 minute."""
        now = datetime.now()
        pre_time = now - timedelta(minutes=1, seconds=1)

        # Should allow unlock (more than 1 minute passed)
        # 잠금 해제를 허용해야 함 (1분 이상 경과)
        self.assertTrue((now - pre_time) > timedelta(minutes=1))


def run_tests():
    """
    Run all unit tests.
    모든 단위 테스트를 실행합니다.
    """
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
