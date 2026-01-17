# ThinkCar TC Reader

A Python library and command-line tool for reading and converting ThinkCar `.TC` diagnostic log files to CSV format.

## Overview

ThinkCar diagnostic devices (ThinkDiag, ThinkScan, ThinkTool) and reseller apps (Kingbolen eDiag, Topdon) record OBD-II live data in a proprietary binary format with the `.TC` extension. This library provides tools to parse these files and export the data to CSV for analysis.

The TC file format has been reverse-engineered and documented in [`docs/TC-FILE-FORMAT.md`](docs/TC-FILE-FORMAT.md).

## Features

- **Parse TC files**: Read binary TC files and extract structured data
- **Export to CSV**: Convert TC data to CSV format with proper handling of duplicate columns
- **Command-line tool**: Simple `tc2csv` command for quick conversions
- **Python API**: Library for programmatic access to TC file data
- **Metadata preservation**: Extract and preserve recording metadata (timestamp, device info, etc.)

## Installation

### Using uv (recommended)

This project uses `uv` for package management with a Python virtual environment:

```bash
# Clone the repository
git clone <repository-url>
cd thinkcar-tc-reader

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Using pip

```bash
pip install -e .
```

### Development Installation

To install with development dependencies (pytest, etc.):

```bash
uv pip install -e ".[dev]"
```

## Usage

### Command-Line Tool

Convert a TC file to CSV:

```bash
tc2csv recording.TC
```

Specify output file:

```bash
tc2csv recording.TC -o output.csv
```

Verbose output with details:

```bash
tc2csv recording.TC -v
```

Exclude metadata comments from CSV:

```bash
tc2csv recording.TC --no-metadata
```

### Python API

#### Parse a TC file

```python
from thinkcar_tc_reader import parse_tc_file

# Parse the file
data = parse_tc_file("testdata/SUBARU_9T8P20524415_20260117154318.TC")

# Access metadata
print(f"Manufacturer: {data.metadata.manufacturer}")
print(f"Timestamp: {data.metadata.timestamp}")
print(f"Device ID: {data.metadata.device_id}")

# Access parameters
print(f"Parameters: {data.parameters}")
print(f"Record count: {data.record_count}")

# Access records
for i, record in enumerate(data.records[:5]):
    print(f"Record {i}: {record}")
```

#### Export to CSV

```python
from thinkcar_tc_reader import parse_tc_file, export_to_csv

# Parse and export
data = parse_tc_file("recording.TC")
export_to_csv(data, "output.csv")

# Export without metadata comments
export_to_csv(data, "output.csv", include_metadata=False)
```

#### Extract specific parameter values

```python
from thinkcar_tc_reader import parse_tc_file

data = parse_tc_file("recording.TC")

# Get all values for a specific parameter
speeds = data.get_parameter_values("Front Wheel Speed")
temps = data.get_parameter_values("ATF Temp.")

print(f"Max speed: {max(speeds)}")
print(f"Temp range: {min(temps)} - {max(temps)}")
```

## File Format

The ThinkCar `.TC` format is a binary format with the following characteristics:

- **Magic signature**: `LSX9`
- **String table architecture**: All values stored as string references
- **1-based indexing**: String indices start at 1 (not 0)
- **32 parameters per record**: Fixed record size of 128 bytes (32 × uint32)
- **Little-endian encoding**: All multi-byte integers are little-endian

For complete format specification, see [`docs/TC-FILE-FORMAT.md`](docs/TC-FILE-FORMAT.md).

## Testing

Run the test suite with pytest:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=src/thinkcar_tc_reader --cov-report=html
```

## Project Structure

```
thinkcar-tc-reader/
├── src/
│   └── thinkcar_tc_reader/
│       ├── __init__.py       # Public API
│       ├── parser.py         # TC file parser
│       ├── exporter.py       # CSV exporter
│       └── cli.py            # Command-line interface
├── tests/
│   ├── test_parser.py        # Parser tests
│   └── test_exporter.py      # Exporter tests
├── examples/
│   ├── basic_usage.py        # API usage example
│   └── parse_tc_example.py   # Reference parser implementation
├── docs/
│   ├── TC-FILE-FORMAT.md     # File format specification
│   ├── IMPLEMENTATION.md     # Implementation summary
│   ├── AGENTS.md             # Development guidelines
│   └── archive/
│       └── tc-file-info.md   # Historical research notes
├── testdata/
│   ├── SUBARU_*.TC           # Sample TC file
│   └── SUBARU_*.csv          # Sample CSV output
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Known Limitations

1. **Reverse-engineered format**: The TC format has been reverse-engineered and may contain errors or omissions
2. **Version variations**: Different ThinkCar app versions may use slightly different formats
3. **No timestamp per record**: Individual record timestamps are not stored in the format
4. **Parameter-unit mapping**: Units must be inferred from parameter names as there's no explicit mapping

## Example Data

The repository includes a sample file from a Subaru Outback BR (2014) TCM recording in the `testdata/` directory:

- File: `testdata/SUBARU_9T8P20524415_20260117154318.TC`
- Duration: ~15 minutes of driving data
- Records: 203 data points
- Parameters: 32 (Engine Speed, ATF Temp, Vehicle Speed, Gear Ratio, etc.)

## Contributing

Contributions are welcome! Please ensure:

- Code follows existing style conventions
- Tests pass (`pytest`)
- New features include tests
- Documentation is updated

## License

MIT License - see LICENSE file for details

## Related Files

- [`docs/TC-FILE-FORMAT.md`](docs/TC-FILE-FORMAT.md) - Complete file format specification
- [`docs/AGENTS.md`](docs/AGENTS.md) - Development guidelines and architecture notes
- [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) - Implementation summary
- [`examples/parse_tc_example.py`](examples/parse_tc_example.py) - Reference implementation (working parser)