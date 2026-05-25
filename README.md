# Waters2mzML

Waters2mzML converts Waters MassLynx `.raw` directories into `.mzML` files.  
The pipeline performs metadata extraction, msconvert execution, MS‑level assignment, scan renumbering, optional QC extraction, and metadata validation.  
The output works with MZmine 3, OpenMS, MSnbase, and other mzML‑based tools.

Repository: [https://github.com/AnP311/Waters2mzML](https://github.com/AnP311/Waters2mzML)

---

## Overview

Waters2mzML provides:

- conversion through ProteoWizard msconvert  
- extraction of acquisition metadata from `_extern.inf`  
- metadata validation of RAW folder structure and function numbering  
- annotation of MS levels and precursor information  
- mzML post‑processing (scan renumbering, MS‑level correction)  
- optional QC metric extraction (TIC, BPC, peak counts)  
- parallel execution with retry logic  
- structured logging

Conversion requires a working msconvert installation, either native or Docker‑based.

---

## Features

### Metadata and annotation
- parse `_extern.inf`  
- detect analytical and non‑analytical functions  
- detect lockmass  
- assign MS1, MSe, and DDA levels  
- reconstruct precursor information when present  
- validate RAW metadata (extern structure, function sequence, FUNCxxx directories, lockmass consistency)  
- surface validation issues as warnings during annotation

### Conversion
- run msconvert in native or Docker mode  
- optional centroiding  
- correct MS levels and scan numbering  

### QC metrics
- extract TIC  
- extract BPC  
- count peaks per MS1 scan  
- skip QC for synthetic mzML fixtures  

### Parallel execution
- process multiple `.raw` directories concurrently  
- isolated per‑job working directories  
- retry msconvert failures  
- progress bar and per‑job timing  

### Logging
- structured logging for annotation, validation, conversion, QC, and parallel execution  
- configurable log level  

---

## Validation

Waters2mzML includes a dedicated validation module:

- checks `_extern.inf` structure  
- detects malformed or non‑ASCII lines  
- validates function headers and numbering  
- checks contiguity and monotonicity  
- validates FUNCxxx directory structure  
- cross‑checks extern function count vs filesystem  
- validates lockmass consistency  

Validation runs automatically during annotation and produces warnings without stopping the pipeline.

---

## Supported data

Validated on:

- Waters Synapt G2‑Si  
- Waters Xevo G2 (DDA)  
- MassLynx V4.2 `.raw` structure  

Other instruments may work if their `_extern` format matches these variants.

---

## Installation

Development install:

```
pip install -e ".[test]"
```

---

## Docker mode

Waters2mzML can run msconvert inside a Docker container.  
Users must supply an image containing:

- msconvert.exe  
- Wine or another Windows compatibility layer  
- an entrypoint compatible with msconvert arguments  

Enable Docker mode:

```
waters2mzml convert --input raw/ --output mzml/ --docker --docker-image my/msconvert
```

---

## Usage

Convert `.raw` directories:

```
waters2mzml convert -i raw/ -o mzml/
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
waters2mzml convert -i raw/ -o mzml/ --docker --docker-image my/msconvert
```

Set log level:

```
waters2mzml convert -i raw/ -o mzml/ --log-level DEBUG
```

---

## Pipeline details

### Annotation
- parse `_extern.inf`  
- detect lockmass  
- identify analytical functions  
- remove non‑analytical functions  
- run metadata validation and surface issues as warnings

### Conversion
- run msconvert  
- apply centroiding when requested  

### Post‑processing
- renumber scans  
- correct MS levels  
- fix metadata inconsistencies  

### QC extraction
- compute TIC, BPC, peak counts  
- skip QC for synthetic mzML files  

### Parallel execution
- each `.raw` directory processed independently  
- progress bar updated on job completion  
- per‑job timing logged  
- retry logic for msconvert failures  
