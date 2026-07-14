# Machine Learning Interatomic Potential for Formic Acid Dimer

This project presents a machine learning interatomic potential for the formic acid dimer (FAD).  
The workflow combines ab initio molecular dynamics data, DeepMD-kit model training and molecular dynamics simulations in LAMMPS.

The aim of the project was to prepare ORCA AIMD data, convert molecular trajectories into the DeepMD format, train a neural network potential and test whether the trained model can reproduce reference energies and forces for an independent validation set.

## Project overview

The reference data came from ab initio molecular dynamics simulations performed at two temperatures:

- 500 K trajectory: training dataset
- 298 K trajectory: independent validation and test dataset

The trained model was then frozen, compressed and used as a machine learning potential in a LAMMPS molecular dynamics simulation at 298 K.

## Workflow

```text
ORCA AIMD trajectories
        ↓
Data conversion to DeepMD format
        ↓
DeepMD-kit model training
        ↓
Model testing on 298 K validation set
        ↓
Model freezing and compression
        ↓
LAMMPS molecular dynamics simulation
        ↓
Trajectory and RMSD analysis
```

## Methods

The model was trained using DeepMD-kit with the `se_e2_a` descriptor.  
The descriptor describes local atomic environments within a cutoff radius of 6.0 Å.

Main training settings:

| Parameter | Value |
|---|---|
| Descriptor | `se_e2_a` |
| Cutoff radius | 6.0 Å |
| Smooth cutoff | 0.5 Å |
| Descriptor neurons | `[10, 20, 40]` |
| Fitting network neurons | `[100, 100, 100]` |
| Training steps | 50,000 |
| Training dataset | FAD 500 K |
| Validation dataset | FAD 298 K |
| Energy prefactor | start: 0.02, limit: 1 |
| Force prefactor | start: 1000, limit: 1 |

## Results

The model showed stable convergence during training.  
Training and validation RMSE decreased over 50,000 optimization steps without clear signs of overfitting.

Final model performance on the 298 K validation set:

| Metric | Value |
|---|---|
| Energy MAE | 2.25 meV |
| Energy RMSE | 2.89 meV |
| Force MAE | 23 meV/Å |
| Force RMSE | 29 meV/Å |

The compressed DeepMD model was successfully used in a 10,000-step LAMMPS molecular dynamics simulation at 298 K.  
The RMSD stayed below approximately 0.26 Å, indicating that the formic acid dimer structure remained stable during the simulation.

## Repository structure

```text
formic-acid-mlp/
├── index.html
├── formic.css
├── README.md
├── requirements.txt
├── environment.yml
├── figures/
│   ├── formic-acid-dimer.png
│   ├── learning_curve.png
│   ├── force_rmse.png
│   ├── aimd_energy.png
│   ├── energy_distribution.png
│   ├── model_errors.png
│   └── rmsd_lammps.png
├── scripts/
│   ├── 01_convert_orca_aimd_to_deepmd.py
│   ├── 02_make_deepmd_input.py
│   ├── 03_prepare_lammps_run.py
│   ├── 04_plot_training_and_test_results.py
│   └── 05_analyze_lammps_trajectory.py
├── notebooks/
│   └── task_2_ML.ipynb
├── data/
│   ├── raw/
│   │   ├── trajectory_298.xyz
│   │   └── trajectory_500.xyz
│   └── deepmd/
│       ├── FAD_298/
│       └── FAD_500/
├── models/
│   ├── graph.pb
│   └── graph-compress.pb
└── lammps/
    ├── in.lammps
    ├── conf.lmp
    └── fad_mlp.dump
```

## Scripts

The workflow was divided into separate Python scripts:

| Script | Purpose |
|---|---|
| `01_convert_orca_aimd_to_deepmd.py` | Converts ORCA AIMD trajectories and force files into DeepMD-compatible datasets |
| `02_make_deepmd_input.py` | Creates the DeepMD `input.json` training configuration |
| `03_prepare_lammps_run.py` | Prepares LAMMPS input files for MD simulation with the trained model |
| `04_plot_training_and_test_results.py` | Generates plots for learning curves, force RMSE and model errors |
| `05_analyze_lammps_trajectory.py` | Analyzes the LAMMPS trajectory and calculates RMSD |

## Installation

Create the Conda environment:

```bash
conda env create -f environment.yml
conda activate formic-acid-mlp
```

Alternatively, install only the basic Python dependencies:

```bash
pip install -r requirements.txt
```

## Example usage

Convert ORCA AIMD data:

```bash
python scripts/01_convert_orca_aimd_to_deepmd.py
```

Create DeepMD training input:

```bash
python scripts/02_make_deepmd_input.py
```

Train the model:

```bash
dp train input.json
```

Freeze and compress the trained model:

```bash
dp freeze -o graph.pb
dp compress -i graph.pb -o graph-compress.pb
```

Prepare the LAMMPS simulation:

```bash
python scripts/03_prepare_lammps_run.py
```

Run LAMMPS:

```bash
cd lammps
lmp -i in.lammps
cd ..
```

Plot training and testing results:

```bash
python scripts/04_plot_training_and_test_results.py
```

Analyze the LAMMPS trajectory:

```bash
python scripts/05_analyze_lammps_trajectory.py
```
## Technologies

- Python
- NumPy
- pandas
- Matplotlib
- ORCA AIMD data
- DeepMD-kit
- LAMMPS
- Conda
- Git / GitHub

## Key conclusions

The project shows that a DeepMD neural network potential can reproduce the reference AIMD energies and forces for a small molecular system with good accuracy.  
Training on the broader 500 K trajectory allowed the model to generalize to the lower-temperature 298 K validation set.  
The compressed model also produced a stable LAMMPS molecular dynamics trajectory, confirming that the learned potential can be used for molecular simulation of the formic acid dimer.

## Project page

A portfolio page presenting this project is available in the GitHub Pages version of this repository.

## Author

Gabriela Bieda  
MSc Bioinformatics student  
Computational chemistry · Molecular modeling · Machine learning

## Acknowledgements

The scripts used in this project were adapted and modified for the formic acid dimer system based on the official DeepModeling DeePMD-kit hands-on tutorial:

[DeepMD-kit Handson-Tutorial v2.0.3](https://tutorials.deepmodeling.com/en/latest/Tutorials/DeePMD-kit/learnDoc/Handson-Tutorial%28v2.0.3%29.html)

The original tutorial presents the general DeePMD-kit workflow, including data preparation, model training and model application. In this project, the workflow was adjusted to ORCA AIMD data for the formic acid dimer, with the 500 K trajectory used for training and the 298 K trajectory used for validation and testing.

TODO:
-> dodac prawidlowy folder z notebook pliki inputowe i nazwac folder automated_costam
-> zmienic w readme i na stronie zmiane wygladu repository i dopsiac ze w tym folderze jest zautomatyzowany proces tych obliczen
