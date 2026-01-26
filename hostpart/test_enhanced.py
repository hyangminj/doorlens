"""
Enhanced Unit Tests for Host Part
호스트 파트 향상된 단위 테스트

Tests for refactored key generator, email sender, and publisher.
리팩토링된 키 생성기, 이메일 전송기 및 게시자에 대한 테스트입니다.
"""

import unittest
import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from constants import (
    KeyGeneratorConfig,
    EmailConfig,
    PubSubConfig,
    DEFAULT_EXPIRE_MINUTES,
    DATETIME_FORMAT
)
from key_generator import KeyGenerator, GeneratedKey, DoorKey
from email_sender import EmailSender, EmailSendError
from publisher import PubSubPublisher, PublishError


class TestGeneratedKey(unittest.TestCase):
    """Test cases for GeneratedKey dataclass."""

    def test_to_dict_basic(self):
        """Test basic dictionary conversion."""
        key = GeneratedKey(
            door_id="test-door",
            passwd="test-pass",
            start="2025-01-01, 10:00:00",
            end="2025-01-01, 10:10:00"
        )

        result = key.to_dict()

        self.assertEqual(result['doorID'], "test-door")
        self.assertEqual(result['passwd'], "test-pass")
        self.assertEqual(result['start'], "2025-01-01, 10:00:00")
        self.assertEqual(result['end'], "2025-01-01, 10:10:00")
        self.assertNotIn('start_utc', result)

    def test_to_dict_with_utc(self):
        """Test dictionary conversion with UTC times."""
        key = GeneratedKey(
            door_id="test-door",
            passwd="test-pass",
            start="2025-01-01, 10:00:00",
            end="2025-01-01, 10:10:00",
            start_utc="2025-01-01T01:00:00Z",
            end_utc="2025-01-01T01:10:00Z"
        )

        result = key.to_dict(include_utc=True)

        self.assertIn('start_utc', result)
        self.assertIn('end_utc', result)

    def test_to_json(self):
        """Test JSON string conversion."""
        key = GeneratedKey(
            door_id="test-door",
            passwd="test-pass",
            start="2025-01-01, 10:00:00",
            end="2025-01-01, 10:10:00"
        )

        result = key.to_json()
        parsed = json.loads(result)

        self.assertEqual(parsed['doorID'], "test-door")


class TestKeyGenerator(unittest.TestCase):
    """Test cases for KeyGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_generate_key_creates_password(self):
        """Test that generate_key auto-generates password."""
        config = KeyGeneratorConfig(door_id="test-door")
        generator = KeyGenerator(config)

        key = generator.generate_key()

        self.assertIsNotNone(key.passwd)
        self.assertTrue(len(key.passwd) > 0)

    def test_generate_key_preserves_custom_password(self):
        """Test that custom password is preserved."""
        config = KeyGeneratorConfig(
            door_id="test-door",
            passwd="custom-pass"
        )
        generator = KeyGenerator(config)

        key = generator.generate_key()

        self.assertEqual(key.passwd, "custom-pass")

    def test_generate_key_time_calculation(self):
        """Test time calculation for key validity."""
        config = KeyGeneratorConfig(
            door_id="test-door",
            expire_minutes=15
        )
        generator = KeyGenerator(config)

        key = generator.generate_key()

        start = datetime.strptime(key.start, DATETIME_FORMAT)
        end = datetime.strptime(key.end, DATETIME_FORMAT)

        diff = (end - start).total_seconds()
        self.assertAlmostEqual(diff, 15 * 60, delta=2)

    def test_create_qr_image(self):
        """Test QR code image creation."""
        config = KeyGeneratorConfig(door_id="test-door")
        generator = KeyGenerator(config)

        key = generator.generate_key()
        qr_path = generator.create_qr_image(key)

        self.assertTrue(os.path.exists(qr_path))
        self.assertTrue(qr_path.endswith('.png'))

    def test_generate_and_create_qr(self):
        """Test combined generation and QR creation."""
        config = KeyGeneratorConfig(door_id="test-door")
        generator = KeyGenerator(config)

        qr_path, key = generator.generate_and_create_qr()

        self.assertTrue(os.path.exists(qr_path))
        self.assertIsInstance(key, GeneratedKey)

    def test_audit_trail(self):
        """Test generated keys audit trail."""
        config = KeyGeneratorConfig(door_id="test-door")
        generator = KeyGenerator(config)

        generator.generate_key()
        generator.generate_key()
        generator.generate_key()

        keys = generator.get_generated_keys()
        self.assertEqual(len(keys), 3)


class TestDoorKeyBackwardCompatibility(unittest.TestCase):
    """Test cases for DoorKey backward compatibility."""

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
        key = DoorKey()

        self.assertEqual(key.door_id, 'default')
        self.assertIsNone(key.passwd)
        self.assertEqual(key.expire_time, 10)

    def test_doorkey_custom_values(self):
        """Test DoorKey initialization with custom values."""
        key = DoorKey(
            door_id='custom-door',
            passwd='custom-pass',
            expire_minutes=20
        )

        self.assertEqual(key.door_id, 'custom-door')
        self.assertEqual(key.passwd, 'custom-pass')
        self.assertEqual(key.expire_time, 20)

    def test_create_key_returns_tuple(self):
        """Test create_key returns tuple of path and JSON."""
        key = DoorKey(door_id='test-door')

        qr_path, qr_info = key.create_key()

        self.assertTrue(os.path.exists(qr_path))
        data = json.loads(qr_info)
        self.assertEqual(data['doorID'], 'test-door')


class TestKeyGeneratorSecurity(unittest.TestCase):
    """Test cases for KeyGenerator security improvements."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_create_qr_image_creates_missing_directory(self):
        """Test that create_qr_image creates missing output directory."""
        config = KeyGeneratorConfig(door_id="test-door")
        generator = KeyGenerator(config)

        key = generator.generate_key()
        nested_dir = os.path.join(self.test_dir, "nested", "output", "dir")

        qr_path = generator.create_qr_image(key, output_dir=nested_dir)

        self.assertTrue(os.path.exists(nested_dir))
        self.assertTrue(os.path.exists(qr_path))

    def test_create_qr_image_empty_output_dir_raises_error(self):
        """Test that empty output_dir raises ValueError."""
        config = KeyGeneratorConfig(door_id="test-door")
        generator = KeyGenerator(config)

        key = generator.generate_key()

        with self.assertRaises(ValueError) as context:
            generator.create_qr_image(key, output_dir="")

        self.assertIn("empty", str(context.exception).lower())

    def test_create_qr_image_invalid_path_raises_error(self):
        """Test that invalid path raises ValueError."""
        config = KeyGeneratorConfig(door_id="test-door")
        generator = KeyGenerator(config)

        key = generator.generate_key()

        # Use a path that cannot be created (null byte in path)
        with self.assertRaises(ValueError):
            generator.create_qr_image(key, output_dir="/nonexistent\x00path")


class TestEmailSender(unittest.TestCase):
    """Test cases for EmailSender class."""

    def test_config_validation_empty_sender_id(self):
        """Test config validation with empty sender_id."""
        config = EmailConfig(
            sender_id="",
            sender_password="password"
        )

        with self.assertRaises(ValueError):
            EmailSender(config)

    def test_config_validation_empty_password(self):
        """Test config validation with empty password."""
        config = EmailConfig(
            sender_id="user",
            sender_password=""
        )

        with self.assertRaises(ValueError):
            EmailSender(config)

    @patch('email_sender.smtplib.SMTP')
    def test_send_key_success(self, mock_smtp):
        """Test successful email sending."""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        config = EmailConfig(
            sender_id="test",
            sender_password="password"
        )
        sender = EmailSender(config)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            test_file = f.name
            f.write(b'test image data')

        try:
            result = sender.send_key(test_file, "recipient@example.com")

            self.assertTrue(result)
            mock_smtp.assert_called_once()
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.sendmail.assert_called_once()

        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_send_key_missing_file(self):
        """Test sending with missing key file."""
        config = EmailConfig(
            sender_id="test",
            sender_password="password"
        )
        sender = EmailSender(config)

        with self.assertRaises(EmailSendError):
            sender.send_key("nonexistent.png", "recipient@example.com")

    def test_send_key_path_traversal_prevention(self):
        """Test that path traversal attacks are blocked."""
        config = EmailConfig(
            sender_id="test",
            sender_password="password"
        )
        sender = EmailSender(config)

        # Create a file outside cwd to simulate path traversal attack
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png', dir='/tmp') as f:
            test_file = f.name
            f.write(b'test image data')

        try:
            # This should raise EmailSendError due to path traversal protection
            with self.assertRaises(EmailSendError) as context:
                sender.send_key(test_file, "recipient@example.com")

            self.assertIn("working directory", str(context.exception).lower())

        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    @patch('email_sender.smtplib.SMTP')
    def test_send_key_within_cwd_succeeds(self, mock_smtp):
        """Test that files within current working directory are allowed."""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        config = EmailConfig(
            sender_id="test",
            sender_password="password"
        )
        sender = EmailSender(config)

        # Create a file in current working directory
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png', dir=os.getcwd()) as f:
            test_file = f.name
            f.write(b'test image data')

        try:
            result = sender.send_key(test_file, "recipient@example.com")
            self.assertTrue(result)

        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    @patch('email_sender.smtplib.SMTP')
    def test_send_key_auth_failure(self, mock_smtp):
        """Test handling of authentication failure."""
        import smtplib

        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b'Authentication failed'
        )
        mock_smtp.return_value = mock_server

        config = EmailConfig(
            sender_id="test",
            sender_password="wrong"
        )
        sender = EmailSender(config)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            test_file = f.name
            f.write(b'test data')

        try:
            with self.assertRaises(EmailSendError) as context:
                sender.send_key(test_file, "recipient@example.com")

            self.assertIn("Authentication", str(context.exception))

        finally:
            if os.path.exists(test_file):
                os.remove(test_file)


class TestPubSubPublisher(unittest.TestCase):
    """Test cases for PubSubPublisher class."""

    @patch('publisher.pubsub_v1.PublisherClient')
    def test_publish_success(self, mock_client_class):
        """Test successful message publishing."""
        mock_client = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "message-id-123"
        mock_client.publish.return_value = mock_future
        mock_client_class.return_value = mock_client

        config = PubSubConfig(
            project_id="test-project",
            topic_name="test-topic"
        )
        publisher = PubSubPublisher(config)

        result = publisher.publish(b"test message")

        self.assertEqual(result, "message-id-123")

    @patch('publisher.pubsub_v1.PublisherClient')
    def test_publish_string(self, mock_client_class):
        """Test string message publishing."""
        mock_client = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "message-id-456"
        mock_client.publish.return_value = mock_future
        mock_client_class.return_value = mock_client

        config = PubSubConfig(
            project_id="test-project",
            topic_name="test-topic"
        )
        publisher = PubSubPublisher(config)

        result = publisher.publish_string("test string message")

        self.assertEqual(result, "message-id-456")

    @patch('publisher.pubsub_v1.PublisherClient')
    def test_publish_topic_not_found(self, mock_client_class):
        """Test handling of topic not found error."""
        from google.api_core import exceptions as gcp_exceptions

        mock_client = MagicMock()
        mock_future = MagicMock()
        mock_future.result.side_effect = gcp_exceptions.NotFound("Topic not found")
        mock_client.publish.return_value = mock_future
        mock_client_class.return_value = mock_client

        config = PubSubConfig(
            project_id="test-project",
            topic_name="nonexistent-topic"
        )
        publisher = PubSubPublisher(config)

        with self.assertRaises(PublishError) as context:
            publisher.publish(b"test message")

        self.assertIn("not found", str(context.exception).lower())

    @patch('publisher.pubsub_v1.PublisherClient')
    def test_message_tracking(self, mock_client_class):
        """Test published message tracking."""
        mock_client = MagicMock()
        mock_future = MagicMock()
        mock_future.result.side_effect = ["msg-1", "msg-2", "msg-3"]
        mock_client.publish.return_value = mock_future
        mock_client_class.return_value = mock_client

        config = PubSubConfig(
            project_id="test-project",
            topic_name="test-topic"
        )
        publisher = PubSubPublisher(config)

        publisher.publish(b"message 1")
        publisher.publish(b"message 2")
        publisher.publish(b"message 3")

        messages = publisher.get_published_messages()
        self.assertEqual(len(messages), 3)


def run_tests():
    """Run all unit tests."""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
