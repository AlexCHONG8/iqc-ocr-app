#!/usr/bin/env python3
"""
IQC Statistical Analysis Script
Calculates 6SPC (Six Sigma Statistical Process Control) metrics for quality inspection data.
"""

import json
import statistics
from typing import List, Dict, Any, Tuple


def calculate_subgroups(measurements: List[float], subgroup_size: int = 5) -> List[Dict[str, float]]:
    """Divide measurements into subgroups and calculate mean/range for each."""
    subgroups = []
    for i in range(0, len(measurements), subgroup_size):
        subgroup = measurements[i:i + subgroup_size]
        # FIX: Accept partial subgroups if we don't have enough data
        if len(subgroup) >= 2:
            subgroups.append({
                "mean": round(statistics.mean(subgroup), 4),
                "range": round(max(subgroup) - min(subgroup), 4)
            })
    return subgroups


def calculate_control_limits(subgroups: List[Dict[str, float]], subgroup_size: int = 5) -> Dict[str, float]:
    """Calculate Xbar-R control chart limits using A2, D3, D4 constants."""
    # Constants for n=5
    A2, D3, D4 = 0.577, 0.0, 2.114

    # FIX: Handle empty subgroups
    if not subgroups:
        return {
            "x_bar_bar": 0.0,
            "r_bar": 0.0,
            "ucl_x": 0.0,
            "lcl_x": 0.0,
            "ucl_r": 0.0,
            "lcl_r": 0.0
        }

    x_bar_bar = statistics.mean([s["mean"] for s in subgroups])
    r_bar = statistics.mean([s["range"] for s in subgroups])

    return {
        "x_bar_bar": round(x_bar_bar, 4),
        "r_bar": round(r_bar, 4),
        "ucl_x": round(x_bar_bar + A2 * r_bar, 4),
        "lcl_x": round(x_bar_bar - A2 * r_bar, 4),
        "ucl_r": round(D4 * r_bar, 4),
        "lcl_r": round(D3 * r_bar, 0)
    }


def calculate_process_capability(
    measurements: List[float],
    usl: float,
    lsl: float,
    nominal: float,
    subgroups: List[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Calculate Cp, Cpk, Pp, Ppk and related statistics."""
    mean = statistics.mean(measurements)
    min_val = min(measurements)
    max_val = max(measurements)

    # Calculate overall standard deviation (for Pp, Ppk)
    if len(measurements) < 2:
        # Use tolerance range as estimate for std dev
        std_dev_overall = (usl - lsl) / 6 if usl > lsl else 0.1
    else:
        std_dev_overall = statistics.stdev(measurements)

    # Calculate within standard deviation (for Cp, Cpk)
    # Method 1: Use R-bar / d2 (preferred for Xbar-R charts)
    if subgroups and len(subgroups) >= 2:
        r_bar = statistics.mean([s["range"] for s in subgroups])
        d2 = 2.326  # Constant for subgroup size n=5
        # If R-bar is 0 (perfect within-subgroup consistency), use small value
        # This makes Cp large, correctly detecting between-subgroup variation
        if r_bar > 0:
            std_dev_within = r_bar / d2
        else:
            # Edge case: No within-subgroup variation
            # Use minimum resolution to avoid division by zero
            # This correctly results in high Cp when process has between-subgroup shifts
            std_dev_within = 1e-6
    else:
        # Method 2: Use moving range if no subgroups available
        if len(measurements) >= 2:
            moving_ranges = [abs(measurements[i] - measurements[i-1])
                           for i in range(1, len(measurements))]
            mr_bar = statistics.mean(moving_ranges)
            # For n=2, d2 = 1.128
            if mr_bar > 0:
                std_dev_within = mr_bar / 1.128
            else:
                std_dev_within = 1e-6
        else:
            std_dev_within = std_dev_overall

    # Process capability (within subgroup) - use std_dev_within
    cp = (usl - lsl) / (6 * std_dev_within) if std_dev_within > 0 else 0
    cpu = (usl - mean) / (3 * std_dev_within) if std_dev_within > 0 else 0
    cpl = (mean - lsl) / (3 * std_dev_within) if std_dev_within > 0 else 0
    cpk = min(cpu, cpl)

    # Overall performance (using overall std dev) - use std_dev_overall
    pp = (usl - lsl) / (6 * std_dev_overall) if std_dev_overall > 0 else 0
    ppu = (usl - mean) / (3 * std_dev_overall) if std_dev_overall > 0 else 0
    ppl = (mean - lsl) / (3 * std_dev_overall) if std_dev_overall > 0 else 0
    ppk = min(ppu, ppl)

    # Determine status and suggestion
    if cpk >= 1.33:
        conclusion = "优质合格"
        suggestion = "【绿色优良】过程能力极佳 (Cpk≥1.33)。生产工艺稳定且受控。建议保持当前控制水平，可考虑降低抽样频次。"
    elif cpk >= 1.0:
        conclusion = "合格-一般"
        suggestion = "【黄色注意】过程能力一般 (1.0≤Cpk<1.33)。建议继续监控控制图，关注过程中心偏移。"
    else:
        conclusion = "合格-过程不稳"
        suggestion = "【红色警示】过程能力不足 (Cpk<1.0)。建议：1.检查设备精度；2.反馈供方调整工艺；3.增加抽样频次。"

    # Check if any values are out of spec
    status = "OK" if all(lsl <= v <= usl for v in measurements) else "NG"

    return {
        "mean": round(mean, 4),
        "max_val": round(max_val, 3),
        "min_val": round(min_val, 3),
        "std_dev_overall": round(std_dev_overall, 6),
        "std_dev_within": round(std_dev_within, 6),
        "cp": round(cp, 3),
        "cpk": round(cpk, 3),
        "pp": round(pp, 2),
        "ppk": round(ppk, 2),
        "six_sigma_spread": round(6 * std_dev_overall, 4),
        "status": status,
        "conclusion": f"{conclusion} (Cpk: {cpk:.2f})",
        "suggestion": suggestion
    }


def parse_dimension_from_data(
    position: str,
    spec_str: str,
    measurements: List[float]
) -> Dict[str, Any]:
    """Parse dimension data and calculate all statistics."""
    # Parse specification
    # Clean the spec string: remove spaces, units, and parentheses
    spec_str = spec_str.strip().replace(" ", "").replace("mm", "").replace("(", "").replace(")", "")
    nominal, usl, lsl = 0.0, 0.0, 0.0

    if "Φ" in spec_str or "Ø" in spec_str:
        # Diameter spec like "Ø6.00±0.10" or "Φ6.00±0.10"
        spec_clean = spec_str.replace("Φ", "").replace("Ø", "")
        if "±" in spec_clean:
            base_part = spec_clean.split("±")[0]
            tol = float(spec_clean.split("±")[1])
            nominal = float(base_part)
            usl = nominal + tol
            lsl = nominal - tol
    elif "±" in spec_str:
        # ENHANCED: Handle ± format without diameter prefix (e.g., "2.88±1.0")
        parts = spec_str.split("±")
        base_part = parts[0]
        tol_part = parts[1]
        try:
            nominal = float(base_part)
            tol = float(tol_part)
            usl = nominal + tol
            lsl = nominal - tol
        except ValueError:
            # If parsing fails, use defaults
            nominal = float(base_part) if base_part.replace('.', '').isdigit() else 0.0
            usl = nominal * 1.01
            lsl = nominal * 0.99
    elif "+" in spec_str and "-" in spec_str:
        # Bilateral tolerance like "27.80+0.10-0.00"
        base = float(spec_str.split("+")[0])
        plus_tol = float(spec_str.split("+")[1].split("-")[0])
        minus_tol = float(spec_str.split("-")[1])
        nominal = base
        usl = base + plus_tol
        lsl = base - minus_tol
    else:
        # Simple spec - assume ± from nominal
        try:
            nominal = float(spec_str)
            usl = nominal * 1.01
            lsl = nominal * 0.99
        except ValueError:
            # If all parsing fails, use defaults
            nominal = 0.0
            usl = 1.0
            lsl = -1.0

    # Calculate subgroups first (needed for capability calculation)
    subgroups = calculate_subgroups(measurements)

    # Calculate statistics (pass subgroups for correct Cp/Cpk calculation)
    capability = calculate_process_capability(measurements, usl, lsl, nominal, subgroups)
    control_limits = calculate_control_limits(subgroups)

    return {
        "name": position,
        "spec": spec_str,
        "nominal": nominal,
        "usl": usl,
        "lsl": lsl,
        "measurements": measurements,
        **capability,
        "subgroups": subgroups,
        **control_limits
    }


def generate_iqc_data(
    material_name: str,
    material_code: str,
    batch_no: str,
    supplier: str,
    date: str,
    dimensions_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate complete IQC data structure for HTML report."""
    return {
        "meta": {
            "material_name": material_name,
            "material_code": material_code,
            "batch_no": batch_no,
            "supplier": supplier,
            "date": date
        },
        "dimensions": dimensions_data
    }


def generate_html_report(iqc_data: Dict[str, Any], output_path: str) -> None:
    """Generate HTML report from IQC data."""
    from pathlib import Path

    template_path = Path(__file__).parent.parent / "assets" / "iqc_template.html"
    if not template_path.exists():
        # Create basic HTML structure
        html_content = _create_basic_html(iqc_data)
    else:
        html_content = template_path.read_text(encoding="utf-8")

    # Inject data
    data_json = json.dumps(iqc_data, ensure_ascii=False, indent=8)
    html_content = html_content.replace("const iqcData = {};", f"const iqcData = {data_json};")

    # Verify replacement happened
    if "const iqcData = {};" in html_content:
        raise ValueError("Failed to replace iqcData placeholder in HTML template!")
    if "const iqcData = {" not in html_content:
        raise ValueError("iqcData JSON not properly injected into HTML!")

    # Verify dimensions exist
    if not iqc_data.get("dimensions"):
        raise ValueError("No dimensions found in IQC data!")

    print(f"✅ Injected {len(iqc_data['dimensions'])} dimensions into HTML report")

    # Write output
    Path(output_path).write_text(html_content, encoding="utf-8")
    print(f"✅ Report generated: {output_path}")


def _create_basic_html(iqc_data: Dict[str, Any]) -> str:
    """Create basic HTML structure with embedded data."""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>IQC Report - {iqc_data['meta']['material_name']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
</head>
<body>
    <h1>IQC Statistical Report</h1>
    <div id="app"></div>
    <script>
        const iqcData = {json.dumps(iqc_data, ensure_ascii=False)};
        console.log("IQC Data loaded:", iqcData);
    </script>
</body>
</html>"""


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        # Run from command line with JSON input
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            input_data = json.load(f)

        dimensions = []
        for dim_data in input_data.get("dimensions", []):
            dimensions.append(parse_dimension_from_data(
                dim_data["position"],
                dim_data["spec"],
                dim_data["measurements"]
            ))

        iqc_data = generate_iqc_data(
            input_data["meta"]["material_name"],
            input_data["meta"]["material_code"],
            input_data["meta"]["batch_no"],
            input_data["meta"]["supplier"],
            input_data["meta"]["date"],
            dimensions
        )

        output_file = sys.argv[2] if len(sys.argv) > 2 else "iqc_report.html"
        generate_html_report(iqc_data, output_file)
