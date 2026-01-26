"""
Enhanced Unit Tests for Raspberry Pi Part
라즈베리파이 파트 향상된 단위 테스트

Tests for refactored QR scanner, door controller, and subscriber.
리팩토링된 QR 스캐너, 도어 컨트롤러 및 구독자에 대한 테스트입니다.
"""

import unittest
import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock hardware modules before importing our modules
# 모듈 임포트 전에 하드웨어 모듈 모킹
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['pyzbar'] = MagicMock()
sys.modules['pyzbar.pyzbar'] = MagicMock()

from constants import DoorConfig, validate_config, DEFAULT_GPIO_PIN
from door_controller import GPIODoorController, MockDoorController


class TestConstants(unittest.TestCase):
    """Test cases for constants module."""

    def test_door_config_defaults(self):
        """Test DoorConfig default values."""
        config = DoorConfig(door_id="test-door")

        self.assertEqual(config.door_id, "test-door")
        self.assertEqual(config.gpio_pin, DEFAULT_GPIO_PIN)
        self.assertEqual(config.unlock_duration, 5)
        self.assertEqual(config.rate_limit_minutes, 1)

    def test_door_config_custom_values(self):
        """Test DoorConfig with custom values."""
        config = DoorConfig(
            door_id="custom-door",
            gpio_pin=18,
            unlock_duration=10,
            rate_limit_minutes=2
        )

        self.assertEqual(config.door_id, "custom-door")
        self.assertEqual(config.gpio_pin, 18)
        self.assertEqual(config.unlock_duration, 10)
        self.assertEqual(config.rate_limit_minutes, 2)

    def test_validate_config_valid(self):
        """Test config validation with valid config."""
        config = DoorConfig(door_id="test-door")
        self.assertTrue(validate_config(config))

    def test_validate_config_empty_door_id(self):
        """Test config validation with empty door_id."""
        config = DoorConfig(door_id="")
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_validate_config_invalid_gpio_pin(self):
        """Test config validation with invalid GPIO pin."""
        config = DoorConfig(door_id="test", gpio_pin=100)
        with self.assertRaises(ValueError):
            validate_config(config)


class TestMockDoorController(unittest.TestCase):
    """Test cases for MockDoorController."""

    def test_initial_state(self):
        """Test initial state is locked."""
        controller = MockDoorController()
        self.assertTrue(controller.is_locked)
        self.assertEqual(controller.unlock_count, 0)

    def test_unlock(self):
        """Test unlock operation."""
        controller = MockDoorController()

        result = controller.unlock()

        self.assertTrue(result)
        self.assertFalse(controller.is_locked)
        self.assertEqual(controller.unlock_count, 1)

    def test_lock(self):
        """Test lock operation."""
        controller = MockDoorController()
        controller.unlock()

        result = controller.lock()

        self.assertTrue(result)
        self.assertTrue(controller.is_locked)

    def test_multiple_unlocks(self):
        """Test multiple unlock operations."""
        controller = MockDoorController()

        for i in range(5):
            controller.unlock()

        self.assertEqual(controller.unlock_count, 5)

    def test_cleanup(self):
        """Test cleanup operation."""
        controller = MockDoorController()
        # Should not raise any exceptions
        controller.cleanup()


class TestGPIODoorController(unittest.TestCase):
    """Test cases for GPIODoorController."""

    @patch('door_controller.GPIO_AVAILABLE', True)
    @patch('door_controller.GPIO')
    def test_initialization(self, mock_gpio):
        """Test GPIO controller initialization."""
        controller = GPIODoorController(gpio_pin=17)

        mock_gpio.setmode.assert_called_once()
        mock_gpio.setup.assert_called_once_with(17, mock_gpio.OUT)

    def test_cleanup_race_condition_protection(self):
        """Test that double cleanup is prevented (race condition protection)."""
        with patch('door_controller.GPIO_AVAILABLE', False):
            controller = GPIODoorController(gpio_pin=17)

            # First cleanup should work
            controller.cleanup()
            self.assertTrue(controller._cleanup_done)

            # Second cleanup should be skipped (no error, but no action)
            controller.cleanup()
            self.assertTrue(controller._cleanup_done)

    @patch('door_controller.GPIO_AVAILABLE', True)
    @patch('door_controller.GPIO')
    def test_cleanup_only_runs_once_with_gpio(self, mock_gpio):
        """Test that GPIO cleanup only runs once even if called multiple times."""
        controller = GPIODoorController(gpio_pin=17)

        # First cleanup
        controller.cleanup()
        first_cleanup_call_count = mock_gpio.cleanup.call_count

        # Second cleanup should not call GPIO.cleanup again
        controller.cleanup()
        second_cleanup_call_count = mock_gpio.cleanup.call_count

        self.assertEqual(first_cleanup_call_count, second_cleanup_call_count)

    @patch('door_controller.GPIO_AVAILABLE', False)
    def test_simulation_mode(self):
        """Test controller runs in simulation mode without GPIO."""
        controller = GPIODoorController(gpio_pin=17)

        # Should not raise exception
        result = controller.unlock()
        self.assertTrue(result)

    def test_can_unlock_first_time(self):
        """Test can_unlock returns True for first unlock."""
        with patch('door_controller.GPIO_AVAILABLE', False):
            controller = GPIODoorController()
            self.assertTrue(controller.can_unlock())

    def test_rate_limiting(self):
        """Test rate limiting blocks rapid unlocks."""
        with patch('door_controller.GPIO_AVAILABLE', False):
            with patch('door_controller.time.sleep'):
                controller = GPIODoorController(rate_limit_minutes=1)

                # First unlock should succeed
                self.assertTrue(controller.unlock())

                # Second unlock should be blocked
                self.assertFalse(controller.can_unlock())


class TestQRScanner(unittest.TestCase):
    """Test cases for QRScanner class."""

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

    def _create_test_key(self, minutes_valid: int = 5) -> dict:
        """Create a test key dictionary."""
        now = datetime.now()
        start = now - timedelta(minutes=1)
        end = now + timedelta(minutes=minutes_valid)

        return {
            'doorID': 'test-door',
            'passwd': 'test-password',
            'start': start.strftime("%Y-%m-%d, %H:%M:%S"),
            'end': end.strftime("%Y-%m-%d, %H:%M:%S")
        }

    def test_load_key_success(self):
        """Test successful key loading."""
        from qr_scanner import QRScanner

        test_key = self._create_test_key()
        with open(self.test_key_file, 'w') as f:
            json.dump(test_key, f)

        config = DoorConfig(door_id="test", key_file=self.test_key_file)
        scanner = QRScanner(config, door_controller=MockDoorController())

        result = scanner.load_key()

        self.assertTrue(result)
        self.assertEqual(scanner._current_key['doorID'], 'test-door')

    def test_load_key_missing_file(self):
        """Test key loading with missing file."""
        from qr_scanner import QRScanner

        config = DoorConfig(door_id="test", key_file="nonexistent.json")
        scanner = QRScanner(config, door_controller=MockDoorController())

        result = scanner.load_key()

        self.assertFalse(result)

    def test_is_key_valid_within_window(self):
        """Test key validity check within time window."""
        from qr_scanner import QRScanner

        test_key = self._create_test_key(minutes_valid=10)
        with open(self.test_key_file, 'w') as f:
            json.dump(test_key, f)

        config = DoorConfig(door_id="test", key_file=self.test_key_file)
        scanner = QRScanner(config, door_controller=MockDoorController())
        scanner.load_key()

        self.assertTrue(scanner.is_key_valid())

    def test_is_key_valid_expired(self):
        """Test key validity check for expired key."""
        from qr_scanner import QRScanner

        # Create an expired key
        now = datetime.now()
        test_key = {
            'doorID': 'test-door',
            'passwd': 'test-password',
            'start': (now - timedelta(hours=2)).strftime("%Y-%m-%d, %H:%M:%S"),
            'end': (now - timedelta(hours=1)).strftime("%Y-%m-%d, %H:%M:%S")
        }
        with open(self.test_key_file, 'w') as f:
            json.dump(test_key, f)

        config = DoorConfig(door_id="test", key_file=self.test_key_file)
        scanner = QRScanner(config, door_controller=MockDoorController())
        scanner.load_key()

        self.assertFalse(scanner.is_key_valid())

    def test_validate_qr_data_success(self):
        """Test QR data validation with matching data."""
        from qr_scanner import QRScanner

        test_key = self._create_test_key()
        with open(self.test_key_file, 'w') as f:
            json.dump(test_key, f)

        config = DoorConfig(door_id="test", key_file=self.test_key_file)
        scanner = QRScanner(config, door_controller=MockDoorController())
        scanner.load_key()

        qr_data = json.dumps(test_key)
        result = scanner.validate_qr_data(qr_data)

        self.assertTrue(result.success)

    def test_validate_qr_data_mismatch(self):
        """Test QR data validation with mismatched password."""
        from qr_scanner import QRScanner

        test_key = self._create_test_key()
        with open(self.test_key_file, 'w') as f:
            json.dump(test_key, f)

        config = DoorConfig(door_id="test", key_file=self.test_key_file)
        scanner = QRScanner(config, door_controller=MockDoorController())
        scanner.load_key()

        wrong_key = test_key.copy()
        wrong_key['passwd'] = 'wrong-password'
        qr_data = json.dumps(wrong_key)

        result = scanner.validate_qr_data(qr_data)

        self.assertFalse(result.success)
        self.assertIn("mismatch", result.error.lower())

    def test_validate_qr_data_invalid_json(self):
        """Test QR data validation with invalid JSON."""
        from qr_scanner import QRScanner

        test_key = self._create_test_key()
        with open(self.test_key_file, 'w') as f:
            json.dump(test_key, f)

        config = DoorConfig(door_id="test", key_file=self.test_key_file)
        scanner = QRScanner(config, door_controller=MockDoorController())
        scanner.load_key()

        result = scanner.validate_qr_data("not valid json")

        self.assertFalse(result.success)
        self.assertIn("invalid", result.error.lower())

    def test_access_attempt_recording(self):
        """Test access attempt audit trail."""
        from qr_scanner import QRScanner

        test_key = self._create_test_key()
        with open(self.test_key_file, 'w') as f:
            json.dump(test_key, f)

        config = DoorConfig(door_id="test", key_file=self.test_key_file)
        scanner = QRScanner(config, door_controller=MockDoorController())
        scanner.load_key()

        scanner._record_access_attempt(
            success=True,
            reason="Test access",
            key_id="test-key-id"
        )

        log = scanner.get_access_log()
        self.assertEqual(len(log), 1)
        self.assertTrue(log[0].success)
        self.assertEqual(log[0].reason, "Test access")

    def test_has_key_changed_detection(self):
        """Test detection of key password changes."""
        from qr_scanner import QRScanner

        test_key = self._create_test_key()
        with open(self.test_key_file, 'w') as f:
            json.dump(test_key, f)

        config = DoorConfig(door_id="test", key_file=self.test_key_file)
        scanner = QRScanner(config, door_controller=MockDoorController())
        scanner.load_key()

        # Initially should not detect change
        self.assertFalse(scanner.has_key_changed())

        # Update key file with new password
        test_key['passwd'] = 'new-password'
        with open(self.test_key_file, 'w') as f:
            json.dump(test_key, f)

        # Should now detect change
        self.assertTrue(scanner.has_key_changed())


class TestSubscriber(unittest.TestCase):
    """Test cases for DoorLensSubscriber."""

    def test_save_key_valid_json(self):
        """Test saving valid JSON key data."""
        from subscriber import DoorLensSubscriber, SubscriberConfig

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            key_file = f.name

        try:
            config = SubscriberConfig(
                project_id="test-project",
                subscription_name="test-sub",
                key_file=key_file
            )
            subscriber = DoorLensSubscriber(config)

            key_data = json.dumps({'doorID': 'test', 'passwd': 'test'})
            result = subscriber._save_key(key_data)

            self.assertTrue(result)

            with open(key_file, 'r') as f:
                saved_data = json.load(f)

            self.assertEqual(saved_data['doorID'], 'test')

        finally:
            if os.path.exists(key_file):
                os.remove(key_file)

    def test_save_key_invalid_json(self):
        """Test saving invalid JSON data."""
        from subscriber import DoorLensSubscriber, SubscriberConfig

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            key_file = f.name

        try:
            config = SubscriberConfig(
                project_id="test-project",
                subscription_name="test-sub",
                key_file=key_file
            )
            subscriber = DoorLensSubscriber(config)

            result = subscriber._save_key("not valid json")

            self.assertFalse(result)

        finally:
            if os.path.exists(key_file):
                os.remove(key_file)

    def test_save_key_sets_restrictive_permissions(self):
        """Test that saved key file has restrictive permissions (0o600)."""
        from subscriber import DoorLensSubscriber, SubscriberConfig
        import stat

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            key_file = f.name

        try:
            config = SubscriberConfig(
                project_id="test-project",
                subscription_name="test-sub",
                key_file=key_file
            )
            subscriber = DoorLensSubscriber(config)

            key_data = json.dumps({'doorID': 'test', 'passwd': 'test'})
            subscriber._save_key(key_data)

            # Check file permissions
            file_stat = os.stat(key_file)
            mode = stat.S_IMODE(file_stat.st_mode)

            # Should be 0o600 (owner read/write only)
            self.assertEqual(mode, 0o600)

        finally:
            if os.path.exists(key_file):
                os.remove(key_file)


class TestSubscriberProcessMonitoring(unittest.TestCase):
    """Test cases for subscriber process monitoring feature."""

    def test_monitor_scanner_config_option(self):
        """Test that monitor_scanner config option is available."""
        from subscriber import SubscriberConfig

        config = SubscriberConfig(
            project_id="test-project",
            subscription_name="test-sub",
            monitor_scanner=False
        )

        self.assertFalse(config.monitor_scanner)

        config_enabled = SubscriberConfig(
            project_id="test-project",
            subscription_name="test-sub",
            monitor_scanner=True
        )

        self.assertTrue(config_enabled.monitor_scanner)

    def test_stop_process_monitor_safe_when_no_thread(self):
        """Test that stopping monitor is safe when no thread exists."""
        from subscriber import DoorLensSubscriber, SubscriberConfig

        config = SubscriberConfig(
            project_id="test-project",
            subscription_name="test-sub",
            monitor_scanner=False
        )
        subscriber = DoorLensSubscriber(config)

        # Should not raise any exceptions
        subscriber._stop_process_monitor()

    @patch('subscriber.threading.Thread')
    def test_start_process_monitor_creates_thread(self, mock_thread_class):
        """Test that process monitor creates a daemon thread."""
        from subscriber import DoorLensSubscriber, SubscriberConfig

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        config = SubscriberConfig(
            project_id="test-project",
            subscription_name="test-sub",
            monitor_scanner=True
        )
        subscriber = DoorLensSubscriber(config)

        subscriber._start_process_monitor()

        mock_thread_class.assert_called_once()
        call_kwargs = mock_thread_class.call_args[1]
        self.assertTrue(call_kwargs['daemon'])
        self.assertEqual(call_kwargs['name'], 'ScannerProcessMonitor')
        mock_thread.start.assert_called_once()

    def test_monitor_disabled_does_not_start_thread(self):
        """Test that monitor thread is not started when disabled."""
        from subscriber import DoorLensSubscriber, SubscriberConfig

        config = SubscriberConfig(
            project_id="test-project",
            subscription_name="test-sub",
            monitor_scanner=False
        )
        subscriber = DoorLensSubscriber(config)

        subscriber._start_process_monitor()

        self.assertIsNone(subscriber._monitor_thread)


def run_tests():
    """Run all unit tests."""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
