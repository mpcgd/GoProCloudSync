import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
from src.sync import sync_account

class TestSync(unittest.TestCase):
    """Test cases for the sync module"""

    def test_sync_account_success(self):
        """Test successful sync account with mocked client"""
        test_token = "test_token"
        test_folder = tempfile.mkdtemp()

        try:
            # Mock the GoProPlus client
            with patch('src.sync.GoProPlus') as mock_client_class:
                mock_client = MagicMock()
                mock_client.validate.return_value = True
                mock_client.get_media_list.return_value = [
                    {
                        "id": "media1",
                        "filename": "test1.mp4",
                        "file_size": 1000,
                        "file_extension": "mp4"
                    }
                ]
                mock_client.download_media_item.return_value = "downloaded"
                mock_client_class.return_value = mock_client

                # Test sync with callback
                callback_messages = []
                def test_callback(message, progress):
                    callback_messages.append((message, progress))

                result = sync_account(test_token, test_folder, callback=test_callback)
                self.assertTrue(result)

                # Verify callback was called
                self.assertGreater(len(callback_messages), 0)
                self.assertEqual(callback_messages[-1][0], "Sync complete.")
                self.assertEqual(callback_messages[-1][1], 100)

                # Verify client methods were called
                mock_client.validate.assert_called_once()
                mock_client.get_media_list.assert_called_once()
                mock_client.download_media_item.assert_called_once()

        finally:
            # Clean up
            if os.path.exists(test_folder):
                for file in os.listdir(test_folder):
                    os.remove(os.path.join(test_folder, file))
                os.rmdir(test_folder)

    def test_sync_account_invalid_token(self):
        """Test sync account with invalid token"""
        test_token = "invalid_token"
        test_folder = tempfile.mkdtemp()

        try:
            # Mock the GoProPlus client with validation failure
            with patch('src.sync.GoProPlus') as mock_client_class:
                mock_client = MagicMock()
                mock_client.validate.return_value = False
                mock_client_class.return_value = mock_client

                # Test sync with callback
                callback_messages = []
                def test_callback(message, progress):
                    callback_messages.append((message, progress))

                result = sync_account(test_token, test_folder, callback=test_callback)
                self.assertFalse(result)

                # Verify error callback was called (may have multiple messages due to logging)
                self.assertGreaterEqual(len(callback_messages), 1)
                # Check that "Invalid token" message is in the callback messages
                invalid_token_messages = [msg for msg, _ in callback_messages if "Invalid token" in msg]
                self.assertGreaterEqual(len(invalid_token_messages), 1)

        finally:
            # Clean up
            if os.path.exists(test_folder):
                os.rmdir(test_folder)

    def test_sync_account_cancelled(self):
        """Test sync account with cancellation - simplified to test the cancellation mechanism"""
        test_token = "test_token"
        test_folder = tempfile.mkdtemp()

        try:
            # Mock the GoProPlus client
            with patch('src.sync.GoProPlus') as mock_client_class:
                mock_client = MagicMock()
                mock_client.validate.return_value = True
                mock_client.get_media_list.return_value = [
                    {
                        "id": "media1",
                        "filename": "test1.mp4",
                        "file_size": 1000,
                        "file_extension": "mp4"
                    }
                ]
                mock_client_class.return_value = mock_client

                # Test sync with immediate cancellation
                callback_messages = []
                def test_callback(message, progress):
                    callback_messages.append((message, progress))

                # Always return True for cancellation
                def is_cancelled():
                    return True

                result = sync_account(test_token, test_folder,
                                     callback=test_callback,
                                     is_cancelled=is_cancelled)

                # Verify sync was cancelled
                self.assertFalse(result)
                self.assertGreater(len(callback_messages), 0)
                # Check that cancellation was detected
                cancelled_messages = [msg for msg, _ in callback_messages if "cancelled" in msg.lower()]
                self.assertGreater(len(cancelled_messages), 0)

        finally:
            # Clean up
            if os.path.exists(test_folder):
                os.rmdir(test_folder)

    def test_sync_account_folder_creation(self):
        """Test that sync account creates target folder if it doesn't exist"""
        test_token = "test_token"
        test_folder = os.path.join(tempfile.gettempdir(), "test_sync_folder_that_does_not_exist")

        try:
            # Mock the GoProPlus client
            with patch('src.sync.GoProPlus') as mock_client_class:
                mock_client = MagicMock()
                mock_client.validate.return_value = True
                mock_client.get_media_list.return_value = []
                mock_client_class.return_value = mock_client

                # Verify folder doesn't exist
                self.assertFalse(os.path.exists(test_folder))

                # Run sync
                result = sync_account(test_token, test_folder)
                self.assertTrue(result)

                # Verify folder was created
                self.assertTrue(os.path.exists(test_folder))

        finally:
            # Clean up
            if os.path.exists(test_folder):
                os.rmdir(test_folder)

if __name__ == '__main__':
    unittest.main()
