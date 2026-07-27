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

By default, the CSV contains a positional unit row directly below the column
headers:

```csv
Record,Accelerator Pedal Position,Comp Power Supply Voltage,Engine Speed
Unit,%,V,rpm
0,0.00,14.34,873.00
```

Exclude this row for compatibility with consumers that expect exactly one
header row:

```bash
tc2csv recording.TC --no-units
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
print(f"Parameter units: {data.parameter_units}")
print(f"Record count: {data.record_count}")

# Access records
for i, record in enumerate(data.records[:5]):
    print(f"Record {i}: {record}")
```

#### Read and adjust parameter units

`parameters` and `parameter_units` are positional lists of the same length.
The unit at a given column therefore belongs to the parameter at that column:

```python
for column, (parameter, unit) in enumerate(
    zip(data.parameters, data.parameter_units, strict=True)
):
    print(column, parameter, unit or "(no unit)")
```

The association is read directly from the parallel unit-index table in the TC
file. A zero index or a whitespace-only unit becomes an empty string. `units`
contains the unique non-empty units in their first-seen order.

If an embedded unit is empty, the parser consults
`KNOWN_PARAMETER_UNITS`. Embedded units always take precedence. The central
mapping contains all non-empty associations observed in the current Subaru,
Toyota, Nissan, and EOBD/OBD-II samples.

The known fallback associations are:

| Unit | Parameters |
|------|------------|
| `%` | Accel. Opening Angle; Accelerator Pedal Position; Lock Up Duty Ratio; Primary DOWN Duty; Primary UP Duty; Transfer Duty Ratio |
| `mA` | Actual Forward && Reverse Linear Solenoid Current; Commanded Forward && Reverse Linear Solenoid Current; Secondary Actual Current; Secondary Set Current |
| `MPa` | Actual Secondary Pressure |
| `degree C` | Air Temperature At The Air Flow Sensor; ATF Temp.; Engine Coolant Temperature; Exterior Air Temperature; Temperature Of The Fuel; Temperature Upstream Of The Turbine; Turbocharging Inlet Air Temperature |
| `V` | Air Mixer Position Sensor Voltage; Comp Power Supply Voltage; Control module voltage; EGR Valve Position Signal Voltage; Oxygen Sensor Output Voltage B1S1; Oxygen Sensor Output Voltage B1S2; Voltage Of The Turbocharger Position Signal |
| `rpm` | Engine RPM; Engine Speed; Primary Rev Speed; Secondary Rev Speed; Turbine Revolution Speed |
| `km/h`, `rpm` | First and second occurrence of Front Wheel Speed |

If a device omits a unit or an application needs a different display notation,
override it by column:

```python
# Use the column index because TC files may contain duplicate parameter names.
data.set_parameter_unit(4, "°C")
data.set_parameter_unit(6, "km/h")

assert data.parameter_units[4] == "°C"
print(data.units)  # Automatically refreshed after an override
```

To maintain an application-specific mapping, apply overrides after parsing:

```python
unit_overrides = {
    "Engine Coolant Temperature": "°C",
    "Vehicle Speed": "km/h",
}

for column, parameter in enumerate(data.parameters):
    if parameter in unit_overrides:
        data.set_parameter_unit(column, unit_overrides[parameter])
```

Name-based overrides affect every matching column. Use explicit column indices
when duplicate names require different units.

To extend the parser-wide fallback mapping for another device, register the
exact parameter name before parsing:

```python
from thinkcar_tc_reader import KNOWN_PARAMETER_UNITS, parse_tc_file

KNOWN_PARAMETER_UNITS["Boost Pressure"] = ("kPa",)

# Multiple entries describe duplicate columns in occurrence order.
KNOWN_PARAMETER_UNITS["Wheel Speed"] = ("km/h", "rpm")

data = parse_tc_file("recording.TC")
```

Fallbacks only fill empty unit fields; they never replace a unit encoded in the
TC file. Application-only display changes should continue to use
`data.set_parameter_unit()`.

#### Export to CSV

```python
from thinkcar_tc_reader import parse_tc_file, export_to_csv

# Parse and export
data = parse_tc_file("recording.TC")
export_to_csv(data, "output.csv")

# Export without metadata comments
export_to_csv(data, "output.csv", include_metadata=False)

# Export without the positional unit row
export_to_csv(data, "output.csv", include_units=False)
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

- **Magic signatures**: `LSX8` and `LSX9`
- **String table architecture**: All values stored as string references
- **1-based indexing**: String indices start at 1 (not 0)
- **Variable record width**: The descriptor defines the data-block offset and
  record size (observed: 2, 3, 12 or 32 parameters)
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
4. **Incomplete metadata**: A parameter can explicitly have no unit, and the
   purpose of the two remaining parallel parameter tables is still unknown

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

Apache License 2.0 - see LICENSE file for details

## Related Files

- [`docs/TC-FILE-FORMAT.md`](docs/TC-FILE-FORMAT.md) - Complete file format specification
- [`docs/AGENTS.md`](docs/AGENTS.md) - Development guidelines and architecture notes
- [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) - Implementation summary
- [`examples/parse_tc_example.py`](examples/parse_tc_example.py) - Reference implementation (working parser)
