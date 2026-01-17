"""
CSV exporter for ThinkCar TC data.

This module provides functionality to export parsed TC data to CSV format,
handling duplicate column names and proper encoding.
"""

import csv
from pathlib import Path
from typing import TextIO

from .parser import TCData


def export_to_csv(
    data: TCData, output_path: str | Path, include_metadata: bool = True
) -> None:
    """
    Export parsed TC data to CSV format.

    The CSV file will have:
    - Optional metadata header (as comments)
    - Column headers with parameter names (duplicates are numbered)
    - One row per record with all parameter values

    Args:
        data: Parsed TCData object
        output_path: Path to output CSV file
        include_metadata: If True, include metadata as comment lines at top

    Raises:
        IOError: If writing to the file fails
    """
    output_path = Path(output_path)

    # Create unique column headers (handle duplicates)
    headers = _make_unique_headers(data.parameters)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        # Write metadata as comments
        if include_metadata:
            _write_metadata_header(f, data)

        # Write CSV data
        writer = csv.writer(f)

        # Header row: Record number + parameter names
        writer.writerow(["Record"] + headers)

        # Data rows
        for i, record in enumerate(data.records):
            row = [i] + [record.get(p, "") for p in data.parameters]
            writer.writerow(row)


def _make_unique_headers(parameters: list[str]) -> list[str]:
    """
    Make column headers unique by numbering duplicates.

    Example:
        ["Speed", "Temp", "Speed"] -> ["Speed", "Temp", "Speed (2)"]

    Args:
        parameters: List of parameter names (may contain duplicates)

    Returns:
        List of unique column names
    """
    headers = []
    seen = {}

    for param in parameters:
        if param in seen:
            seen[param] += 1
            headers.append(f"{param} ({seen[param]})")
        else:
            seen[param] = 1
            headers.append(param)

    return headers


def _write_metadata_header(f: TextIO, data: TCData) -> None:
    """
    Write metadata as CSV comment lines.

    Args:
        f: File handle to write to
        data: TCData object with metadata
    """
    f.write(f"# ThinkCar TC File Export\n")
    f.write(f"# Magic: {data.magic}\n")
    f.write(f"#\n")
    f.write(f"# Metadata:\n")
    f.write(f"#   Language: {data.metadata.language}\n")
    f.write(f"#   Timestamp: {data.metadata.timestamp}\n")
    f.write(f"#   Region: {data.metadata.region}\n")
    f.write(f"#   Version: {data.metadata.version}\n")
    f.write(f"#   Manufacturer: {data.metadata.manufacturer}\n")
    f.write(f"#   Device ID: {data.metadata.device_id}\n")
    f.write(f"#   Protocol: {data.metadata.protocol}\n")
    f.write(f"#   Session ID: {data.metadata.session_id}\n")
    f.write(f"#\n")
    f.write(f"# Statistics:\n")
    f.write(f"#   Parameters: {len(data.parameters)}\n")
    f.write(f"#   Records: {data.record_count}\n")
    f.write(f"#   Strings: {data.string_count}\n")
    f.write(f"#\n")
    if data.units:
        f.write(f"# Units: {', '.join(data.units)}\n")
        f.write(f"#\n")
