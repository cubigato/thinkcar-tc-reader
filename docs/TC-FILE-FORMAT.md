# ThinkCar .TC File Format Specification

## Overview

The `.TC` file format is a proprietary binary format used by ThinkCar diagnostic devices (ThinkDiag, ThinkScan, ThinkTool) and reseller apps (Kingbolen eDiag, Topdon) to store OBD-II live data recordings.

This document is based on reverse engineering of recordings from a **Subaru
Outback BR (2014)** and a **Topdon Phoenix Lite 2 / Toyota**. Offsets and record
widths shown below are examples; readers must follow the descriptor pointers.

---

## File Structure Summary

| Offset | Size | Description |
|--------|------|-------------|
| 0x0000 | 256 | File Header |
| 0x0100 | 40 | Record Metadata Header |
| variable | 16 | Data Section Descriptor (offset referenced at 0x0118) |
| descriptor + 16 | variable | Parameter Definition Table |
| descriptor field | 16 | Data Block Header |
| data block + 16 | variable | Data Records |
| variable | 16 | String Table Header |
| variable | variable | String Table Entries |

---

## 1. File Header (0x0000 - 0x00FF)

### Magic Number (0x0000)
```
Offset  Size  Description
------  ----  -----------
0x0000  4     Magic: "LSX8" or "LSX9"
```

### Header Fields
```
Offset  Size  Type      Description
------  ----  ----      -----------
0x0004  4     uint32    Version/flags (observed: 0x00140301)
0x0008  4     uint32    Unknown (observed: 0x00000100)
0x000C  4     uint32    String table offset (e.g., 0x68C8)
0x0010  4     uint32    Unknown
0x0014  4     uint32    Unknown
0x0018  4     uint32    Unknown
0x001C  4     uint32    Unknown
0x0020  4     uint32    Unknown
0x0024  16    char[16]  Device Serial Number (null-terminated)
                        Example: "9T8P20524415"
0x0034  ...   ...       Reserved (zeros until 0x0100)
```

---

## 2. Record Metadata Header (0x0100 - 0x0127)

```
Offset  Size  Type      Description
------  ----  ----      -----------
0x0100  2     uint16    Unknown (observed: 0x28 = 40)
0x0102  2     uint16    Unknown (observed: 0x01)
0x0104  4     uint32    String table offset (duplicate, 0x68C8)
0x0108  4     uint32    Data section size (0x67A0 = 26528)
0x010C  4     uint32    Unknown
0x0110  4     uint32    Unknown
0x0114  4     uint32    Unknown
0x0118  4     uint32    Offset to data descriptor (0x0128)
0x011C  4     uint32    Offset to data block (e.g. 0x0338 or 0x01F8)
0x0120  8     ...       Reserved (zeros)
```

---

## 3. Data Section Descriptor (0x0128 - 0x0137)

```
Offset  Size  Type      Description
------  ----  ----      -----------
0x0128  2     uint16    Number of columns/parameters (observed: 16)
0x012A  2     uint16    Unknown (observed: 5)
0x012C  4     uint32    Data block offset (0x0338)
0x0130  4     uint32    Max record count (512, but actual may differ)
0x0134  4     uint32    Record size in bytes (128 = 32 × 4)
```

The value at descriptor offset `+0x04` (normally file offset `0x012C`) points
to the **data block header**, not directly to the first record. Record data
starts 16 bytes after that referenced offset.

---

## 4. Parameter Definition Tables (immediately after descriptor)

The parameter section contains four parallel tables. Each table is one record
wide and contains one 4-byte entry per parameter:

| Relative offset | Observed purpose |
|-----------------|------------------|
| `descriptor + 16` | Parameter-name string indices |
| `descriptor + 16 + record_size` | Parameter-unit string indices |
| `descriptor + 16 + 2 × record_size` | Unknown (all zero in samples) |
| `descriptor + 16 + 3 × record_size` | Unknown (all zero in samples) |

```
Offset  Size  Type      Description
------  ----  ----      -----------
+0x00   2     uint16    Parameter name string index
+0x02   2     uint16    Same as name index (redundant/unused?)
```

The same duplicated-index entry format is used by the unit table. A unit index
of zero means that no unit is assigned. Some devices instead reference a
whitespace-only string, which should also be treated as no unit.

**Note:** Parameter indices reference the String Table. For this sample file:
- Index 9 → "Accel. Opening Angle"
- Index 10 → "Actual Forward && Reverse Linear Solenoid Current"
- Index 11 → "Actual Gear Ratio"
- ... (see String Table section)

**Important:** Parameter 14 appears twice (duplicate entry for "Front Wheel Speed").

---

## 5. Data Block Header (variable offset)

```
Offset  Size  Type      Description
------  ----  ----      -----------
0x0338  4     uint32    Flags/type (observed: 0x00040010)
0x033C  4     uint32    Reserved (0)
0x0340  4     uint32    Data size in bytes (0x6580 = 25984)
0x0344  4     uint32    Record size (0x80 = 128)
```

**Calculated values:**
- Data size / Record size = Number of records
- 25984 / 128 = **203 records**

---

## 6. Data Records (immediately after data block header)

Each data record contains `record size / 4` × `uint32` values. Observed record
sizes include 8 bytes (2 values), 12 bytes (3 values), 48 bytes (12 values),
and 128 bytes (32 values).

Each value is a **string index** into the String Table, pointing to the actual measurement value as a string.

**Important:** 
- String indices in data records are **1-based** (i.e., subtract 1 to get the zero-based array index when parsing).
- Some parameters appear **twice** with the same name but different units/meanings (e.g., "Front Wheel Speed" at columns 13 and 14).

### Record Format
```
Offset  Size  Type      Description
------  ----  ----      -----------
+0x00   4     uint32    Value string index for Parameter 0
+0x04   4     uint32    Value string index for Parameter 1
...
+0x7C   4     uint32    Value string index for Parameter 31
```

### Sample Record Mapping (Verified)
```
Column  Parameter                                    Sample Values
------  -----------------------------------------    -------------
0       Accel. Opening Angle                         "0.00", "4.31" (%)
1       Actual Forward && Reverse Linear Sol. Curr  "1001.00", "806.00" (mA)
2       Actual Gear Ratio                           "2.16", "2.25"
3       Actual Secondary Pressure                    "0.60", "0.94" (MPa)
4       AT learning                                  "Completed"
5       ATF Temp.                                    "9.00" (°C)
6       ATF Temperature Lamp                         "OFF"
7       Commanded Forward && Reverse Linear Sol. C. "1000.00", "802.00" (mA)
8       Control module voltage                       "14.64", "14.67" (V)
9       D Range Signal                               "OFF", "ON"
10      Diagnosis Lamp                               "OFF"
11      Down Switch                                  "OFF"
12      Engine Speed                                 "976.00", "1245.00" (rpm)
13      Front Wheel Speed                            "0.00", "95.00" (km/h) ← Actual vehicle speed!
14      Front Wheel Speed (duplicate)                "0.00", "3165.00" (rpm?) ← Wheel sensor pulses/rpm
15      Lock Up Duty Ratio                           "0.00" (%)
16      Lock-Up ON/OFF Solenoid                      "OFF"
17      Manual Mode Switch                           "OFF"
18      N Range                                      "OFF"
19      P Range                                      "ON", "OFF"
20      Primary DOWN Duty                            "34.80", "0.00" (%)
21      Primary Rev Speed                            "821.00", "851.00" (rpm)
22      Primary UP Duty                              "0.00", "47.60" (%)
23      R Range Signal                               "OFF"
24      Secondary Actual Current                     "768.00", "721.00" (mA)
25      Secondary Rev Speed                          "386.00", "353.00" (rpm)
26      Secondary Set Current                        "767.00", "718.00" (mA)
27      Shift step in Manu. Mode                     "0.00"
28      Stop Light Switch                            "OFF"
29      Transfer Duty Ratio                          "0.00", "32.00" (%)
30      Turbine Revolution Speed                     "928.00", "832.00" (rpm)
31      Up Switch                                    "OFF"
```

---

## 7. String Table

Located at offset specified in header (e.g., 0x68C8).

### String Table Header (16 bytes)
```
Offset  Size  Type      Description
------  ----  ----      -----------
+0x00   2     uint16    Type (observed: 0x10)
+0x02   2     uint16    Flags (observed: 0x02)
+0x04   4     uint32    Reserved (0)
+0x08   4     uint32    Total string data size (e.g., 12453)
+0x0C   4     uint32    String count (e.g., 1334)
```

### String Entry Format
Each string is stored as:
```
+0x00   2     uint16    Total entry size (including this field)
+0x02   L-2   char[]    String data followed by null terminator
```

`L` is the total entry size, including the 2-byte length field and the null
terminator. For example, the `%` entry is `04 00 25 00`: total size 4, followed
immediately by the next entry.

### String Table Organization

| Index (1-based) | Content Type | Example |
|-----------------|--------------|---------|
| 1 | Language | "en.English" |
| 2 | Timestamp | "Sat Jan 17 15:43:18 2026" |
| 3 | Region | "DE.DE" |
| 4 | Version | "1.0" |
| 5 | Manufacturer | "SUBARU" |
| 6 | Device Serial/VIN | "12345678976543210" |
| 7 | Protocol | "Canbus" |
| 8 | Session ID | "20260117154318" |
| 9-39 | Parameter Names | "Accel. Opening Angle", etc. |
| 40-46 | Units | "%", "mA", "MPa", "degree C", "V", "rpm", "km/h" |
| 47+ | Measurement Values | "0.00", "1001.00", "ON", "OFF", "Completed", etc. |

**Note:** All indices in the file are 1-based. When using a zero-based array, subtract 1 from the stored index.

---

## 8. Observed Parameters (Sample File)

| Index | Parameter Name | Unit |
|-------|----------------|------|
| 8 | Accel. Opening Angle | % |
| 9 | Actual Forward && Reverse Linear Solenoid Current | mA |
| 10 | Actual Gear Ratio | ratio |
| 11 | Actual Secondary Pressure | MPa |
| 12 | AT learning | Status |
| 13 | ATF Temp. | degree C |
| 14 | ATF Temperature Lamp | ON/OFF |
| 15 | Commanded Forward && Reverse Linear Solenoid Current | mA |
| 16 | Control module voltage | V |
| 17 | D Range Signal | ON/OFF |
| 18 | Diagnosis Lamp | ON/OFF |
| 19 | Down Switch | ON/OFF |
| 20 | Engine Speed | rpm |
| 21 | Front Wheel Speed | km/h (actual speed) |
| 22 | Lock Up Duty Ratio | % |
| 23 | Lock-Up ON/OFF Solenoid | ON/OFF |
| 24 | Manual Mode Switch | ON/OFF |
| 25 | N Range | ON/OFF |
| 26 | P Range | ON/OFF |
| 27 | Primary DOWN Duty | % |
| 28 | Primary Rev Speed | rpm |
| 29 | Primary UP Duty | % |
| 30 | R Range Signal | ON/OFF |
| 31 | Secondary Actual Current | mA |
| 32 | Secondary Rev Speed | rpm |
| 33 | Secondary Set Current | mA |
| 34 | Shift step in Manu. Mode | - |
| 35 | Stop Light Switch | ON/OFF |
| 36 | Transfer Duty Ratio | % |
| 37 | Turbine Revolution Speed | rpm |
| 38 | Up Switch | ON/OFF |

---

## 9. Sample File Statistics

| Property | Value |
|----------|-------|
| File Size | 39,293 bytes |
| Magic | LSX9 |
| String Table Offset | 0x68C8 |
| Data Block Offset | 0x0348 |
| Record Size | 128 bytes |
| Record Count | 203 (~4.4s per sample) |
| Parameters per Record | 32 (indices) |
| Total Strings | 1,334 |
| Parameter Names | 31 (but 32 columns due to 1 duplicate) |
| Units | 7 |
| Value Strings | ~1,288 |
| Recording Duration | ~15 minutes |
| Max Speed Observed | 95 km/h |
| ATF Temp Range | 9°C → 27°C |

---

## 10. Data Types

All multi-byte integers are **Little-Endian**.

| Type | Size | Description |
|------|------|-------------|
| uint16 | 2 bytes | Unsigned 16-bit integer (LE) |
| uint32 | 4 bytes | Unsigned 32-bit integer (LE) |
| char[] | variable | Null-terminated ASCII/UTF-8 string |

---

## 11. Parsing Algorithm (Pseudocode)

```python
def parse_tc_file(data):
    # 1. Verify magic
    assert data[0:4] in (b'LSX8', b'LSX9')
    
    # 2. Get string table offset
    string_table_offset = read_uint32(data, 0x0C)
    
    # 3. Parse string table (with index 0 as placeholder for 1-based indexing)
    strings = ['']  # Placeholder at index 0
    strings.extend(parse_string_table(data, string_table_offset + 16))
    
    # 4. Follow the data descriptor and block pointers
    descriptor_offset = read_uint32(data, 0x118)
    data_block_offset = read_uint32(data, descriptor_offset + 4)
    data_offset = data_block_offset + 16
    record_size = read_uint32(data, data_block_offset + 12)
    data_size = read_uint32(data, data_block_offset + 8)
    record_count = data_size // record_size
    
    # 5. Parse one parameter definition per uint32 record value
    params = []
    parameter_count = record_size // 4
    parameter_table_offset = descriptor_offset + 16
    for i in range(parameter_count):
        name_idx = read_uint16(data, parameter_table_offset + i*4)
        params.append(strings[name_idx])  # Direct index (1-based)

    # 6. Parse the parallel parameter-unit table
    parameter_units = []
    unit_table_offset = parameter_table_offset + record_size
    for i in range(parameter_count):
        unit_idx = read_uint16(data, unit_table_offset + i*4)
        unit = strings[unit_idx].strip() if unit_idx else ''
        parameter_units.append(unit)
    
    # 7. Parse data records
    records = []
    for r in range(record_count):
        offset = data_offset + r * record_size
        values = []
        for c in range(parameter_count):
            idx = read_uint32(data, offset + c*4)
            values.append(strings[idx])  # Direct index (1-based)
        records.append(values)
    
    return {
        'metadata': strings[1:9],      # Indices 1-8
        'parameters': params,           # From definition table
        'parameter_units': parameter_units,
        'units': list(dict.fromkeys(u for u in parameter_units if u)),
        'records': records
    }

def parse_string_table(data, pos):
    """Parse length-prefixed null-terminated strings."""
    strings = []
    while pos + 2 <= len(data):
        length = read_uint16(data, pos)
        if length == 0 or length < 3 or length > 500:
            break
        entry_end = pos + length
        if entry_end > len(data) or data[entry_end - 1] != 0:
            break
        strings.append(data[pos + 2:entry_end - 1].decode('utf-8'))
        pos = entry_end
    return strings
```

---

## 12. Known Limitations

1. **No official documentation** - Format derived from reverse engineering
2. **Version variations** - Different ThinkCar app versions may use slightly different formats
3. **Timestamp per record** - No visible per-record timestamp; timing inferred from record count and session duration
4. **Remaining parameter tables** - The third and fourth parallel tables are
   all zero in known samples, so their purpose is unknown

---

## 13. Related Formats

The ThinkCar `.TC` format appears similar to:
- **Launch X-431 `.x431`** log files (same parent company technology)
- May share structural elements with other Chinese OBD-II diagnostic tools

---

## 14. Verified Data Observations

Sample data from the ~15 minute test drive on German country roads shows plausible values:

| Parameter | Start (cold) | During drive | End |
|-----------|--------------|--------------|-----|
| **Vehicle Speed** (col 13) | 0 km/h | 66-95 km/h | 0 km/h |
| **Engine Speed** | ~976 rpm (idle) | 1000-2200 rpm | ~977 rpm |
| **Gear Ratio** | 2.16 (neutral) | 0.38-0.89 (high gear) | 2.12 |
| **ATF Temperature** | 9°C | 10-27°C (warming up) | 27°C |
| **P Range** | ON | OFF | ON |
| **D Range** | OFF | ON | OFF |
| **Transfer Duty** | 0% | 18-54% (AWD active) | 40% |
| **Control Voltage** | 14.64V | 14.53-14.72V | ~14.6V |

**Key observations:**
- Vehicle starts in P-Range, shifts to D-Range for driving, returns to P at end
- Maximum speed reached: **~95 km/h** (plausible for country roads)
- ATF temperature rises from 9°C to 27°C during the drive (normal warm-up)
- CVT gear ratio changes smoothly from ~2.2 (low) to ~0.4 (high)
- AWD Transfer Duty activates during driving (18-54%)

**Important:** Column 13 ("Front Wheel Speed") contains the **actual vehicle speed in km/h**.
Column 14 (also named "Front Wheel Speed") contains different data (~0-3165), likely wheel sensor pulses or rpm.

---

## Document History

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2025-01 | Initial reverse engineering from Subaru TCM sample |
| 1.1 | 2025-01 | Corrected string index offset (1-based), verified data mapping |

---

## References

- Sample file: `SUBARU_9T8P20524415_20260117154318.TC`
- Vehicle: Subaru Outback BR, 2014
- ECU: TCM (Transmission Control Module)
- Recording: ~15 minute test drive
