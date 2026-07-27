"""
Command-line interface for ThinkCar TC to CSV converter.

This module provides the tc2csv command-line tool for converting
ThinkCar .TC diagnostic log files to CSV format.
"""

import argparse
import sys
from pathlib import Path

from . import __version__, export_to_csv, parse_tc_file
from .parser import TCParseError


def main() -> int:
    """Main entry point for the tc2csv command."""
    parser = argparse.ArgumentParser(
        prog="tc2csv",
        description="Convert ThinkCar .TC diagnostic log files to CSV format",
        epilog="Example: tc2csv recording.TC -o output.csv",
    )

    parser.add_argument(
        "input",
        type=str,
        help="Input .TC file to convert",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output CSV file (default: same name as input with .csv extension)",
    )

    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Do not include metadata comments in CSV output",
    )

    parser.add_argument(
        "--no-units",
        action="store_true",
        help="Do not include the parameter unit row in CSV output",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed information during conversion",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # Determine input and output paths
    input_path = Path(args.input)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".csv")

    # Check input file exists
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    if not input_path.is_file():
        print(f"Error: Input path is not a file: {input_path}", file=sys.stderr)
        return 1

    # Warn if output file exists
    if output_path.exists() and args.verbose:
        print(f"Warning: Output file will be overwritten: {output_path}")

    try:
        # Parse TC file
        if args.verbose:
            print(f"Parsing: {input_path}")

        data = parse_tc_file(input_path)

        if args.verbose:
            print(f"  Magic: {data.magic}")
            print(f"  Manufacturer: {data.metadata.manufacturer}")
            print(f"  Timestamp: {data.metadata.timestamp}")
            print(f"  Parameters: {len(data.parameters)}")
            print(f"  Records: {data.record_count}")
            print(f"  Strings: {data.string_count}")
            print(f"  Units: {', '.join(data.units) or '(none)'}")

        # Export to CSV
        if args.verbose:
            print(f"Exporting to: {output_path}")

        export_to_csv(
            data,
            output_path,
            include_metadata=not args.no_metadata,
            include_units=not args.no_units,
        )

        print(f"Successfully converted {data.record_count} records to {output_path}")
        return 0

    except TCParseError as e:
        print(f"Error parsing TC file: {e}", file=sys.stderr)
        return 1

    except IOError as e:
        print(f"Error writing CSV file: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
