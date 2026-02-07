#!/usr/bin/env python3
"""Test split-table format (REAL IQC format)."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import unittest
from app import parse_html_tables_for_dimensions

class TestSplitTableFormat(unittest.TestCase):
    """Test the actual split-table format from real IQC reports."""

    def test_split_table_with_3_dimensions(self):
        """Test specs and data in separate tables (REAL format)."""

        # This is the ACTUAL format from MinerU OCR
        markdown = """
        | 检验位置 | 1 | 11 | 13 |
        |----------|---|----|----|
        | **检验标准** | 27.80+0.10-0.00 | Φ6.00±0.10 | 73.20+0.00-0.15 |

        | 结果序号 | 测试结果(1) | 判定 | 测试结果(11) | 判定 | 测试结果(13) | 判定 |
        |----------|-------------|------|--------------|------|--------------|------|
        | 1 | 27.85 | OK | 6.02 | OK | 73.14 | OK |
        | 2 | 27.84 | OK | 6.02 | OK | 73.12 | OK |
        | 3 | 27.81 | OK | 6.01 | OK | 73.15 | OK |
        | 4 | 27.82 | OK | 6.01 | OK | 73.12 | OK |
        | 5 | 27.85 | OK | 6.06 | OK | 73.10 | OK |
        """

        dimensions = parse_html_tables_for_dimensions(markdown)

        # Verify
        self.assertEqual(len(dimensions), 3,
                        f"Expected 3 dimensions from split tables, got {len(dimensions)}")

        # Verify first dimension
        self.assertEqual(dimensions[0]['position'], '1')
        self.assertEqual(dimensions[0]['spec'], '27.80+0.10-0.00')
        self.assertEqual(len(dimensions[0]['measurements']), 5)
        self.assertAlmostEqual(dimensions[0]['measurements'][0], 27.85, places=2)

        # Verify second dimension
        self.assertEqual(dimensions[1]['position'], '11')
        self.assertEqual(len(dimensions[1]['measurements']), 5)
        self.assertAlmostEqual(dimensions[1]['measurements'][0], 6.02, places=2)

        # Verify third dimension
        self.assertEqual(dimensions[2]['position'], '13')
        self.assertEqual(len(dimensions[2]['measurements']), 5)
        self.assertAlmostEqual(dimensions[2]['measurements'][0], 73.14, places=2)

        print("✅ Split-table format test PASSED!")

    def test_real_file_format(self):
        """Test with the actual structure from output/20260122_111541.md"""

        # More realistic format with HTML tables (MinerU sometimes outputs HTML)
        markdown = """
        <table>
        <tr>
        <td>检验位置</td>
        <td>1</td>
        <td>11</td>
        <td>13</td>
        </tr>
        <tr>
        <td>**检验标准**</td>
        <td>27.80+0.10-0.00(mm)</td>
        <td>Φ6.00±0.10(mm)</td>
        <td>73.20+0.00-0.15(mm)</td>
        </tr>
        </table>

        <table>
        <tr>
        <td>结果序号</td>
        <td>测试结果(1)</td>
        <td>判定</td>
        <td>测试结果(11)</td>
        <td>判定</td>
        <td>测试结果(13)</td>
        <td>判定</td>
        </tr>
        <tr>
        <td>1</td>
        <td>27.85</td>
        <td>OK</td>
        <td>6.02</td>
        <td>OK</td>
        <td>73.14</td>
        <td>OK</td>
        </tr>
        <tr>
        <td>2</td>
        <td>27.84</td>
        <td>OK</td>
        <td>6.02</td>
        <td>OK</td>
        <td>73.12</td>
        <td>OK</td>
        </tr>
        <tr>
        <td>3</td>
        <td>27.81</td>
        <td>OK</td>
        <td>6.01</td>
        <td>OK</td>
        <td>73.15</td>
        <td>OK</td>
        </tr>
        <tr>
        <td>4</td>
        <td>27.82</td>
        <td>OK</td>
        <td>6.01</td>
        <td>OK</td>
        <td>73.12</td>
        <td>OK</td>
        </tr>
        <tr>
        <td>5</td>
        <td>27.85</td>
        <td>OK</td>
        <td>6.06</td>
        <td>OK</td>
        <td>73.10</td>
        <td>OK</td>
        </tr>
        </table>
        """

        dimensions = parse_html_tables_for_dimensions(markdown)

        self.assertEqual(len(dimensions), 3,
                        f"Expected 3 dimensions from HTML split tables, got {len(dimensions)}")

        print("✅ Real file format test PASSED!")

if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
