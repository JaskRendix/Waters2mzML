# Waters2mzML

Waters2mzML converts Waters MassLynx `.raw` directories into structured `.mzML` files.  
The pipeline performs metadata extraction, msconvert execution, MS‑level assignment, scan renumbering, and optional QC metric extraction.  
The output is compatible with tools such as MZmine 3, OpenMS, and MSnbase.

Repository: [https://github.com/AnP311/Waters2mzML](https://github.com/AnP311/Waters2mzML)

---

## Overview

Waters2mzML provides:

- conversion through ProteoWizard `msconvert`
- extraction of acquisition metadata from Waters `_extern` files
- annotation of MS levels and precursor information
- mzML post‑processing (scan renumbering, MS‑level correction)
- optional QC metric extraction (TIC, BPC, peak counts)
- parallel execution with retry logic
- progress bar and per‑job timing in parallel mode
- structured logging across all modules

Conversion requires a working ProteoWizard installation, either native or Docker‑based.

---

## Features

### Metadata and Annotation
- parse `_extern.inf`
- detect analytical and non‑analytical functions
- identify lockmass
- assign MS¹, MSe, and DDA levels
- reconstruct precursor information when present

### Conversion
- run msconvert in native or Docker mode
- apply centroiding when requested
- correct MS levels and scan numbering

### QC Metrics
- extract TIC
- extract BPC
- count peaks per MS¹ scan
- skip QC for synthetic mzML fixtures

### Parallel Execution
- process multiple `.raw` directories concurrently
- isolated per‑job working directories
- retry msconvert failures
- progress bar
- per‑job timing metrics

### Logging
- structured logging for annotation, conversion, QC, and parallel execution
- configurable log level through CLI

---

## Supported Data

Validated on:

- Waters Synapt G2‑Si  
- Waters Xevo G2 (DDA)  
- MassLynx V4.2 `.raw` structure  

Other instruments may work if their `_extern` format matches these variants.

---

## Installation

Development installation:

```
pip install -e ".[test]"
```

---

## Docker Mode

Waters2mzML can run msconvert inside a Docker container.  
This enables conversion on Linux and macOS.

Waters2mzML does not ship a Docker image.  
Users must supply an image containing:

- `msconvert.exe`
- Wine or another Windows compatibility layer
- an ENTRYPOINT compatible with msconvert arguments

Enable Docker mode with:

```
waters2mzml convert --input raw/ --output mzml/ --docker
```

---

## Usage

Convert `.raw` directories:

```
waters2mzml convert --input path/to/raw/ --output path/to/mzml/
```

Enable centroiding:

```
waters2mzml convert -i raw/ -o mzml/ --centroid
```

Run in parallel:

```
waters2mzml convert -i raw/ -o mzml/ -p 8
```

Enable Docker:

```
waters2mzml convert -i raw/ -o mzml/ --docker
```

Set log level:

```
waters2mzml convert -i raw/ -o mzml/ --log-level DEBUG
```

---

## Pipeline Details

### Annotation
- parse `_extern.inf`
- detect lockmass
- identify analytical functions
- remove non‑analytical functions

### Conversion
- run msconvert
- apply centroiding when requested

### Post‑Processing
- renumber scans
- correct MS levels
- fix metadata inconsistencies

### QC Extraction
- compute TIC, BPC, peak counts
- skip QC for synthetic mzML files

### Parallel Execution
- each `.raw` directory processed independently
- progress bar updated on job completion
- per‑job timing logged
- retry logic for msconvert failures
