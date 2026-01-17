# INTRO
Always read the README.md file before editing this repo.

# ARCHITECTURE
- python library to read ThinkCar TC files
- small tool using this library to convert .TC to .CSV files
- uv for package management but with python venv
- packaging with pyproject.toml
- pytest for testing (don't overuse tests)

# TC FILE FORMAT

The ThinkCar .TC file format has been **reverse-engineered** and documented in:
→ **`TC-FILE-FORMAT.md`** ← PRIMARY SPECIFICATION

This is the source for the file format. It includes:
- Complete binary structure (headers, data blocks, string table)
- Magic signature: `LSX9`
- All offsets, data types, and field meanings
- Parsing algorithm with pseudocode
- Verified against real-world Subaru Outback BR TCM recording data

The spec might still contain errors or omissions as it is a reverse-engineered format.

A working reference implementation is provided:
→ **`example_parse_tc.py`** ← WORKING PARSER

Key format characteristics:
- Binary format with string table architecture
- All measured values stored as string references (not raw numbers)
- String indices are 1-based (index 0 is placeholder)
- 32 parameters per record × 128 bytes per record
- Parameters defined in table at offset 0x138
- Data records start at offset 0x348
- String table at variable offset (specified in header at 0x0C)

The format has been validated with real driving data showing:
- Plausible speeds (0-100 km/h), temperatures (9-27°C), voltages (14.5-14.7V)
- Correct gear selector states (P/R/N/D transitions)
- CVT operation patterns matching expected behavior

Historical note: `tc-file-info.md` contains early research notes (mostly speculation). 
**It has been superseded by TC-FILE-FORMAT.md and can be ignored.**
