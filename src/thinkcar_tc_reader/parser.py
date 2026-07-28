"""
ThinkCar .TC file parser.

This module implements the parser for ThinkCar diagnostic log files (.TC format)
based on the reverse-engineered file format specification.

The TC format uses:
- Binary structure with LSX8 or LSX9 magic signature
- String table architecture for storing all values
- 1-based string indexing
- A device-dependent number of parameters per record
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path

from .unit_mapping import apply_known_unit_fallbacks


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
    parameter_units: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize the positional parameter-to-unit mapping."""
        has_parameter_unit_mapping = bool(self.parameter_units)
        if not has_parameter_unit_mapping:
            self.parameter_units = [""] * len(self.parameters)
        elif len(self.parameter_units) != len(self.parameters):
            raise ValueError(
                "parameter_units must contain one entry for every parameter"
            )
        else:
            self.parameter_units = [unit.strip() for unit in self.parameter_units]

        if has_parameter_unit_mapping:
            self.units = list(dict.fromkeys(u for u in self.parameter_units if u))

    def get_parameter_values(self, param_name: str) -> list[str]:
        """Get all values for a specific parameter across all records."""
        return [record.get(param_name, "") for record in self.records]

    def set_parameter_unit(self, column: int, unit: str) -> None:
        """
        Override the unit for one parameter column.

        Columns are used instead of names because TC files may contain duplicate
        parameter names. The unique ``units`` inventory is refreshed automatically.
        """
        if column < 0 or column >= len(self.parameters):
            raise IndexError(f"Parameter column out of range: {column}")

        self.parameter_units[column] = unit.strip()
        self.units = list(dict.fromkeys(u for u in self.parameter_units if u))


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
        - 2-byte total entry size (uint16 LE)
        - string data (UTF-8)
        - null terminator

    The entry size includes the 2-byte size field, string bytes, and terminator.

    Returns a list with index 0 as empty placeholder (for 1-based indexing).

    Args:
        data: Full file data
        start_pos: Offset to start of string data (after 16-byte header)

    Returns:
        List of strings with empty string at index 0
    """
    strings = [""]  # Placeholder at index 0 for 1-based indexing
    pos = start_pos

    while pos + 2 <= len(data):
        length = _read_uint16(data, pos)

        # Stop conditions
        if length == 0 or length > 500:
            break
        if length < 3:
            break

        entry_end = pos + length
        if entry_end > len(data):
            break

        payload = data[pos + 2 : entry_end]
        if not payload or payload[-1] != 0:
            break

        # Decode string
        try:
            s = payload[:-1].decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1 for non-UTF8 strings
            s = payload[:-1].decode("latin-1", errors="replace")

        strings.append(s)
        pos = entry_end

    return strings


def parse_tc_file(filepath: str | Path) -> TCData:
    """
    Parse a ThinkCar .TC file and return structured data.

    The parser follows the TC-FILE-FORMAT.md specification:
    - Verifies LSX8/LSX9 magic signature
    - Parses string table (1-based indexing)
    - Extracts parameter definitions
    - Maps every parameter to its unit
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

    if magic not in {"LSX8", "LSX9"}:
        raise TCParseError(f"Invalid magic: {magic!r}, expected 'LSX8' or 'LSX9'")

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

    # 5. Locate the data descriptor. The metadata header points to it at 0x118;
    # older documentation happened to observe it at 0x128 in every sample.
    try:
        data_descriptor_offset = _read_uint32(data, 0x118)
    except TCParseError as e:
        raise TCParseError(f"Cannot read data descriptor offset: {e}")

    if data_descriptor_offset == 0:
        # Some early/synthetic files omit the pointer, but still place the
        # descriptor at the format's conventional location.
        data_descriptor_offset = 0x128

    if data_descriptor_offset + 16 > len(data):
        raise TCParseError(
            f"Data descriptor offset {data_descriptor_offset:#x} beyond file size"
        )

    try:
        data_block_offset = _read_uint32(data, data_descriptor_offset + 4)
        parameter_section_size = _read_uint32(data, data_descriptor_offset + 8)
        descriptor_record_size = _read_uint32(data, data_descriptor_offset + 12)
    except TCParseError as e:
        raise TCParseError(f"Cannot read data descriptor: {e}")

    if data_block_offset + 16 > len(data):
        raise TCParseError(
            f"Data block offset {data_block_offset:#x} beyond file size"
        )

    # The authoritative record size is repeated in the data block header.
    try:
        data_size = _read_uint32(data, data_block_offset + 8)
        record_size = _read_uint32(data, data_block_offset + 12)
    except TCParseError as e:
        raise TCParseError(f"Cannot read data block header: {e}")

    if record_size == 0:
        raise TCParseError("Invalid record size: 0")
    if record_size % 4 != 0:
        raise TCParseError(
            f"Invalid record size: {record_size} (must be divisible by 4)"
        )
    if descriptor_record_size not in {0, record_size}:
        raise TCParseError(
            "Record size mismatch between data descriptor "
            f"({descriptor_record_size}) and data block ({record_size})"
        )
    if data_size % record_size != 0:
        raise TCParseError(
            f"Data size {data_size} is not a multiple of record size {record_size}"
        )

    parameter_count = record_size // 4
    parameter_table_offset = data_descriptor_offset + 16

    if parameter_section_size and (
        parameter_table_offset + parameter_section_size > data_block_offset
    ):
        raise TCParseError(
            "Parameter section overlaps the data block "
            f"({parameter_section_size} bytes)"
        )

    if parameter_table_offset + record_size > data_block_offset:
        raise TCParseError(
            "Parameter definition table overlaps the data block "
            f"({parameter_count} entries)"
        )

    # 6. Get one parameter definition for every uint32 value in a record.
    param_indices = []
    for i in range(parameter_count):
        try:
            idx = _read_uint16(data, parameter_table_offset + i * 4)
            param_indices.append(idx)
        except TCParseError:
            raise TCParseError(
                "Cannot read parameter index "
                f"{i} at offset {parameter_table_offset + i * 4:#x}"
            )

    # Build parameter names list
    parameters = []
    for idx in param_indices:
        if idx < len(strings):
            parameters.append(strings[idx])
        else:
            # Invalid index - use placeholder
            parameters.append(f"<index_{idx}>")

    # Unit definitions form a parallel table one record-width after the names.
    # Each entry is another 1-based string-table index; zero means no unit.
    parameter_units = [""] * parameter_count
    unit_table_offset = parameter_table_offset + record_size
    has_unit_table = (
        parameter_section_size >= record_size * 2
        and unit_table_offset + record_size <= data_block_offset
    )
    if has_unit_table:
        for i in range(parameter_count):
            unit_idx = _read_uint16(data, unit_table_offset + i * 4)
            if unit_idx == 0:
                continue
            if unit_idx < len(strings):
                # Some devices encode a missing display unit as whitespace.
                parameter_units[i] = strings[unit_idx].strip()
            else:
                parameter_units[i] = f"<index_{unit_idx}>"

    parameter_units = apply_known_unit_fallbacks(parameters, parameter_units)
    units = list(dict.fromkeys(unit for unit in parameter_units if unit))

    # 7. Validate and locate the records immediately after the block header.
    data_offset = data_block_offset + 16
    record_count = data_size // record_size

    # Sanity check
    if record_count > 100000:
        raise TCParseError(f"Unrealistic record count: {record_count}")

    if data_offset + data_size > len(data):
        raise TCParseError(
            f"Data section ({data_offset:#x} + {data_size:#x}) exceeds file size"
        )

    # 8. Parse data records. Each uint32 is a string-table index.
    records = []

    for rec_num in range(record_count):
        offset = data_offset + rec_num * record_size

        try:
            values = struct.unpack(
                "<" + "I" * parameter_count,
                data[offset : offset + record_size],
            )
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
        parameter_units=parameter_units,
    )
