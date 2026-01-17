"""
ThinkCar .TC file parser.

This module implements the parser for ThinkCar diagnostic log files (.TC format)
based on the reverse-engineered file format specification.

The TC format uses:
- Binary structure with LSX9 magic signature
- String table architecture for storing all values
- 1-based string indexing
- 32 parameters per record × 128 bytes per record
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TCMetadata:
    """Metadata from a TC file."""

    language: str
    timestamp: str
    region: str
    version: str
    manufacturer: str
    device_id: str
    protocol: str
    session_id: str


@dataclass
class TCData:
    """Parsed data from a TC file."""

    magic: str
    metadata: TCMetadata
    parameters: list[str]
    units: list[str]
    records: list[dict[str, str]]
    record_count: int
    string_count: int

    def get_parameter_values(self, param_name: str) -> list[str]:
        """Get all values for a specific parameter across all records."""
        return [record.get(param_name, "") for record in self.records]


class TCParseError(Exception):
    """Exception raised when parsing a TC file fails."""

    pass


def _read_uint16(data: bytes, offset: int) -> int:
    """Read a little-endian uint16 from data at offset."""
    if offset + 2 > len(data):
        raise TCParseError(f"Cannot read uint16 at offset {offset:#x}: out of bounds")
    return struct.unpack("<H", data[offset : offset + 2])[0]


def _read_uint32(data: bytes, offset: int) -> int:
    """Read a little-endian uint32 from data at offset."""
    if offset + 4 > len(data):
        raise TCParseError(f"Cannot read uint32 at offset {offset:#x}: out of bounds")
    return struct.unpack("<I", data[offset : offset + 4])[0]


def _parse_string_table(data: bytes, start_pos: int) -> list[str]:
    """
    Parse the string table from the TC file.

    Format: Each string is stored as:
        - 2-byte length (uint16 LE) including null terminator
        - string data (null-terminated UTF-8)

    Returns a list with index 0 as empty placeholder (for 1-based indexing).

    Args:
        data: Full file data
        start_pos: Offset to start of string data (after 16-byte header)

    Returns:
        List of strings with empty string at index 0
    """
    strings = [""]  # Placeholder at index 0 for 1-based indexing
    pos = start_pos

    while pos < len(data) - 2:
        length = _read_uint16(data, pos)

        # Stop conditions
        if length == 0 or length > 500:
            break

        pos += 2
        start = pos

        # Find null terminator
        while pos < len(data) and data[pos] != 0:
            pos += 1

        if pos >= len(data):
            break

        # Decode string
        try:
            s = data[start:pos].decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1 for non-UTF8 strings
            s = data[start:pos].decode("latin-1", errors="replace")

        strings.append(s)
        pos += 1  # Skip null terminator

    return strings


def parse_tc_file(filepath: str | Path) -> TCData:
    """
    Parse a ThinkCar .TC file and return structured data.

    The parser follows the TC-FILE-FORMAT.md specification:
    - Verifies LSX9 magic signature
    - Parses string table (1-based indexing)
    - Extracts parameter definitions
    - Parses data records

    Args:
        filepath: Path to the .TC file

    Returns:
        TCData object containing all parsed information

    Raises:
        TCParseError: If the file format is invalid
        FileNotFoundError: If the file doesn't exist
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "rb") as f:
        data = f.read()

    # Verify minimum file size
    if len(data) < 0x400:
        raise TCParseError(f"File too small: {len(data)} bytes (minimum 1024)")

    # 1. Verify magic signature
    try:
        magic = data[0:4].decode("ascii")
    except UnicodeDecodeError:
        raise TCParseError("Invalid magic bytes (not ASCII)")

    if magic != "LSX9":
        raise TCParseError(f"Invalid magic: {magic!r}, expected 'LSX9'")

    # 2. Get string table offset from file header at 0x0C
    try:
        string_table_offset = _read_uint32(data, 0x0C)
    except TCParseError:
        raise TCParseError("Cannot read string table offset at 0x0C")

    if string_table_offset >= len(data):
        raise TCParseError(
            f"String table offset {string_table_offset:#x} beyond file size"
        )

    # 3. Parse string table (skip 16-byte header)
    try:
        strings = _parse_string_table(data, string_table_offset + 16)
    except Exception as e:
        raise TCParseError(f"Failed to parse string table: {e}")

    # 4. Extract metadata from string indices 1-8
    metadata = TCMetadata(
        language=strings[1] if len(strings) > 1 else "",
        timestamp=strings[2] if len(strings) > 2 else "",
        region=strings[3] if len(strings) > 3 else "",
        version=strings[4] if len(strings) > 4 else "",
        manufacturer=strings[5] if len(strings) > 5 else "",
        device_id=strings[6] if len(strings) > 6 else "",
        protocol=strings[7] if len(strings) > 7 else "",
        session_id=strings[8] if len(strings) > 8 else "",
    )

    # 5. Get parameter definitions from table at 0x138 (32 entries × 4 bytes)
    param_indices = []
    for i in range(32):
        try:
            idx = _read_uint16(data, 0x138 + i * 4)
            param_indices.append(idx)
        except TCParseError:
            raise TCParseError(
                f"Cannot read parameter index {i} at offset {0x138 + i * 4:#x}"
            )

    # Build parameter names list
    parameters = []
    for idx in param_indices:
        if idx < len(strings):
            parameters.append(strings[idx])
        else:
            # Invalid index - use placeholder
            parameters.append(f"<index_{idx}>")

    # 6. Extract units (string indices 40-46 based on specification)
    units = strings[40:47] if len(strings) > 46 else []

    # 7. Get data section info from data block header at 0x338
    try:
        data_offset = 0x348  # Fixed offset after 16-byte data block header
        record_size = _read_uint32(data, 0x344)  # Usually 128
        data_size = _read_uint32(data, 0x340)
    except TCParseError as e:
        raise TCParseError(f"Cannot read data block header: {e}")

    if record_size == 0:
        raise TCParseError("Invalid record size: 0")

    record_count = data_size // record_size

    # Sanity check
    if record_count > 100000:
        raise TCParseError(f"Unrealistic record count: {record_count}")

    if data_offset + data_size > len(data):
        raise TCParseError(
            f"Data section ({data_offset:#x} + {data_size:#x}) exceeds file size"
        )

    # 8. Parse data records
    # Each record contains 32 uint32 values (string indices)
    records = []

    for rec_num in range(record_count):
        offset = data_offset + rec_num * record_size

        if offset + 128 > len(data):
            # Partial record at end of file - stop parsing
            break

        # Read 32 uint32 values (128 bytes total)
        try:
            values = struct.unpack("<" + "I" * 32, data[offset : offset + 128])
        except struct.error as e:
            raise TCParseError(f"Failed to unpack record {rec_num}: {e}")

        # Map values to parameter names
        record = {}
        for i, param_name in enumerate(parameters):
            value_idx = values[i]

            # Look up string value (indices are 1-based)
            if value_idx < len(strings):
                value = strings[value_idx]
            else:
                # Invalid index - use placeholder
                value = f"<index_{value_idx}>"

            record[param_name] = value

        records.append(record)

    return TCData(
        magic=magic,
        metadata=metadata,
        parameters=parameters,
        units=units,
        records=records,
        record_count=len(records),
        string_count=len(strings) - 1,  # Exclude placeholder at index 0
    )
