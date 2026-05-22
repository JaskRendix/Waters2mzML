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

---

## **Citation**

If you use Waters2mzML, cite the repository and ProteoWizard:

- Chambers et al., *Nat. Biotechnol.* 30, 918–920 (2012)  
- [https://proteowizard.sourceforge.io/tools/msconvert.html](https://proteowizard.sourceforge.io/tools/msconvert.html)  
