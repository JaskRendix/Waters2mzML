# **Waters2mzML**

Waters2mzML converts Waters `.raw` MS¹ and MSⁿ data (MSe and DDA) into structured `.mzML` files and applies post‑processing steps to correct metadata, MS levels, and scan numbering. The output is compatible with downstream tools such as MZmine 3.

The package implements a reproducible, modular conversion pipeline:

- conversion through ProteoWizard `msconvert`
- extraction of acquisition metadata from Waters `_extern` files
- annotation of MS levels and precursor information
- mzML post‑processing (scan renumbering, MS‑level correction)
- **optional QC metric extraction (TIC, BPC, peak counts)**
- optional parallel execution with retry logic

Conversion requires a working ProteoWizard installation (native or Docker‑based).

Repository: [https://github.com/AnP311/Waters2mzML](https://github.com/AnP311/Waters2mzML)

---

## **Features**

- Parse Waters `_extern` metadata  
- Identify and remove non‑analytical functions  
- Assign MS levels for MS¹, MSe, and DDA  
- Reconstruct precursor information when present  
- Convert `.raw` to `.mzML` via `msconvert`  
- Renumber scans and correct metadata in the `.mzML`  
- **Compute basic QC metrics (TIC, BPC, peak counts) for real mzML files**  
- Parallel execution with configurable worker count  
- Retry logic for failed jobs  
- CLI entry point (`waters2mzml`)  
- Comprehensive unit, integration, and regression tests  

QC extraction is optional and automatically disabled for synthetic fixtures or incomplete mzML files.

---

## **Supported Data**

Validated on:

- Waters Synapt G2‑Si  
- Waters Xevo G2 (DDA)  
- MassLynx V4.2 `.raw` structure  

Other Waters instruments may work if their `_extern` format matches the tested variants.

---

## **Installation**

Development installation:

```
pip install -e ".[test]"
```

---

# **Docker Usage**

Waters2mzML can run ProteoWizard `msconvert` inside a Docker container.  
This enables full conversion on Linux and macOS, where native `msconvert.exe` is not available.

Docker mode is fully integrated into the CLI and pipeline, but Waters2mzML does **not** ship a Docker image.  
Users must provide their own image containing a working msconvert installation.

---

## **When to Use Docker Mode**

Use Docker mode if:

- you are on Linux or macOS  
- you do not have a native ProteoWizard installation  
- you want reproducible, isolated conversions  
- you run Waters2mzML on servers, clusters, or CI systems  

On Windows, native mode is usually faster.

---

## **Providing Your Own Docker Image**

Because ProteoWizard binaries cannot be redistributed, Waters2mzML does **not** include a Dockerfile or a prebuilt image.

Your image must contain:

- a working `msconvert.exe`  
- Wine or another Windows compatibility layer  
- an ENTRYPOINT compatible with standard msconvert arguments  

Specify the image via CLI:

```
waters2mzml convert --input raw/ --output mzml/ --docker --docker-image your/msconvert-image
```

---

## **How Docker Mode Works**

When `--docker` is enabled, Waters2mzML:

- mounts the parent directory of each `.raw` folder into the container  
- calls the container’s ENTRYPOINT with:  
  ```
  /data/<raw_name> <msconvert args> --outdir /data
  ```
- writes the resulting `.mzML` file back to the host filesystem  

The rest of the pipeline is identical to native mode.

---

## **Usage**

Convert one or more `.raw` directories:

```
waters2mzml convert path/to/raw/ --out path/to/mzml/
```

The CLI performs:

- raw annotation  
- msconvert execution  
- mzML post‑processing  
- **QC metric extraction (if applicable)**  
- optional parallel execution  

Run `waters2mzml --help` for all options.

---

## **Processing Notes**

### **Function Roles**

Function roles are inferred from the `_extern` file:

- Function 1 → MS¹  
- Subsequent functions → MS² (MSe or DDA)  
- Lockmass → treated as MS¹ unless removed  
- Higher functions → ignored  

### **MSe Precursor Assignment**

For MSe data, precursor m/z values are assigned from the isolation window defined in the raw metadata.

### **Centroiding**

Centroiding is handled by ProteoWizard.  
Peak picking can be enabled through the CLI.

### **QC Metrics**

For real mzML files, Waters2mzML extracts:

- **TIC** (Total Ion Current)  
- **BPC** (Base Peak Chromatogram)  
- **Peak counts** per MS¹ scan  

QC extraction is skipped automatically for synthetic mzML files used in tests.

### **Parallel Execution**

Multiple `.raw` directories can be processed concurrently.  
Each directory is handled as an isolated job.  
Failed jobs can be retried a configurable number of times.

---

## **Development**

The repository contains:

- the Python package (`waters2mzml/`)  
- QC subsystem (`waters2mzml/qc.py`)  
- test suite (`tests/`) including QC‑aware tests  
- CI workflow  
- tests for parallel execution and retry logic  
- modern packaging (`pyproject.toml`)  
