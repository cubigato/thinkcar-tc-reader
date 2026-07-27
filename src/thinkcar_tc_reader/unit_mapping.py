"""Known parameter units used as fallbacks for incomplete TC files."""

from collections import defaultdict


# Values are tuples because the same parameter name can occur in multiple
# columns with different units. The tuple order follows the column occurrence.
KNOWN_PARAMETER_UNITS: dict[str, tuple[str, ...]] = {
    "Accel. Opening Angle": ("%",),
    "Accelerator Pedal Position": ("%",),
    "Actual Forward && Reverse Linear Solenoid Current": ("mA",),
    "Actual Secondary Pressure": ("MPa",),
    "Air Mixer Position Sensor Voltage": ("V",),
    "Air Temperature At The Air Flow Sensor": ("degree C",),
    "ATF Temp.": ("degree C",),
    "Commanded Forward && Reverse Linear Solenoid Current": ("mA",),
    "Comp Power Supply Voltage": ("V",),
    "Control module voltage": ("V",),
    "EGR Valve Position Signal Voltage": ("V",),
    "Engine Coolant Temperature": ("degree C",),
    "Engine RPM": ("rpm",),
    "Engine Speed": ("rpm",),
    "Exterior Air Temperature": ("degree C",),
    "Front Wheel Speed": ("km/h", "rpm"),
    "Lock Up Duty Ratio": ("%",),
    "Oxygen Sensor Output Voltage B1S1": ("V",),
    "Oxygen Sensor Output Voltage B1S2": ("V",),
    "Primary DOWN Duty": ("%",),
    "Primary Rev Speed": ("rpm",),
    "Primary UP Duty": ("%",),
    "Secondary Actual Current": ("mA",),
    "Secondary Rev Speed": ("rpm",),
    "Secondary Set Current": ("mA",),
    "Temperature Of The Fuel": ("degree C",),
    "Temperature Upstream Of The Turbine": ("degree C",),
    "Transfer Duty Ratio": ("%",),
    "Turbine Revolution Speed": ("rpm",),
    "Turbocharging Inlet Air Temperature": ("degree C",),
    "Voltage Of The Turbocharger Position Signal": ("V",),
}


def apply_known_unit_fallbacks(
    parameters: list[str], parameter_units: list[str]
) -> list[str]:
    """
    Fill missing units from known parameter-to-unit associations.

    Units encoded in the TC file always take precedence. Duplicate parameter
    names are resolved by their occurrence order.
    """
    if len(parameters) != len(parameter_units):
        raise ValueError("parameters and parameter_units must have the same length")

    result = [unit.strip() for unit in parameter_units]
    occurrences: defaultdict[str, int] = defaultdict(int)

    for column, parameter in enumerate(parameters):
        occurrence = occurrences[parameter]
        occurrences[parameter] += 1

        if result[column]:
            continue

        known_units = KNOWN_PARAMETER_UNITS.get(parameter)
        if not known_units:
            continue

        if len(known_units) == 1:
            result[column] = known_units[0]
        elif occurrence < len(known_units):
            result[column] = known_units[occurrence]

    return result
