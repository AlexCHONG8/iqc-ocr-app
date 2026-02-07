#!/usr/bin/env python3
"""
MinerU PDF to Markdown Converter

Automates conversion of PDF files (including handwritten) to Markdown format
using MinerU CLI tool. Supports batch processing and API key authentication.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, List


class MinerUConverter:
    """Convert PDFs to Markdown using MinerU."""

    def __init__(
        self,
        output_dir: str = "./output",
        backend: str = "pipeline",
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        lang: str = "auto",
        device: str = "cpu"
    ):
        """
        Initialize the MinerU converter.

        Args:
            output_dir: Directory for converted markdown files
            backend: Parser backend (pipeline, hybrid-auto-engine, vlm-http-client)
            api_url: URL for HTTP client API (for vlm/hybrid backends)
            api_key: API key for authentication
            lang: Document language for OCR
            device: Inference device (cpu, cuda, mps, npu)
        """
        self.output_dir = Path(output_dir).absolute()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.backend = backend
        self.api_url = api_url
        self.api_key = api_key
        self.lang = lang
        self.device = device

    def _build_command(self, input_path: str) -> List[str]:
        """Build the mineru command with all options."""
        cmd = ["mineru"]

        # Input and output paths
        cmd.extend(["-p", input_path])
        cmd.extend(["-o", str(self.output_dir)])

        # Backend selection
        cmd.extend(["-b", self.backend])

        # Language setting (for better OCR accuracy)
        if self.lang != "auto":
            cmd.extend(["-l", self.lang])

        # Device selection
        cmd.extend(["-d", self.device])

        # API URL for http-client backends
        if self.api_url and "http-client" in self.backend:
            cmd.extend(["-u", self.api_url])

        return cmd

    def _set_env_vars(self) -> dict:
        """Set environment variables for API key authentication."""
        env = os.environ.copy()

        if self.api_key and "http-client" in self.backend:
            env["MINERU_VL_API_KEY"] = self.api_key

        return env

    def convert(self, input_path: str) -> dict:
        """
        Convert a single PDF to Markdown.

        Args:
            input_path: Path to input PDF file

        Returns:
            Dict with conversion results including output file path
        """
        input_file = Path(input_path).absolute()

        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if input_file.suffix.lower() != ".pdf":
            raise ValueError(f"Input must be a PDF file: {input_path}")

        print(f"Converting: {input_file.name}")

        cmd = self._build_command(str(input_file))
        env = self._set_env_vars()

        # Run mineru command
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"MinerU conversion failed: {result.stderr}")

        # Find output markdown file
        output_name = input_file.stem
        md_files = list(self.output_dir.rglob(f"{output_name}/*.md"))

        if not md_files:
            # Try alternative output patterns
            md_files = list(self.output_dir.rglob("*.md"))

        if md_files:
            output_file = md_files[0]
            print(f"Output: {output_file}")
            return {
                "success": True,
                "input": str(input_file),
                "output": str(output_file),
                "stdout": result.stdout
            }
        else:
            return {
                "success": False,
                "input": str(input_file),
                "error": "Output markdown file not found",
                "stdout": result.stdout
            }

    def convert_batch(self, input_paths: List[str]) -> List[dict]:
        """
        Convert multiple PDFs to Markdown.

        Args:
            input_paths: List of paths to input PDF files

        Returns:
            List of conversion results
        """
        results = []

        for path in input_paths:
            try:
                result = self.convert(path)
                results.append(result)
            except Exception as e:
                results.append({
                    "success": False,
                    "input": path,
                    "error": str(e)
                })

        return results


def main():
    """Command line interface for the converter."""
    parser = argparse.ArgumentParser(
        description="Convert PDFs to Markdown using MinerU"
    )
    parser.add_argument(
        "input",
        nargs="+",
        help="Input PDF file(s) or directory"
    )
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Output directory (default: ./output)"
    )
    parser.add_argument(
        "-b", "--backend",
        choices=["pipeline", "hybrid-auto-engine", "vlm-http-client", "hybrid-http-client"],
        default="pipeline",
        help="Parser backend (default: pipeline for CPU/handwritten PDFs)"
    )
    parser.add_argument(
        "-u", "--api-url",
        help="API URL for http-client backends"
    )
    parser.add_argument(
        "-k", "--api-key",
        help="API key for authentication"
    )
    parser.add_argument(
        "-l", "--lang",
        default="auto",
        help="Document language (ch, en, korean, japan, etc.)"
    )
    parser.add_argument(
        "-d", "--device",
        default="cpu",
        help="Inference device (cpu, cuda, mps, npu)"
    )

    args = parser.parse_args()

    # Collect input files
    input_files = []
    for path in args.input:
        p = Path(path)
        if p.is_dir():
            input_files.extend(p.glob("**/*.pdf"))
        elif p.is_file() and p.suffix.lower() == ".pdf":
            input_files.append(p)
        else:
            print(f"Warning: Skipping non-PDF: {path}", file=sys.stderr)

    if not input_files:
        print("Error: No PDF files found", file=sys.stderr)
        sys.exit(1)

    # Create converter and process files
    converter = MinerUConverter(
        output_dir=args.output,
        backend=args.backend,
        api_url=args.api_url,
        api_key=args.api_key,
        lang=args.lang,
        device=args.device
    )

    results = converter.convert_batch([str(f) for f in input_files])

    # Print summary
    successful = sum(1 for r in results if r.get("success"))
    print(f"\nConverted {successful}/{len(results)} files successfully")

    # Save results JSON
    results_file = Path(args.output) / "conversion_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    main()
