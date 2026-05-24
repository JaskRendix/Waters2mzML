# **Waters2mzML**

Waters2mzML converts Waters `.raw` MS¹ and MSⁿ data (MSe and DDA) into structured `.mzML` files and applies post‑processing steps to correct metadata, MS levels, and scan numbering. The output is compatible with tools such as MZmine 3.

The project is a modular Python package built around a reproducible conversion pipeline:

- conversion through ProteoWizard `msconvert`
- extraction of acquisition metadata from Waters `_extern` files
- annotation of MS levels and precursor information
- mzML post‑processing and scan renumbering
- optional parallel execution with retry logic

Conversion depends on ProteoWizard availability on the host system.

Repository: [https://github.com/AnP311/Waters2mzML](https://github.com/AnP311/Waters2mzML)

---

## **Features**

- Parse Waters `_extern` metadata  
- Identify and remove non‑analytical functions  
- Assign MS levels for MS¹, MSe, and DDA  
- Reconstruct precursor information when present  
- Convert `.raw` to `.mzML` through `msconvert`  
- Renumber scans and correct metadata in the `.mzML`  
- Parallel execution with configurable worker count  
- Retry logic for failed jobs  
- CLI entry point (`waters2mzml`)  
- Unit, integration, and regression tests  

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
This enables full conversion on **Linux and macOS**, where native `msconvert.exe` is not available.

Docker mode is fully integrated into the CLI and pipeline, but **Waters2mzML does not ship a Docker image**.  
Users must provide their own image containing a working `msconvert` installation.

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

To use Docker mode, you must supply an image that contains:

- a working `msconvert.exe`  
- Wine or another Windows compatibility layer  
- an ENTRYPOINT that accepts standard msconvert arguments  

You can specify the image via CLI:

```
waters2mzml convert --input raw/ --output mzml/ --docker --docker-image your/msconvert-image
```

Or configure it in `ConversionConfig`.

---

## **How Docker Mode Works**

When `--docker` is enabled, Waters2mzML:

- mounts the parent directory of each `.raw` folder into the container  
- calls the container’s ENTRYPOINT with:  
  ```
  /data/<raw_name> <msconvert args> --outdir /data
  ```
- writes the resulting `.mzML` file back to the host filesystem  

This makes Docker mode fully transparent to the rest of the pipeline.

---

## **Notes**

- Waters2mzML does **not** build or distribute a Docker image.  
- You must provide an image that contains a working msconvert installation.  
- Docker mode requires the `docker` CLI to be available on the host.  
- Output `.mzML` files are identical to native msconvert output except for timestamps.  

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

### **Parallel Execution**

Multiple `.raw` directories can be processed concurrently.  
Each directory is handled as an isolated job.  
Failed jobs can be retried a configurable number of times.

---

## **Development**

The repository contains:

- the Python package (`waters2mzml/`)  
- test suite (`tests/`)  
- CI workflow  
- tests for parallel execution and retry logic  
- modern packaging (`pyproject.toml`)  
