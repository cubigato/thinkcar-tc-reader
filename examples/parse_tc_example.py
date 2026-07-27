#!/usr/bin/env python3
"""
Example parser for ThinkCar .TC files.

This script demonstrates how to parse and extract data from ThinkCar diagnostic
log files (.TC format). Based on reverse engineering of the LSX8/LSX9 file format.

This is a reference implementation showing the low-level parsing approach.
For production use, prefer the thinkcar_tc_reader library instead.

Usage:
    python parse_tc_example.py <filename.TC>
    python parse_tc_example.py ../testdata/SUBARU_9T8P20524415_20260117154318.TC
"""

import struct
import sys
from pathlib import Path


def read_uint16(data: bytes, offset: int) -> int:
    """Read a little-endian uint16 from data at offset."""
    return struct.unpack("<H", data[offset : offset + 2])[0]


def read_uint32(data: bytes, offset: int) -> int:
    """Read a little-endian uint32 from data at offset."""
    return struct.unpack("<I", data[offset : offset + 4])[0]


def parse_string_table(data: bytes, start_pos: int) -> list[str]:
    """
    Parse the string table from the TC file.

    Format: Each string is stored as:
        - 2-byte length (uint16 LE)
        - string data (null-terminated)

    Returns a list with index 0 as empty placeholder (for 1-based indexing).
    """
    strings = [""]  # Placeholder at index 0 for 1-based indexing
    pos = start_pos

    while pos < len(data) - 2:
        length = read_uint16(data, pos)
        if length == 0 or length > 500:
            break

        pos += 2
        start = pos

        # Find null terminator
        while pos < len(data) and data[pos] != 0:
            pos += 1

        try:
            s = data[start:pos].decode("utf-8")
        except UnicodeDecodeError:
            s = data[start:pos].decode("latin-1")

        strings.append(s)
        pos += 1  # Skip null terminator

    return strings


def parse_tc_file(filepath: str) -> dict:
    """
    Parse a ThinkCar .TC file and return structured data.

    Returns a dict with:
        - magic: File magic string
        - metadata: Dict with language, timestamp, region, etc.
        - parameters: List of parameter names
        - parameter_units: Positional unit for every parameter
        - units: List of unit strings
        - records: List of dicts, each containing parameter values
    """
    with open(filepath, "rb") as f:
        data = f.read()

    # Verify magic
    magic = data[0:4].decode("ascii")
    if magic not in {"LSX8", "LSX9"}:
        raise ValueError(f"Invalid magic: {magic}, expected LSX8 or LSX9")

    # Get string table offset from header
    string_table_offset = read_uint32(data, 0x0C)

    # Parse string table (skip 16-byte header)
    strings = parse_string_table(data, string_table_offset + 16)

    # Extract metadata (indices 1-8)
    metadata = {
        "language": strings[1] if len(strings) > 1 else "",
        "timestamp": strings[2] if len(strings) > 2 else "",
        "region": strings[3] if len(strings) > 3 else "",
        "version": strings[4] if len(strings) > 4 else "",
        "manufacturer": strings[5] if len(strings) > 5 else "",
        "device_id": strings[6] if len(strings) > 6 else "",
        "protocol": strings[7] if len(strings) > 7 else "",
        "session_id": strings[8] if len(strings) > 8 else "",
    }

    # Follow the data descriptor and data block pointers.
    data_descriptor_offset = read_uint32(data, 0x118) or 0x128
    data_block_offset = read_uint32(data, data_descriptor_offset + 4)
    data_offset = data_block_offset + 16
    record_size = read_uint32(data, data_block_offset + 12)
    data_size = read_uint32(data, data_block_offset + 8)
    record_count = data_size // record_size
    parameter_count = record_size // 4

    # Get one parameter definition for each uint32 in a record.
    parameter_table_offset = data_descriptor_offset + 16
    param_indices = []
    for i in range(parameter_count):
        idx = read_uint16(data, parameter_table_offset + i * 4)
        param_indices.append(idx)

    # Build parameter names list
    parameters = [
        strings[idx] if idx < len(strings) else f"<{idx}>" for idx in param_indices
    ]

    # Units form a parallel table one record-width after the parameter names.
    parameter_units = []
    unit_table_offset = parameter_table_offset + record_size
    for i in range(parameter_count):
        idx = read_uint16(data, unit_table_offset + i * 4)
        unit = strings[idx].strip() if 0 < idx < len(strings) else ""
        parameter_units.append(unit)
    units = list(dict.fromkeys(unit for unit in parameter_units if unit))

    # Parse data records
    records = []
    for rec_num in range(record_count):
        offset = data_offset + rec_num * record_size
        values = struct.unpack(
            "<" + "I" * parameter_count,
            data[offset : offset + record_size],
        )

        # Map values to parameter names
        record = {}
        for i, param_name in enumerate(parameters):
            value_idx = values[i]
            value = strings[value_idx] if value_idx < len(strings) else f"<{value_idx}>"
            record[param_name] = value

        records.append(record)

    return {
        "magic": magic,
        "metadata": metadata,
        "parameters": parameters,
        "parameter_units": parameter_units,
        "units": units,
        "records": records,
        "record_count": record_count,
        "string_count": len(strings) - 1,  # Exclude placeholder
    }


def export_to_csv(parsed_data: dict, output_path: str):
    """Export parsed TC data to CSV format."""
    import csv

    # Rename duplicate columns to make them unique
    headers = []
    seen = {}
    for p in parsed_data["parameters"]:
        if p in seen:
            seen[p] += 1
            headers.append(f"{p} ({seen[p]})")
        else:
            seen[p] = 1
            headers.append(p)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header row with unique column names
        writer.writerow(["Record"] + headers)
        writer.writerow(["Unit"] + parsed_data["parameter_units"])

        # Data rows
        for i, record in enumerate(parsed_data["records"]):
            row = [i] + [record.get(p, "") for p in parsed_data["parameters"]]
            writer.writerow(row)

    print(f"Exported {len(parsed_data['records'])} records to {output_path}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    filepath = sys.argv[1]

    if not Path(filepath).exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    print(f"Parsing: {filepath}")
    print("=" * 60)

    try:
        parsed = parse_tc_file(filepath)
    except Exception as e:
        print(f"Error parsing file: {e}")
        sys.exit(1)

    # Print metadata
    print(f"\nFile Magic: {parsed['magic']}")
    print(f"\nMetadata:")
    for key, value in parsed["metadata"].items():
        print(f"  {key:15s}: {value}")

    print(f"\nStatistics:")
    print(f"  Parameters:    {len(parsed['parameters'])}")
    print(f"  Records:       {parsed['record_count']}")
    print(f"  Total strings: {parsed['string_count']}")

    print(f"\nUnits found: {parsed['units']}")

    print(f"\nParameters:")
    for i, (param, unit) in enumerate(
        zip(parsed["parameters"], parsed["parameter_units"], strict=True)
    ):
        suffix = f" [{unit}]" if unit else ""
        print(f"  [{i:2d}] {param}{suffix}")

    print(f"\nSample Data (first 5 records):")
    print("-" * 60)

    # Show a few commonly encountered parameters when present.
    key_params = [
        "Engine Speed",
        "ATF Temp.",
        "Control module voltage",
        "Accel. Opening Angle",
    ]

    for i, record in enumerate(parsed["records"][:5]):
        print(f"Record {i}:")
        for param in key_params:
            if param in record:
                print(f"  {param:25s}: {record[param]}")
        print()

    # Optional: Export to CSV
    if len(sys.argv) > 2 and sys.argv[2] == "--csv":
        csv_path = Path(filepath).with_suffix(".csv")
        export_to_csv(parsed, str(csv_path))


if __name__ == "__main__":
    main()
