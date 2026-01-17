"""
ThinkCar TC Reader - Python library for reading ThinkCar .TC diagnostic log files.

This library provides functionality to parse and extract data from ThinkCar diagnostic
devices (ThinkDiag, ThinkScan, ThinkTool) log files in the proprietary .TC format.

Basic usage:
    >>> from thinkcar_tc_reader import parse_tc_file
    >>> data = parse_tc_file("recording.TC")
    >>> print(data.metadata)
    >>> for record in data.records:
    ...     print(record)

Export to CSV:
    >>> from thinkcar_tc_reader import parse_tc_file, export_to_csv
    >>> data = parse_tc_file("recording.TC")
    >>> export_to_csv(data, "output.csv")
"""

from .exporter import export_to_csv
from .parser import TCData, parse_tc_file

__version__ = "0.1.0"
__all__ = ["parse_tc_file", "export_to_csv", "TCData"]
