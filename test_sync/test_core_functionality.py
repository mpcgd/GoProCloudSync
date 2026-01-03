import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
from src.gopro_client import GoProPlus
from src.sync import sync_account

class TestCoreFunctionality(unittest.TestCase):
    """Test cases for core functionality that work reliably"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_token = "test_token_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        self.client = GoProPlus(self.test_token)

    def test_client_initialization(self):
        """Test that the client initializes correctly"""
        self.assertEqual(self.client.auth_token, self.test_token)
        self.assertEqual(self.client.base, "api.gopro.com")
        self.assertEqual(self.client.host, "https://api.gopro.com")
        self.assertIsNone(self.client.user_id)

    def test_headers_generation(self):
        """Test that headers are generated correctly"""
        headers = self.client._headers()
        self.assertEqual(headers["Accept"], "application/vnd.gopro.jk.media+json; version=2.0.0")
        self.assertEqual(headers["Authorization"], f"Bearer {self.test_token}")
        self.assertIn("User-Agent", headers)

    @patch('requests.get')
    def test_token_validation_success(self, mock_get):
        """Test successful token validation"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test_user_id"}
        mock_get.return_value = mock_response

        result = self.client.validate()
        self.assertTrue(result)
        self.assertEqual(self.client.user_id, "test_user_id")

    @patch('requests.get')
    def test_token_validation_failure(self, mock_get):
        """Test failed token validation"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = self.client.validate()
        self.assertFalse(result)

    @patch('requests.get')
    def test_media_list_retrieval(self, mock_get):
        """Test getting media list from API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "_embedded": {
                "media": [
                    {"id": "media1", "filename": "test1.mp4", "file_size": 1000, "file_extension": "mp4"},
                    {"id": "media2", "filename": "test2.mp4", "file_size": 2000, "file_extension": "mp4"}
                ]
            },
            "_pages": {"total_pages": 1}
        }
        mock_get.return_value = mock_response

        media_list = self.client.get_media_list(pages=1)
        self.assertEqual(len(media_list), 2)
        self.assertEqual(media_list[0]["id"], "media1")
        self.assertEqual(media_list[1]["filename"], "test2.mp4")

    def test_download_url_selection(self):
        """Test getting download URL from media variations"""
        # Test with source variation
        media_item = {
            "variations": [
                {"type": "source", "url": "https://source.url"},
                {"type": "high", "url": "https://high.url"}
            ]
        }
        url = self.client.get_download_url(media_item)
        self.assertEqual(url, "https://source.url")

        # Test with no source variation
        media_item_no_source = {"variations": [{"type": "high", "url": "https://high.url"}]}
        url = self.client.get_download_url(media_item_no_source)
        self.assertIsNone(url)

    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_file_skipping_logic(self, mock_getsize, mock_exists):
        """Test that existing files are skipped when size matches"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1000

        media_item = {
            "id": "test_media",
            "filename": "test.mp4",
            "file_size": 1000,
            "file_extension": "mp4"
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = os.path.join(temp_dir, "test.mp4")
            with open(target_path, 'w') as f:
                f.write("test content")

            result = self.client.download_media_item(media_item, temp_dir)
            self.assertEqual(result, "skipped")

    def test_360_file_handling(self):
        """Test .360 file handling with actual zip operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test zip file
            test_zip_path = os.path.join(temp_dir, "test.360.zip")
            test_360_path = os.path.join(temp_dir, "test.360")

            # Create a simple zip file with a test media file
            import zipfile
            with zipfile.ZipFile(test_zip_path, 'w') as z:
                z.writestr("test_media.mp4", "test content")

            # Rename to .360
            os.rename(test_zip_path, test_360_path)

            # Test the handling
            result = self.client._handle_360_file(test_360_path)

            # Verify results
            self.assertTrue(result)
            expected_extracted_path = os.path.join(temp_dir, "test.mp4")
            self.assertTrue(os.path.exists(expected_extracted_path))
            self.assertFalse(os.path.exists(test_360_path))

    def test_sync_process_success(self):
        """Test successful sync process with mocked client"""
        test_folder = tempfile.mkdtemp()

        try:
            with patch('src.sync.GoProPlus') as mock_client_class:
                mock_client = MagicMock()
                mock_client.validate.return_value = True
                mock_client.get_media_list.return_value = [
                    {"id": "media1", "filename": "test1.mp4", "file_size": 1000, "file_extension": "mp4"}
                ]
                mock_client.download_media_item.return_value = "downloaded"
                mock_client_class.return_value = mock_client

                callback_messages = []
                def test_callback(message, progress):
                    callback_messages.append((message, progress))

                result = sync_account(self.test_token, test_folder, callback=test_callback)
                self.assertTrue(result)
                self.assertEqual(callback_messages[-1][0], "Sync complete.")
                self.assertEqual(callback_messages[-1][1], 100)

        finally:
            if os.path.exists(test_folder):
                for file in os.listdir(test_folder):
                    os.remove(os.path.join(test_folder, file))
                os.rmdir(test_folder)

    def test_sync_process_invalid_token(self):
        """Test sync process with invalid token"""
        test_folder = tempfile.mkdtemp()

        try:
            with patch('src.sync.GoProPlus') as mock_client_class:
                mock_client = MagicMock()
                mock_client.validate.return_value = False
                mock_client_class.return_value = mock_client

                callback_messages = []
                def test_callback(message, progress):
                    callback_messages.append((message, progress))

                result = sync_account(self.test_token, test_folder, callback=test_callback)
                self.assertFalse(result)
                self.assertGreaterEqual(len(callback_messages), 1)

        finally:
            if os.path.exists(test_folder):
                os.rmdir(test_folder)

    def test_sync_folder_creation(self):
        """Test that sync creates target folder if it doesn't exist"""
        test_folder = os.path.join(tempfile.gettempdir(), "test_sync_folder_that_does_not_exist")

        try:
            with patch('src.sync.GoProPlus') as mock_client_class:
                mock_client = MagicMock()
                mock_client.validate.return_value = True
                mock_client.get_media_list.return_value = []
                mock_client_class.return_value = mock_client

                self.assertFalse(os.path.exists(test_folder))
                result = sync_account(self.test_token, test_folder)
                self.assertTrue(result)
                self.assertTrue(os.path.exists(test_folder))

        finally:
            if os.path.exists(test_folder):
                os.rmdir(test_folder)

if __name__ == '__main__':
    unittest.main()
