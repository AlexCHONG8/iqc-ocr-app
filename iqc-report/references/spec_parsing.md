# IQC Specification Parsing Guide

## Supported Specification Formats

### 1. Bilateral Tolerance: `27.80+0.10-0.00`
- Format: `<nominal>+<positive_tol>-<negative_tol>`
- Example: `27.80+0.10-0.00` → USL=27.90, LSL=27.80, Nominal=27.80

### 2. Symmetric Tolerance: `Ø6.00±0.10` or `Φ6.00±0.10`
- Format: `<diameter_symbol><nominal>±<tolerance>`
- Example: `Ø6.00±0.10` → USL=6.10, LSL=5.90, Nominal=6.00

### 3. Unilateral Upper: `73.20+0.00-0.15`
- Format: `<nominal>+<zero>-<negative_tol>`
- Example: `73.20+0.00-0.15` → USL=73.20, LSL=73.05, Nominal=73.20

## Control Chart Constants (n=5)

| Constant | Value | Used For |
|----------|-------|----------|
| A2 | 0.577 | Xbar UCL/LCL |
| D3 | 0.0 | R LCL |
| D4 | 2.114 | R UCL |

## Formulas

### Process Capability Indices

- **Cp** = (USL - LSL) / (6 × σ)
- **Cpk** = min[(USL - μ)/(3σ), (μ - LSL)/(3σ)]
- **Pp** = (USL - LSL) / (6 × σ_overall)
- **Ppk** = min[(USL - μ)/(3σ), (μ - LSL)/(3σ)]

### Control Limits

- **Xbar UCL** = X̄̄ + A2 × R̄
- **Xbar LCL** = X̄̄ - A2 × R̄
- **R UCL** = D4 × R̄
- **R LCL** = D3 × R̄
