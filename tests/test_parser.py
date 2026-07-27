"""
Tests for the ThinkCar TC file parser.
"""

import struct
from pathlib import Path

import pytest

from thinkcar_tc_reader.parser import (
    TCData,
    TCMetadata,
    TCParseError,
    _parse_string_table,
    _read_uint16,
    _read_uint32,
    parse_tc_file,
)


class TestBinaryReaders:
    """Test binary reading helper functions."""

    def test_read_uint16_valid(self):
        data = b"\x34\x12\x00\x00"
        assert _read_uint16(data, 0) == 0x1234

    def test_read_uint16_out_of_bounds(self):
        data = b"\x34"
        with pytest.raises(TCParseError, match="out of bounds"):
            _read_uint16(data, 0)

    def test_read_uint32_valid(self):
        data = b"\x78\x56\x34\x12"
        assert _read_uint32(data, 0) == 0x12345678

    def test_read_uint32_out_of_bounds(self):
        data = b"\x78\x56\x34"
        with pytest.raises(TCParseError, match="out of bounds"):
            _read_uint32(data, 0)


class TestStringTableParser:
    """Test string table parsing."""

    def test_parse_empty_string_table(self):
        data = b"\x00\x00"
        strings = _parse_string_table(data, 0)
        assert strings == [""]  # Only placeholder

    def test_parse_single_string(self):
        # Length=6 (includes null), "Hello\0"
        data = b"\x06\x00Hello\x00"
        strings = _parse_string_table(data, 0)
        assert len(strings) == 2
        assert strings[0] == ""  # Placeholder
        assert strings[1] == "Hello"

    def test_parse_multiple_strings(self):
        # "Foo\0" + "Bar\0"
        data = b"\x04\x00Foo\x00\x04\x00Bar\x00"
        strings = _parse_string_table(data, 0)
        assert len(strings) == 3
        assert strings[1] == "Foo"
        assert strings[2] == "Bar"

    def test_parse_string_with_utf8(self):
        data = b"\x07\x00\xc3\xa4\xc3\xb6\xc3\xbc\x00"  # "äöü\0"
        strings = _parse_string_table(data, 0)
        assert strings[1] == "äöü"

    def test_parse_string_stops_on_zero_length(self):
        data = b"\x04\x00Foo\x00\x00\x00\x04\x00Bar\x00"
        strings = _parse_string_table(data, 0)
        assert len(strings) == 2  # Placeholder + "Foo", stops at zero length


class TestTCFileParser:
    """Test TC file parsing."""

    def create_minimal_tc_file(self) -> bytes:
        """Create a minimal valid TC file for testing."""
        data = bytearray(8192)  # Increased size to accommodate string table at 0x1000

        # Magic at 0x00
        data[0:4] = b"LSX9"

        # String table offset at 0x0C (pointing to offset 0x1000)
        struct.pack_into("<I", data, 0x0C, 0x1000)

        # Data descriptor and data block pointers
        struct.pack_into("<I", data, 0x118, 0x128)
        struct.pack_into("<I", data, 0x12C, 0x338)
        struct.pack_into("<I", data, 0x134, 128)

        # Data block header at 0x338
        struct.pack_into("<I", data, 0x340, 128)  # Data size
        struct.pack_into("<I", data, 0x344, 128)  # Record size

        # Parameter table at 0x138 (32 × 4 bytes)
        for i in range(32):
            # Point to string indices 9-40
            struct.pack_into("<H", data, 0x138 + i * 4, 9 + i)

        # String table at 0x1000
        string_offset = 0x1000 + 16  # After 16-byte header

        # String table header
        struct.pack_into("<H", data, 0x1000, 0x10)  # Type
        struct.pack_into("<I", data, 0x1008, 500)  # Size
        struct.pack_into("<I", data, 0x100C, 50)  # Count

        # Add strings (indices 1-8 for metadata)
        strings = [
            "en.English",  # 1
            "Mon Jan 01 12:00:00 2024",  # 2
            "US.US",  # 3
            "1.0",  # 4
            "SUBARU",  # 5
            "12345678",  # 6
            "Canbus",  # 7
            "20240101120000",  # 8
        ]

        # Add parameter names (indices 9-40)
        for i in range(32):
            strings.append(f"Param{i}")

        # Add some value strings (indices 41+)
        strings.extend(["0.00", "1.00", "ON", "OFF"])

        # Write strings
        for s in strings:
            s_bytes = s.encode("utf-8") + b"\x00"
            length = len(s_bytes)
            struct.pack_into("<H", data, string_offset, length)
            string_offset += 2
            data[string_offset : string_offset + length] = s_bytes
            string_offset += length

        # Add one data record at 0x348 (32 × uint32)
        for i in range(32):
            # Point to value strings (indices 41-44 cycling)
            struct.pack_into("<I", data, 0x348 + i * 4, 41 + (i % 4))

        return bytes(data)

    def test_parse_minimal_file(self, tmp_path):
        """Test parsing a minimal valid TC file."""
        tc_data = self.create_minimal_tc_file()
        tc_file = tmp_path / "test.TC"
        tc_file.write_bytes(tc_data)

        result = parse_tc_file(tc_file)

        assert result.magic == "LSX9"
        assert result.metadata.language == "en.English"
        assert result.metadata.manufacturer == "SUBARU"
        assert len(result.parameters) == 32
        assert result.record_count == 1
        assert len(result.records) == 1

    @pytest.mark.parametrize(
        ("parameter_count", "data_block_offset"),
        [(2, 0x158), (3, 0x168), (12, 0x1F8)],
    )
    def test_parse_lsx8_with_dynamic_data_block_and_record_size(
        self, tmp_path, parameter_count, data_block_offset
    ):
        """LSX8 files use varying column counts and data block offsets."""
        data = bytearray(self.create_minimal_tc_file())
        data[0:4] = b"LSX8"

        record_size = parameter_count * 4
        struct.pack_into("<I", data, 0x12C, data_block_offset)
        struct.pack_into("<I", data, 0x134, record_size)
        struct.pack_into(
            "<IIII",
            data,
            data_block_offset,
            0x00040010,
            0,
            record_size,
            record_size,
        )
        for i in range(parameter_count):
            struct.pack_into(
                "<I",
                data,
                data_block_offset + 16 + i * 4,
                41 + (i % 4),
            )

        tc_file = tmp_path / "lsx8.TC"
        tc_file.write_bytes(data)
        result = parse_tc_file(tc_file)

        assert result.magic == "LSX8"
        assert len(result.parameters) == parameter_count
        assert result.record_count == 1
        assert result.records[0]["Param0"] == "0.00"
        expected_values = ["0.00", "1.00", "ON", "OFF"]
        assert (
            result.records[0][f"Param{parameter_count - 1}"]
            == expected_values[(parameter_count - 1) % 4]
        )

    def test_parse_nonexistent_file(self):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            parse_tc_file("nonexistent.TC")

    def test_parse_invalid_magic(self, tmp_path):
        """Test error on invalid magic signature."""
        tc_file = tmp_path / "invalid.TC"
        tc_file.write_bytes(b"XXXX" + b"\x00" * 1020)

        with pytest.raises(TCParseError, match="Invalid magic"):
            parse_tc_file(tc_file)

    def test_parse_file_too_small(self, tmp_path):
        """Test error on file too small."""
        tc_file = tmp_path / "small.TC"
        tc_file.write_bytes(b"LSX9" + b"\x00" * 100)

        with pytest.raises(TCParseError, match="File too small"):
            parse_tc_file(tc_file)

    def test_parse_invalid_string_table_offset(self, tmp_path):
        """Test error when string table offset is beyond file."""
        data = bytearray(1024)
        data[0:4] = b"LSX9"
        struct.pack_into("<I", data, 0x0C, 0x99999999)  # Invalid offset

        tc_file = tmp_path / "invalid_offset.TC"
        tc_file.write_bytes(data)

        with pytest.raises(TCParseError, match="beyond file size"):
            parse_tc_file(tc_file)


class TestTCData:
    """Test TCData helper methods."""

    def test_get_parameter_values(self):
        """Test extracting values for a specific parameter."""
        records = [
            {"Speed": "10", "Temp": "20"},
            {"Speed": "15", "Temp": "25"},
            {"Speed": "20", "Temp": "30"},
        ]

        data = TCData(
            magic="LSX9",
            metadata=TCMetadata("", "", "", "", "", "", "", ""),
            parameters=["Speed", "Temp"],
            units=[],
            records=records,
            record_count=3,
            string_count=10,
        )

        speeds = data.get_parameter_values("Speed")
        assert speeds == ["10", "15", "20"]

        temps = data.get_parameter_values("Temp")
        assert temps == ["20", "25", "30"]

    def test_get_parameter_values_missing(self):
        """Test extracting values for non-existent parameter."""
        records = [{"Speed": "10"}, {"Speed": "15"}]

        data = TCData(
            magic="LSX9",
            metadata=TCMetadata("", "", "", "", "", "", "", ""),
            parameters=["Speed"],
            units=[],
            records=records,
            record_count=2,
            string_count=5,
        )

        missing = data.get_parameter_values("NonExistent")
        assert missing == ["", ""]
