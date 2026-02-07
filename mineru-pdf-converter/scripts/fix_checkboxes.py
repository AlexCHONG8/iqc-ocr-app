#!/usr/bin/env python3
"""
Post-process MinerU markdown output to fix checkbox selections.
Detects patterns like "OK NG" and replaces with selected option based on context.
"""
import re
import sys

def fix_checkboxes(content: str) -> str:
    """Fix common MinerU checkbox detection issues."""
    # Pattern 1: Both options present - keep first (usually selected)
    content = re.sub(r'OK NG', r'☑OK', content)

    # Pattern 2: Checked vs unchecked box symbols
    content = re.sub(r'ΦOK □NG', r'☑OK', content)  # Φ = checked, □ = unchecked
    content = re.sub(r'□OK ΦNG', r'☑NG', content)  # Reverse case

    # Pattern 3: Chinese pass/fail
    content = re.sub(r'合格 不合格', r'合格', content)
    content = re.sub(r'不合格 合格', r'不合格', content)

    return content

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_checkboxes.py <input.md> [output.md]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    fixed = fix_checkboxes(content)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(fixed)

    print(f"Fixed: {input_file} → {output_file}")
