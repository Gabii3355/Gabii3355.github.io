# DNA sequence effects on cytosine deamination

This folder contains the portfolio page, figures and scripts for the master's thesis project.

TO DO:
README.md z opisem projektu i instrukcją uruchomienia.
Dane wejściowe i przetworzone w formacie CSV.
Folder figures z wykresami w wysokiej jakości.
Diagram workflow projektu.

## Requirements and external software

Some scripts in this repository require external computational chemistry or molecular visualization tools. They may not run in a standard Python environment without these programs installed and configured.

Required or optional tools include:

* **PyMOL** — used for DNA model inspection, single-nucleotide mutations and extraction of selected nucleobase fragments.
* **GAMESS** — used for quantum-chemical calculations and generation of output files required for CAMM electrostatic analysis.
* **Open Babel** — used for molecular file format conversion, especially during preparation of GAMESS input files.
* **pymolecule** — used for reading GAMESS multipole output and calculating CAMM interaction energies.
* **Python packages** — used for data processing and visualization, including `pandas`, `numpy`, `matplotlib` and `seaborn`.

Because some scripts depend on external software, the full workflow may require local installation of these tools and correct file paths. The plotting scripts can be run independently if the processed `.txt` or `.csv` data files are already available.
## Notes on running the scripts

Part of the workflow depends on external software. Some scripts require **PyMOL** for structure mutation and extraction, **GAMESS** for quantum-chemical calculations, **Open Babel** for file conversion and the `pymolecule` module for CAMM energy calculations.

The visualization scripts mainly require standard Python packages such as `pandas`, `numpy`, `matplotlib` and `seaborn`.

