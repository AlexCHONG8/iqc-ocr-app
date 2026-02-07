#!/usr/bin/env python3
"""
Test for the bug: download_markdown with None URL
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from app import MinerUClient


class TestNoneURLBug(unittest.TestCase):
    """Test download_markdown with None URL."""

    @patch('app.requests.get')
    def test_download_markdown_with_none_url(self, mock_get):
        """Should handle None URL gracefully."""
        # None URL means requests.get won't be called
        # but the function should still return empty string
        client = MinerUClient(api_key="test-key")
        result = client.download_markdown(None)

        # This will fail because requests.get(None) raises an exception
        # which download_markdown catches and returns ""
        self.assertEqual(result, "")
        # requests.get should NOT have been called with None
        # (it would raise TypeError: request() got None for url)

    @patch('app.requests.get')
    def test_download_markdown_with_empty_url(self, mock_get):
        """Should handle empty URL gracefully."""
        client = MinerUClient(api_key="test-key")
        result = client.download_markdown("")

        # Empty string URL will fail but should return empty
        self.assertEqual(result, "")

    def test_wait_for_completion_returns_md_url(self):
        """wait_for_completion should include md_url in result."""
        with patch('app.requests.get') as mock_get:
            # Mock API response for task status
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 0,
                'data': {
                    'extract_result': [{
                        'state': 'done',
                        'full_md_link': 'https://cdn.example.com/result.md',
                    }]
                }
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            client = MinerUClient(api_key="test-key")
            result = client.wait_for_completion("test-batch")

            # Result should have md_url
            self.assertIn('md_url', result)
            self.assertIsNotNone(result['md_url'])


if __name__ == "__main__":
    unittest.main(verbosity=2)
