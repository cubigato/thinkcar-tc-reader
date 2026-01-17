# Technical Report: ThinkCar / Kingbolen **.TC File Format**

## Executive Summary

The **.TC file format** is a proprietary binary format for storing diagnostic recordings (live data, fault codes, metadata) from ThinkCar diagnostic devices and reseller apps such as **Kingbolen eDiag** or **Topdon**.  
There is **no official specification**. However, public information, forum reports, and indirect sources consistently show that `.tc` files are structured, presumably compressed, and possibly lightly obfuscated binary containers containing header metadata (VIN, time, device), live data time series, and optional additional content (reports, screenshots).

The format is functionally comparable to **Launch X-431 (.x431)** log files. Reverse engineering is realistic and has already been implemented commercially (e.g., FCD Log Decoder).  
For a Python implementation, a systematic approach consisting of hex analysis, pattern recognition, possible decompression, and correlation with known OBD-II PIDs is recommended.

---

## 1. General Description and Usage

- `.tc` is used by **ThinkCar** devices (ThinkDiag, ThinkScan, ThinkTool) and resellers (Kingbolen eDiag, partly Topdon)
- Purpose: Storage of complete **diagnostic sessions**
  - Live data logging (data stream)
  - Fault codes (DTCs)
  - Vehicle and session metadata
  - optional screenshots
- End users can usually **only export PDF reports**, not the raw data
- `.tc` files can only be played back within the original app/device software
- Users describe the format as "encrypted / unreadable"

---

## 2. Suspected File Structure

### 2.1 Header (very likely)

Very likely contains:
- VIN (17 ASCII characters, often findable)
- Recording timestamp
- Device ID / App version
- possibly vehicle model / ECU-ID
- File format version

Evidence:
- Official documents mention VIN and test time as basis of the file
- Support uploads contain complete session information

---

### 2.2 Data Blocks

#### a) Diagnostic Report
- Fault codes (e.g., P0300)
- Status (current / history)
- possibly plain text descriptions
- Basis for PDF report

#### b) Live Data Stream (core component)
- Time-recorded parameters
- Presumably:
  - Parameter list (PID-IDs or internal IDs)
  - Timestamp + measured values
- Storage probably:
  - as repeated records of equal length **or**
  - as event records (time + parameter ID + value)

#### c) Additional Data
- Screenshots (possibly PNG/JPG blocks)
- Session notes / feedback data

---

## 3. Encoding, Compression, Encryption

Known facts:
- **Not a text format** (no CSV, JSON, XML)
- Content appears "encrypted", but is probably:
  - **binary structured**
  - **compressed** (e.g., zlib/deflate) **or**
  - lightly obfuscated (XOR, byte scrambling)

Evidence:
- Live data generates large amounts of data → compression makes sense
- Manufacturer wants to prevent simple third-party analysis
- No indication of strong cryptography (AES or similar)

Possible markers during analysis:
- `0x78 0x9C` → zlib
- recurring block lengths
- plaintext islands (VIN, PIDs, ASCII strings)

---

## 4. Reverse Engineering Approaches

### 4.1 Static Analysis
- Hex editor (HxD)
- `strings` tool
- Binwalk (search for compression / embedded files)
- Comparison of multiple `.tc` files of the same vehicle type

### 4.2 Comparison with Reference Data
- Same drive / diagnosis:
  - once `.tc`
  - once with another tool (CSV export)
- Comparison of curve progressions and raw values

### 4.3 Software Analysis
- Decompile Android APK of ThinkCar app (JADX)
- Search for:
  - `.tc`
  - `log`, `record`, `playback`
- Analysis of:
  - Parsing functions
  - possible decryption / decompression

### 4.4 Existing Solutions
- **FCD Log Decoder** (commercial)
  - supports ThinkCar `.TC`
  - Proof that reverse engineering is feasible

---

## 5. Similarities to Other Formats

### Launch X-431 `.x431`
- Very similar function
- Also proprietary
- Also live data + playback
- User reports confirm binary structure

High probability:
> ThinkCar `.tc` is conceptually and structurally closely related to Launch `.x431`

---

## 6. Python Implementation Strategy (High-Level)

Recommended steps:
1. Identify header (offset, length, version)
2. Find block boundaries
3. Test compression (`zlib.decompress`)
4. Reconstruct record structure
5. Extract timestamps + values
6. Mapping to known OBD-II PIDs
7. Export to CSV / Parquet / MDF

Relevant Python modules:
- `struct`
- `zlib`
- `construct`
- `numpy`, `pandas`

---

## 7. Known Limitations

- No official documentation
- Changes between app versions possible
- Resellers use the same engine, but possibly slightly different headers
- Consider legal aspects of reverse engineering

---

## 8. Sources (public)

- ThinkCar Community Forum: Export questions about `.tc`
- FCC / Product documentation ThinkScan: Description of log function
- MHH Auto, ScannerDanner, Reddit: User reports
- FCD.eu: Support for ThinkCar `.TC`
- Launch X-431 manuals (`.x431` logs)

---

## Conclusion

The ThinkCar `.TC` format is a proprietary, binary diagnostic log container without public specification.  
With systematic reverse engineering, a **reading implementation in Python is realistic**, especially for live data conversion to CSV.  
The greatest effort lies in reconstructing the data stream structure and possible decompression.

---
