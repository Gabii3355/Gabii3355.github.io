# Data

This folder contains the molecular data used to train and validate the machine learning interatomic potential for the formic acid dimer.

The data are organized into two main parts:

```text
data/
├── raw/
│   ├── trajectory_298.xyz
│   └── trajectory_500.xyz
└── deepmd/
    ├── FAD_298/
    └── FAD_500/
```

## Raw AIMD trajectories

The `raw/` folder contains the original molecular trajectories from ORCA ab initio molecular dynamics simulations.

| File | Description | Role in this project |
|---|---|---|
| `trajectory_298.xyz` | AIMD trajectory of the formic acid dimer at 298 K | Validation and testing dataset |
| `trajectory_500.xyz` | AIMD trajectory of the formic acid dimer at 500 K | Training dataset |

The 500 K trajectory was used for training because it samples a broader range of molecular configurations and higher-energy structures.  
The 298 K trajectory was used as an independent validation and test set to evaluate whether the trained model can generalize to lower-temperature configurations.

## DeepMD-formatted datasets

The `deepmd/` folder contains datasets converted into the DeepMD-kit format.

| Folder | Description | Role |
|---|---|---|
| `FAD_298/` | DeepMD dataset generated from the 298 K AIMD trajectory | Validation and testing |
| `FAD_500/` | DeepMD dataset generated from the 500 K AIMD trajectory | Training |

Each DeepMD dataset may contain files such as:

```text
type.raw
type_map.raw
set.000/
├── coord.npy
├── box.npy
├── energy.npy
└── force.npy
```

These files store atomic types, coordinates, simulation box information, reference energies and reference forces required for DeepMD-kit model training and testing.

## Dataset role in the workflow

```text
trajectory_500.xyz
        ↓
DeepMD conversion
        ↓
FAD_500 dataset
        ↓
Model training

trajectory_298.xyz
        ↓
DeepMD conversion
        ↓
FAD_298 dataset
        ↓
Validation and testing
```

## Notes

Large data files may be stored using Git LFS or provided through a GitHub Release, depending on repository size limits.

If the files are stored with Git LFS, download them after cloning the repository using:

```bash
git lfs install
git lfs pull
```

If the files are provided through a GitHub Release, download the archive from the release page and unpack it into this `data/` folder.

## Reproducibility

The datasets in this folder are used by the scripts in the main project workflow:

```text
scripts/01_convert_orca_aimd_to_deepmd.py
scripts/02_make_deepmd_input.py
scripts/04_plot_training_and_test_results.py
```

The conversion script prepares the DeepMD-compatible files from the raw AIMD trajectories, while the training input script defines how the 500 K and 298 K datasets are used during model training and validation.
