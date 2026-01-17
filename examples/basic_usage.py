#!/usr/bin/env python3
"""
Basic usage example for thinkcar_tc_reader library.

This script demonstrates how to:
1. Parse a TC file
2. Access metadata and statistics
3. Extract parameter values
4. Export to CSV
"""

from thinkcar_tc_reader import export_to_csv, parse_tc_file


def main():
    # Path to TC file
    tc_file = "../testdata/SUBARU_9T8P20524415_20260117154318.TC"

    print("=" * 70)
    print("ThinkCar TC Reader - Basic Usage Example")
    print("=" * 70)

    # Parse the TC file
    print(f"\n📂 Parsing file: {tc_file}")
    data = parse_tc_file(tc_file)
    print("✓ Successfully parsed!")

    # Display metadata
    print("\n" + "=" * 70)
    print("METADATA")
    print("=" * 70)
    print(f"Magic Signature:  {data.magic}")
    print(f"Language:         {data.metadata.language}")
    print(f"Timestamp:        {data.metadata.timestamp}")
    print(f"Region:           {data.metadata.region}")
    print(f"Version:          {data.metadata.version}")
    print(f"Manufacturer:     {data.metadata.manufacturer}")
    print(f"Device ID:        {data.metadata.device_id}")
    print(f"Protocol:         {data.metadata.protocol}")
    print(f"Session ID:       {data.metadata.session_id}")

    # Display statistics
    print("\n" + "=" * 70)
    print("STATISTICS")
    print("=" * 70)
    print(f"Number of parameters:  {len(data.parameters)}")
    print(f"Number of records:     {data.record_count}")
    print(f"Total strings:         {data.string_count}")
    print(f"Available units:       {', '.join(data.units)}")

    # Display parameters
    print("\n" + "=" * 70)
    print("PARAMETERS")
    print("=" * 70)
    for i, param in enumerate(data.parameters, 1):
        print(f"  {i:2d}. {param}")

    # Display sample data from first few records
    print("\n" + "=" * 70)
    print("SAMPLE DATA (First 5 Records)")
    print("=" * 70)

    # Show key parameters
    key_params = [
        "Engine Speed",
        "Front Wheel Speed",
        "ATF Temp.",
        "Control module voltage",
        "Accel. Opening Angle",
        "P Range",
        "D Range Signal",
    ]

    for i, record in enumerate(data.records[:5]):
        print(f"\nRecord {i}:")
        for param in key_params:
            if param in record:
                value = record[param]
                print(f"  {param:30s}: {value}")

    # Extract and analyze specific parameter
    print("\n" + "=" * 70)
    print("PARAMETER ANALYSIS")
    print("=" * 70)

    # Get all speed values
    speeds = data.get_parameter_values("Front Wheel Speed")
    speed_floats = [float(s) for s in speeds if s and s != "0.00"]

    if speed_floats:
        print(f"Vehicle Speed:")
        print(f"  Min:     {min(speed_floats):.2f} km/h")
        print(f"  Max:     {max(speed_floats):.2f} km/h")
        print(f"  Average: {sum(speed_floats) / len(speed_floats):.2f} km/h")

    # Get temperature data
    temps = data.get_parameter_values("ATF Temp.")
    temp_floats = [float(t) for t in temps if t]

    if temp_floats:
        print(f"\nATF Temperature:")
        print(f"  Start:   {temp_floats[0]:.2f} °C")
        print(f"  End:     {temp_floats[-1]:.2f} °C")
        print(f"  Max:     {max(temp_floats):.2f} °C")
        print(f"  Range:   {max(temp_floats) - min(temp_floats):.2f} °C")

    # Export to CSV
    print("\n" + "=" * 70)
    print("EXPORT TO CSV")
    print("=" * 70)

    output_csv = "example_output.csv"
    export_to_csv(data, output_csv)
    print(f"✓ Exported to: {output_csv}")
    print(f"  {data.record_count} records written")

    # Export without metadata
    output_csv_no_meta = "example_output_no_metadata.csv"
    export_to_csv(data, output_csv_no_meta, include_metadata=False)
    print(f"✓ Exported to: {output_csv_no_meta} (without metadata)")

    print("\n" + "=" * 70)
    print("✓ Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
