# Examples

This directory contains example scripts demonstrating how to use the ThinkCar TC Reader library.

## Available Examples

### basic_usage.py

Complete usage example demonstrating the library's main features:
- Parsing TC files with `parse_tc_file()`
- Accessing metadata and statistics
- Iterating through records
- Extracting specific parameter values
- Exporting to CSV with `export_to_csv()`

**Usage:**
```bash
cd examples
python basic_usage.py
```

This example uses the sample file from `../testdata/SUBARU_9T8P20524415_20260117154318.TC`.

**Output:**
- Displays metadata (timestamp, manufacturer, device info)
- Shows all 32 parameters
- Prints sample data from first 5 records
- Analyzes speed and temperature ranges
- Exports to CSV files (with and without metadata)

### parse_tc_example.py

Reference implementation showing low-level parsing of TC files without using the library. This demonstrates the binary file format parsing approach and serves as documentation for how the TC format works internally.

**Usage:**
```bash
cd examples
python parse_tc_example.py <path-to-tc-file>
python parse_tc_example.py ../testdata/SUBARU_9T8P20524415_20260117154318.TC
```

**Optional CSV export:**
```bash
python parse_tc_example.py ../testdata/SUBARU_9T8P20524415_20260117154318.TC --csv
```

**Note:** This is primarily for educational purposes. For production use, prefer the `thinkcar_tc_reader` library instead.

## Quick Start

For most use cases, start with `basic_usage.py` to understand the library API:

```python
from thinkcar_tc_reader import parse_tc_file, export_to_csv

# Parse a TC file
data = parse_tc_file("path/to/file.TC")

# Access data
print(f"Manufacturer: {data.metadata.manufacturer}")
print(f"Records: {data.record_count}")

# Export to CSV
export_to_csv(data, "output.csv")
```

## Related Documentation

- [Main README](../README.md) - Installation and API documentation
- [TC File Format Spec](../docs/TC-FILE-FORMAT.md) - Binary format specification
- [Test Data](../testdata/README.md) - Sample files for testing