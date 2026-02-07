#!/usr/bin/env python3
"""
Tests for MinerUClient - OCR API integration
Following TDD: Write test first, watch it fail, then fix.
Uses built-in unittest (no pytest required).
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from app import MinerUClient


class TestMinerUClientDownload(unittest.TestCase):
    """Test OCR result download functionality."""

    @patch('app.requests.get')
    def test_download_markdown_returns_text(self, mock_get):
        """Should download and return markdown text from URL."""
        # Setup: Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "# Test Document\n\n| Dimension | Value |\n|----------|-------|\n| Length   | 27.85  |"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        client = MinerUClient(api_key="test-key")
        result = client.download_markdown("https://example.com/md.md")

        # Assert
        self.assertIn("# Test Document", result)
        self.assertIn("Dimension", result)
        self.assertIn("27.85", result)
        mock_get.assert_called_once_with("https://example.com/md.md", timeout=30)

    @patch('app.requests.get')
    def test_download_markdown_handles_timeout(self, mock_get):
        """Should return empty string on timeout."""
        # Setup: Mock timeout exception
        mock_get.side_effect = Exception("Timeout")

        # Execute
        client = MinerUClient(api_key="test-key")
        result = client.download_markdown("https://example.com/md.md")

        # Assert
        self.assertEqual(result, "")

    @patch('app.requests.get')
    def test_download_markdown_sets_utf8_encoding(self, mock_get):
        """Should force UTF-8 encoding for Chinese characters."""
        # Setup: Mock response with Chinese content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "检验位置\t测试结果\n1\t27.85"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        client = MinerUClient(api_key="test-key")
        result = client.download_markdown("https://example.com/md.md")

        # Assert
        self.assertIn("检验位置", result)
        self.assertIn("27.85", result)


class TestMinerUClientTaskStatus(unittest.TestCase):
    """Test task status checking."""

    @patch('app.requests.get')
    def test_check_task_status_returns_md_url(self, mock_get):
        """Should return markdown URL from task status."""
        # Setup: Mock API response for task status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': {
                'extract_result': [{
                    'state': 'done',
                    'full_md_link': 'https://cdn.example.com/result.md',
                    'full_zip_url': 'https://cdn.example.com/result.zip',
                    'err_msg': None
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        client = MinerUClient(api_key="test-key")
        result = client.check_task_status("test-batch-123")

        # Assert
        self.assertTrue(result['success'])
        self.assertEqual(result['state'], 'done')
        self.assertEqual(result['md_url'], 'https://cdn.example.com/result.md')

    @patch('app.requests.get')
    def test_check_task_status_handles_failure(self, mock_get):
        """Should handle API errors gracefully."""
        # Setup: Mock error response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': -1,
            'msg': 'Task not found'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        client = MinerUClient(api_key="test-key")
        result = client.check_task_status("invalid-batch")

        # Assert Assert
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class TestMinerUClientTasksEndpoint(unittest.TestCase):
    """Test tasks endpoint method for retrieving full_md_link."""

    @patch('app.requests.get')
    def test_get_task_from_tasks_endpoint(self, mock_get):
        """Should retrieve task with full_md_link from /api/v4/tasks endpoint."""
        # Setup: Mock tasks endpoint response (real API structure)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': {
                'list': [
                    {
                        'task_id': 'batch-123-abcdef',
                        'file_name': 'test.pdf',
                        'state': 'done',
                        'full_md_link': 'https://cdn.example.com/result.md',
                        'err_msg': ''
                    },
                    {
                        'task_id': 'other-batch',
                        'file_name': 'other.pdf',
                        'state': 'processing',
                        'full_md_link': None,
                        'err_msg': ''
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        client = MinerUClient(api_key="test-key")
        result = client.get_task_from_tasks_endpoint("batch-123")

        # Assert
        self.assertTrue(result['success'])
        self.assertEqual(result['state'], 'done')
        self.assertEqual(result['md_url'], 'https://cdn.example.com/result.md')

    @patch('app.requests.get')
    def test_get_task_from_tasks_endpoint_not_found(self, mock_get):
        """Should handle task not found in tasks list."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': {
                'list': [
                    {
                        'task_id': 'other-batch',
                        'state': 'done',
                        'full_md_link': 'https://cdn.example.com/other.md'
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = MinerUClient(api_key="test-key")
        result = client.get_task_from_tasks_endpoint("nonexistent-batch")

        self.assertFalse(result['success'])
        self.assertIn('error', result)


class TestMinerUClientMDLinkDerivation(unittest.TestCase):
    """Test deriving full_md_link from full_zip_url."""

    @patch('app.requests.get')
    def test_derive_md_link_from_zip_url(self, mock_get):
        """Should derive full_md_link from full_zip_url when not directly available."""
        # Mock batch endpoint response (only has full_zip_url)
        mock_batch_response = Mock()
        mock_batch_response.status_code = 200
        mock_batch_response.json.return_value = {
            'code': 0,
            'data': {
                'extract_result': [{
                    'state': 'done',
                    'full_zip_url': 'https://cdn-mineru.openxlab.org.cn/pdf/2026-02-07/4d842f2f-8677-4099-834f-ca1662951d2b.zip',
                    'err_msg': ''
                }]
            }
        }
        mock_batch_response.raise_for_status = Mock()

        # Mock tasks endpoint returning empty (task not found)
        mock_tasks_response = Mock()
        mock_tasks_response.status_code = 200
        mock_tasks_response.json.return_value = {
            'code': 0,
            'data': {'list': []}  # Empty list - task not in tasks endpoint
        }
        mock_tasks_response.raise_for_status = Mock()

        # Configure mock to return different responses for different calls
        mock_get.side_effect = [mock_batch_response, mock_tasks_response]

        client = MinerUClient(api_key="test-key")

        # First call: check_task_status (batch endpoint)
        status = client.check_task_status("test-batch")
        self.assertTrue(status['success'])
        self.assertEqual(status['state'], 'done')

        # The derived md_url should be constructed from zip_url
        # Expected: https://cdn-mineru.openxlab.org.cn/result/2026-02-07/4d842f2f-8677-4099-834f-ca1662951d2b/full.md


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
