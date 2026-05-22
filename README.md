# **Waters2mzML**

Waters2mzML converts Waters `.raw` MS¹ and MSⁿ data (MSe and DDA) into structured `.mzML` files and applies post‑processing steps to correct metadata, MS levels, and scan numbering. The output is compatible with tools such as MZmine 3.

The project is a Python package with a modular pipeline:

- conversion through ProteoWizard `msconvert`
- extraction of acquisition metadata from Waters `_extern` files
- annotation of MS levels and precursor information
- mzML post‑processing and scan renumbering

The implementation is platform‑agnostic at the Python level. Conversion still depends on ProteoWizard availability on the host system.

Repository: [https://github.com/AnP311/Waters2mzML](https://github.com/AnP311/Waters2mzML)

---

## **Features**

- Parse Waters `_extern` metadata  
- Identify and remove non‑analytical functions (e.g., lockmass)  
- Assign MS levels for MS¹, MSe, and DDA  
- Reconstruct precursor information when present  
- Convert `.raw` to `.mzML` through `msconvert`  
- Renumber scans and correct metadata in the resulting `.mzML`  
- Provide a CLI entry point (`waters2mzml`)  
- Include unit, integration, and regression tests  

---

## **Supported Data**

Tested on:

- Waters Synapt G2‑Si  
- Waters Xevo G2 (DDA)  
- MassLynx V4.2 `.raw` structure  

Other Waters instruments may work if their `_extern` format matches the tested variants.

---

## **Installation**

Not yet published to PyPI.

For development:

```
pip install -e ".[test]"
```

---

## **Usage**

Run the full pipeline on one or more `.raw` directories:

```
waters2mzml convert path/to/raw_files/ --out path/to/mzml/
```

The CLI handles:

- locating `msconvert`
- running the conversion
- applying raw annotation
- applying mzML post‑processing

See `waters2mzml --help` for all commands and options.

---

## **Processing Notes**

### **Function Ordering**

The pipeline infers function roles from the `_extern` file:

- Function 1 → MS¹  
- Subsequent functions → MS² (MSe or DDA)  
- Lockmass → treated as MS¹ unless removed  
- Higher functions → ignored  

### **MSe Precursor Assignment**

For MSe data, the pipeline assigns a precursor m/z based on the isolation window defined in the raw metadata. This reflects the acquisition setup but may not be required by all downstream tools.

### **Profile vs. Centroid**

Centroiding is delegated to ProteoWizard.  
If profile data is present, the user can enable peak picking through the CLI.

---

## **Development**

The repository includes:

- modular Python package (`waters2mzml/`)  
- test suite (`tests/`)  
- CI workflow
- modern packaging (`pyproject.toml`)  

---

## **Citation**

If you use Waters2mzML in a publication, cite the repository and ProteoWizard:

- Chambers et al., *Nat. Biotechnol.* 30, 918–920 (2012)  
- [https://proteowizard.sourceforge.io/tools/msconvert.html](https://proteowizard.sourceforge.io/tools/msconvert.html)  
