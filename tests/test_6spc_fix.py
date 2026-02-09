#!/usr/bin/env python3
"""
Unit tests for 6SPC statistical calculation fix.
Validates that Cp/Cpk use σ_within and Pp/Ppk use σ_overall.
"""

import unittest
import sys
import importlib.util
from pathlib import Path

# Dynamically import iqc_stats due to hyphenated directory name
iqc_stats_path = Path(__file__).parent.parent / "iqc-report" / "scripts" / "iqc_stats.py"
spec = importlib.util.spec_from_file_location("iqc_stats", iqc_stats_path)
iqc_stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iqc_stats)


class Test6SPCFix(unittest.TestCase):
    """Test suite to verify the 6SPC calculation fix."""

    def test_stable_process_cp_should_equal_pp(self):
        """Test stable process: Cp should approximately equal Pp."""
        # Stable process - no mean shifts between subgroups
        measurements = [
            10.00, 10.01, 9.99, 10.00, 10.01,  # Subgroup 1
            10.00, 9.99, 10.01, 10.00, 9.99,   # Subgroup 2
            10.01, 10.00, 9.99, 10.01, 10.00,  # Subgroup 3
            9.99, 10.00, 10.01, 9.99, 10.00,   # Subgroup 4
            10.00, 9.99, 10.01, 10.00, 10.01,  # Subgroup 5
            9.99, 10.00, 9.99, 10.00, 10.01,   # Subgroup 6
            10.01, 10.00, 9.99, 10.01, 10.00,  # Subgroup 7
            10.00, 9.99, 10.00, 9.99, 10.01,   # Subgroup 8
            10.01, 10.00, 10.01, 9.99, 10.00,  # Subgroup 9
            9.99, 10.00, 10.01, 10.00, 9.99    # Subgroup 10
        ]

        usl, lsl, nominal = 10.15, 9.85, 10.00
        subgroups = iqc_stats.calculate_subgroups(measurements)
        result = iqc_stats.calculate_process_capability(
            measurements, usl, lsl, nominal, subgroups
        )

        # For stable process, Cp ≈ Pp (within 10% tolerance)
        cp, pp = result["cp"], result["pp"]
        self.assertAlmostEqual(cp, pp, delta=0.1 * pp,
                             msg=f"Stable process: Cp ({cp}) should ≈ Pp ({pp})")

        # Verify σ_within ≈ σ_overall
        self.assertIn("std_dev_within", result,
                     msg="Result should include std_dev_within")
        self.assertIn("std_dev_overall", result,
                     msg="Result should include std_dev_overall")

    def test_unstable_process_cp_should_be_greater_than_pp(self):
        """Test unstable process: Cp should be greater than Pp."""
        # Unstable process - mean shifts between subgroups
        measurements = [
            10.00, 10.00, 10.00, 10.00, 10.00,  # Subgroup 1: mean=10.00
            10.01, 10.01, 10.01, 10.01, 10.01,  # Subgroup 2: mean=10.01
            10.02, 10.02, 10.02, 10.02, 10.02,  # Subgroup 3: mean=10.02
            10.03, 10.03, 10.03, 10.03, 10.03,  # Subgroup 4: mean=10.03
            10.04, 10.04, 10.04, 10.04, 10.04,  # Subgroup 5: mean=10.04
            10.05, 10.05, 10.05, 10.05, 10.05,  # Subgroup 6: mean=10.05
            10.04, 10.04, 10.04, 10.04, 10.04,  # Subgroup 7: mean=10.04
            10.03, 10.03, 10.03, 10.03, 10.03,  # Subgroup 8: mean=10.03
            10.02, 10.02, 10.02, 10.02, 10.02,  # Subgroup 9: mean=10.02
            10.01, 10.01, 10.01, 10.01, 10.01   # Subgroup 10: mean=10.01
        ]

        usl, lsl, nominal = 10.15, 9.85, 10.00
        subgroups = iqc_stats.calculate_subgroups(measurements)
        result = iqc_stats.calculate_process_capability(
            measurements, usl, lsl, nominal, subgroups
        )

        # For unstable process with mean shifts, Cp > Pp
        cp, pp = result["cp"], result["pp"]
        self.assertGreater(cp, pp,
                          msg=f"Unstable process: Cp ({cp}) should be > Pp ({pp})")

        # Verify σ_within < σ_overall
        std_within = result["std_dev_within"]
        std_overall = result["std_dev_overall"]
        self.assertLess(std_within, std_overall,
                       msg=f"σ_within ({std_within}) should be < σ_overall ({std_overall})")

    def test_within_std_calculated_from_r_bar(self):
        """Test that σ_within is calculated from R̄/d₂."""
        measurements = [
            27.85, 27.84, 27.81, 27.82, 27.85,  # Subgroup 1: R=0.04
            27.84, 27.82, 27.85, 27.81, 27.84,  # Subgroup 2: R=0.04
            27.84, 27.87, 27.82, 27.81, 27.86,  # Subgroup 3: R=0.06
        ]

        usl, lsl, nominal = 27.90, 27.80, 27.80
        subgroups = iqc_stats.calculate_subgroups(measurements)
        result = iqc_stats.calculate_process_capability(
            measurements, usl, lsl, nominal, subgroups
        )

        # Calculate expected R̄
        expected_r_bar = (0.04 + 0.04 + 0.06) / 3
        # Expected σ_within = R̄ / d₂ (d₂=2.326 for n=5)
        expected_std_within = expected_r_bar / 2.326

        # Verify σ_within matches expected calculation
        actual_std_within = result["std_dev_within"]
        self.assertAlmostEqual(actual_std_within, expected_std_within, places=4,
                             msg=f"σ_within should be R̄/d₂ = {expected_std_within:.6f}")

    def test_real_iqc_data_position_1(self):
        """Test with real IQC data from file (Position 1: 27.80+0.10-0.00)."""
        # First 20 measurements from real data
        measurements = [
            27.85, 27.84, 27.81, 27.82, 27.85,
            27.84, 27.82, 27.85, 27.81, 27.84,
            27.84, 27.82, 27.85, 27.81, 27.83,
            27.87, 27.82, 27.81, 27.86, 27.83
        ]

        usl, lsl, nominal = 27.90, 27.80, 27.80
        subgroups = iqc_stats.calculate_subgroups(measurements)
        result = iqc_stats.calculate_process_capability(
            measurements, usl, lsl, nominal, subgroups
        )

        # Verify Cp ≠ Pp (they should be different)
        cp, pp = result["cp"], result["pp"]
        self.assertNotAlmostEqual(cp, pp, places=2,
                                msg=f"Position 1: Cp ({cp}) should ≠ Pp ({pp})")

        # Verify σ_within ≠ σ_overall
        std_within = result["std_dev_within"]
        std_overall = result["std_dev_overall"]
        self.assertNotAlmostEqual(std_within, std_overall, places=4,
                                msg="σ_within should ≠ σ_overall")

        # Both should be non-zero
        self.assertGreater(cp, 0, msg="Cp should be > 0")
        self.assertGreater(pp, 0, msg="Pp should be > 0")

    def test_real_iqc_data_position_11(self):
        """Test with real IQC data from file (Position 11: Φ6.00±0.10)."""
        measurements = [
            6.02, 6.02, 6.01, 6.01, 6.06,
            6.02, 6.04, 6.02, 6.03, 6.03,
            6.04, 6.05, 6.03, 6.03, 6.05,
            6.01, 6.04, 6.02, 6.02, 6.01
        ]

        usl, lsl, nominal = 6.10, 5.90, 6.00
        subgroups = iqc_stats.calculate_subgroups(measurements)
        result = iqc_stats.calculate_process_capability(
            measurements, usl, lsl, nominal, subgroups
        )

        # For this data, Cp and Pp should differ
        cp, pp = result["cp"], result["pp"]
        ratio = abs(cp - pp) / max(cp, pp) if max(cp, pp) > 0 else 0
        self.assertGreater(ratio, 0.01,
                         msg=f"Position 11: Cp ({cp}) and Pp ({pp}) should differ by >1%")

    def test_parse_dimension_from_data_passes_subgroups(self):
        """Test that parse_dimension_from_data passes subgroups correctly."""
        measurements = [10.0] * 50  # 50 stable measurements
        spec = "10.00±0.10"

        result = iqc_stats.parse_dimension_from_data("1", spec, measurements)

        # Verify subgroups were calculated
        self.assertIn("subgroups", result)
        self.assertEqual(len(result["subgroups"]), 10)  # 50/5 = 10 subgroups

        # Verify both std devs are present
        self.assertIn("std_dev_within", result)
        self.assertIn("std_dev_overall", result)

        # Verify Cp and Pp are both calculated
        self.assertIn("cp", result)
        self.assertIn("pp", result)

    def test_control_limits_constants(self):
        """Test that Xbar-R control limit constants are correct for n=5."""
        measurements = [10.0 + i*0.01 for i in range(50)]
        subgroups = iqc_stats.calculate_subgroups(measurements)
        control_limits = iqc_stats.calculate_control_limits(subgroups)

        # Verify constants are correct for n=5
        # A2 should be used in UCL_X and LCL_X
        # D3 and D4 should be used in R chart limits
        self.assertIn("ucl_x", control_limits)
        self.assertIn("lcl_x", control_limits)
        self.assertIn("ucl_r", control_limits)
        self.assertIn("lcl_r", control_limits)

        # For n=5: A2=0.577, D3=0, D4=2.114
        # LCL_R should be 0 (since D3=0)
        self.assertEqual(control_limits["lcl_r"], 0.0)


class Test6SPCBugRegression(unittest.TestCase):
    """Regression tests to ensure the bug doesn't reappear."""

    def test_cp_not_equal_pp_unstable_data(self):
        """Regression test: Ensure Cp ≠ Pp for unstable data."""
        # Data with obvious mean shift
        measurements = (
            [10.00] * 25 +  # First half: mean=10.00
            [11.00] * 25    # Second half: mean=11.00 (1.0 unit shift!)
        )

        usl, lsl, nominal = 11.50, 9.50, 10.50
        subgroups = iqc_stats.calculate_subgroups(measurements)
        result = iqc_stats.calculate_process_capability(
            measurements, usl, lsl, nominal, subgroups
        )

        cp, pp = result["cp"], result["pp"]

        # With such a large mean shift, Cp should be MUCH greater than Pp
        # Cp > Pp detects the process instability
        self.assertGreater(cp, pp,
                          msg=f"REGRESSION: Cp ({cp}) > Pp ({pp}) for unstable process")

        # The difference should be significant (>20%)
        ratio = (cp - pp) / cp if cp > 0 else 0
        self.assertGreater(ratio, 0.20,
                         msg=f"REGRESSION: Cp-Pp difference ({ratio:.1%}) should be >20%")


def run_tests():
    """Run all tests and print summary."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(Test6SPCFix))
    suite.addTests(loader.loadTestsFromTestCase(Test6SPCBugRegression))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)

    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED - Fix verified successfully!")
        return 0
    else:
        print("❌ TESTS FAILED - Fix needs attention")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
