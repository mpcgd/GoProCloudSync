import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock keyring import for testing
sys.modules['keyring'] = MagicMock()
sys.modules['keyring.errors'] = MagicMock()

from src.cli import get_token, set_token, main

class TestCLI(unittest.TestCase):
    """Test cases for the CLI module"""

    def setUp(self):
        """Set up test fixtures"""
        # Save original environment variables
        self.original_env = os.environ.copy()

    def tearDown(self):
        """Clean up after tests"""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('os.environ.get')
    def test_get_token_from_env(self, mock_get):
        """Test getting token from environment variable"""
        mock_get.return_value = "env_token"
        token = get_token()
        self.assertEqual(token, "env_token")

    @patch('keyring.get_password')
    @patch('os.environ.get')
    def test_get_token_from_keyring(self, mock_env_get, mock_keyring_get):
        """Test getting token from keyring when env var is not set"""
        mock_env_get.return_value = None
        mock_keyring_get.return_value = "keyring_token"

        token = get_token()
        self.assertEqual(token, "keyring_token")

    @patch('keyring.get_password')
    @patch('os.environ.get')
    def test_get_token_none(self, mock_env_get, mock_keyring_get):
        """Test getting token when neither env nor keyring is available"""
        mock_env_get.return_value = None
        mock_keyring_get.return_value = None

        token = get_token()
        self.assertIsNone(token)

    @patch('keyring.set_password')
    def test_set_token_success(self, mock_set_password):
        """Test setting token to keyring"""
        mock_set_password.return_value = None

        result = set_token("test_token")
        mock_set_password.assert_called_once_with("gopro-cloud-sync", "auth_token", "test_token")

    @patch('keyring.set_password')
    def test_set_token_failure(self, mock_set_password):
        """Test setting token when keyring fails"""
        mock_set_password.side_effect = Exception("Keyring error")

        result = set_token("test_token")
        mock_set_password.assert_called_once()

    @patch('sys.argv')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_help(self, mock_parse_args, mock_argv):
        """Test CLI help output"""
        mock_argv = ['gopro-sync', '--help']
        mock_parse_args.side_effect = SystemExit(0)

        with self.assertRaises(SystemExit):
            main()

    @patch('sys.argv')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('src.cli.sync_account')
    def test_main_success(self, mock_sync_account, mock_parse_args, mock_argv):
        """Test successful CLI execution"""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.token = "test_token"
        mock_args.save_token = False
        mock_args.folder = "/test/folder"
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Mock sync_account to return True
        mock_sync_account.return_value = True

        # Mock argv
        mock_argv = ['gopro-sync', '--token', 'test_token', '--folder', '/test/folder']

        with patch('sys.argv', mock_argv):
            with patch('argparse.ArgumentParser.parse_args', return_value=mock_args):
                # Test that main doesn't raise exceptions
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)

    @patch('sys.argv')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('src.cli.sync_account')
    def test_main_failure(self, mock_sync_account, mock_parse_args, mock_argv):
        """Test failed CLI execution"""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.token = "test_token"
        mock_args.save_token = False
        mock_args.folder = "/test/folder"
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Mock sync_account to return False
        mock_sync_account.return_value = False

        # Mock argv
        mock_argv = ['gopro-sync', '--token', 'test_token', '--folder', '/test/folder']

        with patch('sys.argv', mock_argv):
            with patch('argparse.ArgumentParser.parse_args', return_value=mock_args):
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 1)

    @patch('sys.argv')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_no_token(self, mock_parse_args, mock_argv):
        """Test CLI execution with no token"""
        # Mock arguments with no token
        mock_args = MagicMock()
        mock_args.token = None
        mock_args.save_token = False
        mock_args.folder = "/test/folder"
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Mock argv
        mock_argv = ['gopro-sync', '--folder', '/test/folder']

        with patch('sys.argv', mock_argv):
            with patch('argparse.ArgumentParser.parse_args', return_value=mock_args):
                with patch('src.cli.get_token', return_value=None):
                    with self.assertRaises(SystemExit) as cm:
                        main()
                    self.assertEqual(cm.exception.code, 1)

    @patch('sys.argv')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('src.cli.set_token')
    @patch('src.cli.sync_account')
    def test_main_save_token(self, mock_sync_account, mock_set_token, mock_parse_args, mock_argv):
        """Test CLI execution with save-token option"""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.token = "test_token"
        mock_args.save_token = True
        mock_args.folder = "/test/folder"
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Mock sync_account to return True
        mock_sync_account.return_value = True

        # Mock argv
        mock_argv = ['gopro-sync', '--token', 'test_token', '--save-token', '--folder', '/test/folder']

        with patch('sys.argv', mock_argv):
            with patch('argparse.ArgumentParser.parse_args', return_value=mock_args):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)

                # Verify set_token was called
                mock_set_token.assert_called_once_with("test_token")

if __name__ == '__main__':
    unittest.main()
