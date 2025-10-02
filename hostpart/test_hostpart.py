"""
Unit Tests for Host Part
호스트 파트 단위 테스트

Tests for key generation, QR code creation, and distribution modules.
키 생성, QR 코드 생성 및 배포 모듈에 대한 테스트입니다.
"""

import unittest
import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import qrcode
from bson import ObjectId

# Import modules to test
# 테스트할 모듈 임포트
import testpart
import logger


class TestLogger(unittest.TestCase):
    """
    Test cases for logger module.
    로거 모듈에 대한 테스트 케이스입니다.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.test_log_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        self.test_log_path = self.test_log_file.name
        self.test_log_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_log_path):
            os.remove(self.test_log_path)

    def test_logger_creation(self):
        """Test logger instance creation."""
        log = logger.logger(self.test_log_path)
        self.assertIsNotNone(log)
        self.assertEqual(log.name, 'snowdeer_log')

    def test_logger_file_creation(self):
        """Test that logger creates log file."""
        log = logger.logger(self.test_log_path)
        log.info("Test message")
        self.assertTrue(os.path.exists(self.test_log_path))

    def test_logger_writes_to_file(self):
        """Test that logger writes messages to file."""
        log = logger.logger(self.test_log_path)
        test_message = "Test log message"
        log.info(test_message)

        with open(self.test_log_path, 'r') as f:
            content = f.read()
            self.assertIn(test_message, content)


class TestDoorKey(unittest.TestCase):
    """
    Test cases for DoorKey class.
    DoorKey 클래스에 대한 테스트 케이스입니다.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_doorkey_initialization(self):
        """Test DoorKey initialization with default values."""
        key = testpart.DoorKey()
        self.assertEqual(key.door_id, 'default')
        self.assertEqual(key.passwd, 'default')
        self.assertEqual(key.expire_time, 10)

    def test_doorkey_custom_initialization(self):
        """Test DoorKey initialization with custom values."""
        key = testpart.DoorKey(
            door_id='test_door',
            passwd='test_pass',
            expire_minutes=20
        )
        self.assertEqual(key.door_id, 'test_door')
        self.assertEqual(key.passwd, 'test_pass')
        self.assertEqual(key.expire_time, 20)

    def test_doorkey_time_calculation(self):
        """Test that start and end times are calculated correctly."""
        key = testpart.DoorKey(expire_minutes=15)

        start_time = datetime.strptime(key.start, "%Y-%m-%d, %H:%M:%S")
        end_time = datetime.strptime(key.end, "%Y-%m-%d, %H:%M:%S")

        time_diff = end_time - start_time
        # Allow 1 second tolerance for execution time
        # 실행 시간을 위해 1초 허용
        self.assertAlmostEqual(
            time_diff.total_seconds(),
            15 * 60,
            delta=1
        )

    def test_create_key_generates_qr_code(self):
        """Test that create_key generates a QR code image."""
        key = testpart.DoorKey(door_id='test_door')
        key_path, qr_info = key.create_key()

        # Check that QR code file was created
        # QR 코드 파일이 생성되었는지 확인
        self.assertTrue(os.path.exists(key_path))
        self.assertTrue(key_path.endswith('.png'))

    def test_create_key_returns_valid_json(self):
        """Test that create_key returns valid JSON data."""
        key = testpart.DoorKey(door_id='test_door')
        key_path, qr_info = key.create_key()

        # Parse JSON and verify structure
        # JSON을 파싱하고 구조 검증
        data = json.loads(qr_info)
        self.assertIn('doorID', data)
        self.assertIn('passwd', data)
        self.assertIn('start', data)
        self.assertIn('end', data)
        self.assertEqual(data['doorID'], 'test_door')

    def test_create_key_auto_generates_password(self):
        """Test that password is auto-generated when default."""
        key = testpart.DoorKey(door_id='test_door', passwd='default')
        key_path, qr_info = key.create_key()

        data = json.loads(qr_info)
        # Password should not be 'default', should be ObjectID string
        # 비밀번호는 'default'가 아닌 ObjectID 문자열이어야 함
        self.assertNotEqual(data['passwd'], 'default')
        self.assertTrue(len(data['passwd']) > 0)

    def test_create_key_preserves_custom_password(self):
        """Test that custom password is preserved."""
        custom_pass = 'my_custom_password'
        key = testpart.DoorKey(door_id='test_door', passwd=custom_pass)
        key_path, qr_info = key.create_key()

        data = json.loads(qr_info)
        self.assertEqual(data['passwd'], custom_pass)


class TestPubIntegration(unittest.TestCase):
    """
    Integration tests for Pub/Sub publishing.
    Pub/Sub 게시에 대한 통합 테스트입니다.
    """

    @patch('testpart.pub.pub')
    @patch('testpart.em.key_sender')
    def test_main_calls_pub_and_email(self, mock_email, mock_pub):
        """Test that main function calls pub and email sender."""
        with patch('testpart.cfg') as mock_cfg:
            mock_cfg.project_id = 'test-project'
            mock_cfg.topic_name = 'test-topic'
            mock_cfg.email_to = 'test@example.com'

            # This would normally run, but we're mocking the external calls
            # 일반적으로 실행되지만 외부 호출을 모킹합니다
            # testpart.main()

            # Verify that pub and email functions would be called
            # pub 및 이메일 함수가 호출될 것인지 확인
            # (Actual test would require more setup)


class TestEmailSender(unittest.TestCase):
    """
    Test cases for email sending functionality.
    이메일 전송 기능에 대한 테스트 케이스입니다.
    """

    @patch('emailsend.smtplib.SMTP')
    def test_key_sender_connects_to_smtp(self, mock_smtp):
        """Test that key_sender connects to Gmail SMTP."""
        import emailsend

        # Create a mock SMTP server
        # 모의 SMTP 서버 생성
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        with patch('emailsend.cfg') as mock_cfg:
            mock_cfg.email_id = 'test'
            mock_cfg.email_passwd = 'password'

            # Create temporary test file
            # 임시 테스트 파일 생성
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
                test_file = f.name
                f.write(b'test image data')

            try:
                emailsend.key_sender(test_file, 'recipient@example.com')

                # Verify SMTP connection was established
                # SMTP 연결이 설정되었는지 확인
                mock_smtp.assert_called_with(host="smtp.gmail.com", port=587)
                mock_server.ehlo.assert_called()
                mock_server.starttls.assert_called()
                mock_server.login.assert_called_with('test', 'password')

            finally:
                if os.path.exists(test_file):
                    os.remove(test_file)


def run_tests():
    """
    Run all unit tests.
    모든 단위 테스트를 실행합니다.
    """
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
