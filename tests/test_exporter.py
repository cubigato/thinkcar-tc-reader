"""
Tests for the CSV exporter module.
"""

import csv
from pathlib import Path

import pytest

from thinkcar_tc_reader.exporter import (
    _make_unique_headers,
    _write_metadata_header,
    export_to_csv,
)
from thinkcar_tc_reader.parser import TCData, TCMetadata


class TestMakeUniqueHeaders:
    """Test header uniqueness helper."""

    def test_no_duplicates(self):
        """Test headers with no duplicates remain unchanged."""
        params = ["Speed", "Temp", "Voltage"]
        result = _make_unique_headers(params)
        assert result == ["Speed", "Temp", "Voltage"]

    def test_with_duplicates(self):
        """Test duplicate headers get numbered."""
        params = ["Speed", "Temp", "Speed"]
        result = _make_unique_headers(params)
        assert result == ["Speed", "Temp", "Speed (2)"]

    def test_multiple_duplicates(self):
        """Test multiple duplicates get sequential numbers."""
        params = ["Speed", "Speed", "Temp", "Speed"]
        result = _make_unique_headers(params)
        assert result == ["Speed", "Speed (2)", "Temp", "Speed (3)"]

    def test_empty_list(self):
        """Test empty parameter list."""
        params = []
        result = _make_unique_headers(params)
        assert result == []


class TestWriteMetadataHeader:
    """Test metadata header writing."""

    def test_write_metadata_header(self, tmp_path):
        """Test metadata is written as CSV comments."""
        csv_file = tmp_path / "test.csv"

        metadata = TCMetadata(
            language="en.English",
            timestamp="Mon Jan 01 12:00:00 2024",
            region="US.US",
            version="1.0",
            manufacturer="SUBARU",
            device_id="12345678",
            protocol="Canbus",
            session_id="20240101120000",
        )

        data = TCData(
            magic="LSX9",
            metadata=metadata,
            parameters=["Speed", "Temp"],
            units=["%", "degree C"],
            records=[],
            record_count=0,
            string_count=10,
        )

        with open(csv_file, "w") as f:
            _write_metadata_header(f, data)

        content = csv_file.read_text()

        # Check for expected metadata lines
        assert "# ThinkCar TC File Export" in content
        assert "# Magic: LSX9" in content
        assert "#   Language: en.English" in content
        assert "#   Manufacturer: SUBARU" in content
        assert "#   Device ID: 12345678" in content
        assert "# Units: %, degree C" in content


class TestExportToCSV:
    """Test CSV export functionality."""

    def create_test_data(self) -> TCData:
        """Create test TCData for export tests."""
        metadata = TCMetadata(
            language="en.English",
            timestamp="Mon Jan 01 12:00:00 2024",
            region="US.US",
            version="1.0",
            manufacturer="SUBARU",
            device_id="12345678",
            protocol="Canbus",
            session_id="20240101120000",
        )

        parameters = ["Speed", "Temp", "Voltage"]
        records = [
            {"Speed": "10", "Temp": "20", "Voltage": "14.5"},
            {"Speed": "15", "Temp": "25", "Voltage": "14.6"},
            {"Speed": "20", "Temp": "30", "Voltage": "14.7"},
        ]

        return TCData(
            magic="LSX9",
            metadata=metadata,
            parameters=parameters,
            units=["km/h", "degree C", "V"],
            records=records,
            record_count=3,
            string_count=20,
        )

    def test_export_basic(self, tmp_path):
        """Test basic CSV export."""
        data = self.create_test_data()
        csv_file = tmp_path / "output.csv"

        export_to_csv(data, csv_file, include_metadata=False)

        assert csv_file.exists()

        # Read and verify CSV content
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Check header
        assert rows[0] == ["Record", "Speed", "Temp", "Voltage"]

        # Check data rows
        assert rows[1] == ["0", "10", "20", "14.5"]
        assert rows[2] == ["1", "15", "25", "14.6"]
        assert rows[3] == ["2", "20", "30", "14.7"]

    def test_export_with_metadata(self, tmp_path):
        """Test CSV export includes metadata comments."""
        data = self.create_test_data()
        csv_file = tmp_path / "output.csv"

        export_to_csv(data, csv_file, include_metadata=True)

        content = csv_file.read_text()

        # Check for metadata
        assert "# ThinkCar TC File Export" in content
        assert "# Magic: LSX9" in content
        assert "#   Manufacturer: SUBARU" in content

        # Check CSV data still present
        assert "Record,Speed,Temp,Voltage" in content

    def test_export_with_duplicate_columns(self, tmp_path):
        """Test export handles duplicate column names."""
        metadata = TCMetadata("", "", "", "", "", "", "", "")

        parameters = ["Speed", "Temp", "Speed"]  # Duplicate
        records = [
            {"Speed": "10", "Temp": "20"},  # Will use first Speed
            {"Speed": "15", "Temp": "25"},
        ]

        data = TCData(
            magic="LSX9",
            metadata=metadata,
            parameters=parameters,
            units=[],
            records=records,
            record_count=2,
            string_count=10,
        )

        csv_file = tmp_path / "output.csv"
        export_to_csv(data, csv_file, include_metadata=False)

        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Check duplicate column is renamed
        assert rows[0] == ["Record", "Speed", "Temp", "Speed (2)"]

    def test_export_with_missing_values(self, tmp_path):
        """Test export handles missing parameter values."""
        metadata = TCMetadata("", "", "", "", "", "", "", "")

        parameters = ["Speed", "Temp", "Voltage"]
        records = [
            {"Speed": "10", "Temp": "20"},  # Missing Voltage
            {"Speed": "15", "Voltage": "14.6"},  # Missing Temp
        ]

        data = TCData(
            magic="LSX9",
            metadata=metadata,
            parameters=parameters,
            units=[],
            records=records,
            record_count=2,
            string_count=10,
        )

        csv_file = tmp_path / "output.csv"
        export_to_csv(data, csv_file, include_metadata=False)

        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Missing values should be empty strings
        assert rows[1] == ["0", "10", "20", ""]
        assert rows[2] == ["1", "15", "", "14.6"]

    def test_export_empty_records(self, tmp_path):
        """Test export with no records."""
        metadata = TCMetadata("", "", "", "", "", "", "", "")

        data = TCData(
            magic="LSX9",
            metadata=metadata,
            parameters=["Speed", "Temp"],
            units=[],
            records=[],
            record_count=0,
            string_count=5,
        )

        csv_file = tmp_path / "output.csv"
        export_to_csv(data, csv_file, include_metadata=False)

        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Only header, no data rows
        assert len(rows) == 1
        assert rows[0] == ["Record", "Speed", "Temp"]

    def test_export_path_as_string(self, tmp_path):
        """Test export accepts string path."""
        data = self.create_test_data()
        csv_file = str(tmp_path / "output.csv")

        export_to_csv(data, csv_file, include_metadata=False)

        assert Path(csv_file).exists()

    def test_export_utf8_content(self, tmp_path):
        """Test export handles UTF-8 characters."""
        metadata = TCMetadata("", "", "", "", "", "", "", "")

        parameters = ["Param", "Wert"]  # German
        records = [{"Param": "Geschwindigkeit", "Wert": "äöü"}]

        data = TCData(
            magic="LSX9",
            metadata=metadata,
            parameters=parameters,
            units=[],
            records=records,
            record_count=1,
            string_count=5,
        )

        csv_file = tmp_path / "output.csv"
        export_to_csv(data, csv_file, include_metadata=False)

        # Read with UTF-8 encoding
        with open(csv_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Geschwindigkeit" in content
        assert "äöü" in content
