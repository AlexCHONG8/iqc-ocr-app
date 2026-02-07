#!/usr/bin/env python3
"""Tests for OCR table extraction - Column mapping bug fix.

Following TDD: Write test first, watch it fail, then fix.
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from app import parse_html_tables_for_dimensions


class TestOCRColumnMapping(unittest.TestCase):
    """Test that spec columns are correctly mapped to data columns."""

    def test_three_measurements_with_noncontiguous_specs(self):
        """
        Should extract all 3 measurements when spec columns are non-contiguous.

        Table structure (simulating OCR output with empty column):
        | 序号 | 位置1 |   | 位置2 | 位置3 |
        | 检验标准 | 27.85±0.5 |   | 15.2±0.3 | 8.0±0.2 |
        | 1 | 27.85 | OK | 15.3 | OK | 8.1 | OK |
        | 2 | 27.90 | OK | 15.1 | OK | 8.0 | OK |
        | 3 | 27.80 | OK | 15.2 | OK | 7.9 | OK |
        | 4 | 27.85 | OK | 15.3 | OK | 8.0 | OK |
        | 5 | 27.88 | OK | 15.2 | OK | 8.1 | OK |

        The empty column causes spec_col_indices to be [1, 3, 4]
        Current buggy code uses 1+i*2 = [1, 3, 5] which misses column 4!
        """
        markdown = """
        <table>
        <tr>
        <td>序号</td>
        <td>位置1</td>
        <td></td>
        <td>位置2</td>
        <td>位置3</td>
        </tr>
        <tr>
        <td>检验标准</td>
        <td>27.85±0.5</td>
        <td></td>
        <td>15.2±0.3</td>
        <td>8.0±0.2</td>
        </tr>
        <tr>
        <td>1</td>
        <td>27.85</td>
        <td>OK</td>
        <td>15.3</td>
        <td>8.1</td>
        </tr>
        <tr>
        <td>2</td>
        <td>27.90</td>
        <td>OK</td>
        <td>15.1</td>
        <td>8.0</td>
        </tr>
        <tr>
        <td>3</td>
        <td>27.80</td>
        <td>OK</td>
        <td>15.2</td>
        <td>7.9</td>
        </tr>
        <tr>
        <td>4</td>
        <td>27.85</td>
        <td>OK</td>
        <td>15.3</td>
        <td>8.0</td>
        </tr>
        <tr>
        <td>5</td>
        <td>27.88</td>
        <td>OK</td>
        <td>15.2</td>
        <td>8.1</td>
        </tr>
        </table>
        """

        dimensions = parse_html_tables_for_dimensions(markdown)

        # Should find 3 dimensions
        self.assertEqual(len(dimensions), 3,
                        f"Expected 3 dimensions, got {len(dimensions)}: {[d['position'] for d in dimensions]}")

        # Verify first dimension (位置1)
        self.assertEqual(dimensions[0]['position'], '位置 1')
        self.assertEqual(dimensions[0]['spec'], '27.85±0.5')
        self.assertEqual(len(dimensions[0]['measurements']), 5)
        self.assertAlmostEqual(dimensions[0]['measurements'][0], 27.85, places=1)

        # Verify second dimension (位置2)
        self.assertEqual(dimensions[1]['position'], '位置 2')
        self.assertEqual(dimensions[1]['spec'], '15.2±0.3')
        self.assertEqual(len(dimensions[1]['measurements']), 5)
        self.assertAlmostEqual(dimensions[1]['measurements'][0], 15.3, places=1)

        # Verify third dimension (位置3)
        self.assertEqual(dimensions[2]['position'], '位置 3')
        self.assertEqual(dimensions[2]['spec'], '8.0±0.2')
        self.assertEqual(len(dimensions[2]['measurements']), 5)
        self.assertAlmostEqual(dimensions[2]['measurements'][0], 8.1, places=1)

    def test_spec_column_with_gap(self):
        """
        Should correctly map data columns when there's a gap in spec columns.

        This tests the actual bug: spec at columns 1, 3, 4 should map to
        data at the SAME columns, not use 1+i*2 pattern.

        spec_col_indices = [1, 3, 4]
        Buggy code: data_col_idx = 1 + i*2 → [1, 3, 5] (wrong!)
        Fixed code: data_col_idx = spec_col_idx → [1, 3, 4] (correct!)
        """
        markdown = """
        <table>
        <tr><td>检验标准</td><td>10±1</td><td></td><td>20±2</td><td>30±3</td></tr>
        <tr><td>1</td><td>10.5</td><td>OK</td><td>20.3</td><td>30.1</td></tr>
        <tr><td>2</td><td>10.2</td><td>OK</td><td>20.1</td><td>30.2</td></tr>
        <tr><td>3</td><td>10.3</td><td>OK</td><td>20.2</td><td>30.0</td></tr>
        <tr><td>4</td><td>10.1</td><td>OK</td><td>20.4</td><td>30.3</td></tr>
        <tr><td>5</td><td>10.4</td><td>OK</td><td>20.0</td><td>30.1</td></tr>
        </table>
        """

        dimensions = parse_html_tables_for_dimensions(markdown)

        # Should find 3 dimensions (not 2!)
        self.assertEqual(len(dimensions), 3,
                        f"Should extract all 3 dimensions despite column gap. Got {len(dimensions)}: {dimensions}")

        # Each should have 5 measurements
        for i, dim in enumerate(dimensions):
            self.assertEqual(len(dim['measurements']), 5,
                           f"Dimension {i+1} ({dim['position']}) should have 5 measurements, got {len(dim['measurements'])}")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
