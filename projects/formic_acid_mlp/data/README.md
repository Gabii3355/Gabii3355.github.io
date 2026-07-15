# Data

This folder contains the raw ORCA AIMD trajectory and force files, as well as the processed datasets prepared for DeepMD-kit model training, validation and testing.

## Folder structure

```text
data/
├── raw/
│   ├── forces_298.xyz
│   ├── forces_500.xyz
│   ├── trajectory_298.xyz
│   └── trajectory_500.xyz
└── deepmd/
    ├── npy_format/
    │   ├── train/
    │   │   ├── set.000/
    │   │   ├── nopbc
    │   │   ├── type.raw
    │   │   └── type_map.raw
    │   ├── validation/
    │   │   ├── set.000/
    │   │   ├── nopbc
    │   │   ├── type.raw
    │   │   └── type_map.raw
    │   └── test/
    │       ├── set.000/
    │       ├── nopbc
    │       ├── type.raw
    │       └── type_map.raw
    ├── train/
    ├── validation/
    └── test/
```

## Raw ORCA AIMD data

The `raw/` folder contains the original trajectory and force files generated from ORCA-based ab initio molecular dynamics calculations for the formic acid dimer.

| File | Description | Role in this project |
|---|---|---|
| `trajectory_298.xyz` | Molecular trajectory at 298 K | Source of validation and test structures |
| `forces_298.xyz` | Reference energies and forces corresponding to the 298 K trajectory | Source of validation and test labels |
| `trajectory_500.xyz` | Molecular trajectory at 500 K | Source of training structures |
| `forces_500.xyz` | Reference energies and forces corresponding to the 500 K trajectory | Source of training labels |

The trajectory files contain atomic coordinates in Angstrom.

The force files contain reference potential energies and atomic forces from ORCA. During preprocessing, energies were converted from Hartree to eV and forces from Hartree/Angstrom to eV/Angstrom for compatibility with the DeepMD/LAMMPS `units metal` convention.

## Dataset split

The dataset was divided according to temperature.

The all 500 K dataset was used for training because it samples a broader range of molecular configurations, including higher-energy structures.

The 298 K dataset was randomly split into validation and test subsets. The validation set contained 20% of the 298 K frames, while the remaining 80% were used as an independent test set.

The same frame indices were used for trajectory and force files to preserve the correspondence between atomic coordinates, energies and forces.

Final split:

| Dataset | Source data | Role |
|---|---|---|
| `train/` | Full 500 K trajectory and force data | Model training |
| `validation/` | 20% of the 298 K trajectory and force data | Validation during training |
| `test/` | 80% of the 298 K trajectory and force data | Independent model testing |

In this workflow, the split was designed to check whether a model trained on higher-temperature configurations can reproduce energies and forces for lower-temperature structures.

## DeepMD-formatted datasets

The `deepmd/` folder contains data prepared for DeepMD-kit.

The folders:

```text
deepmd/train/
deepmd/validation/
deepmd/test/
```

contain the intermediate split trajectory and force files before conversion to NumPy format.

The folder:

```text
deepmd/npy_format/
```

contains the final DeepMD-compatible datasets used directly by DeepMD-kit.

Each dataset contains files such as:

```text
type.raw
type_map.raw
nopbc
set.000/
├── coord.npy
├── energy.npy
└── force.npy
```

Depending on the conversion settings, additional files such as `box.npy` may also be present.

These files store the atomic types, atom type mapping, coordinates, reference energies and reference forces required for DeepMD-kit training and testing.

## DeepMD atom types

The atom type mapping is stored in `type_map.raw`. For this project, the atom types correspond to the atoms present in the formic acid dimer:

```text
H C O
```

This order must be kept consistent between the DeepMD dataset, the training input file and the LAMMPS configuration file.

## Workflow summary

```text
trajectory_500.xyz + forces_500.xyz
        ↓
training split
        ↓
DeepMD npy conversion
        ↓
deepmd/npy_format/train
        ↓
model training


trajectory_298.xyz + forces_298.xyz
        ↓
random split
        ↓
20% validation + 80% test
        ↓
DeepMD npy conversion
        ↓
deepmd/npy_format/validation
deepmd/npy_format/test
        ↓
validation and independent testing
```

## Notes on large files

Large data files may be stored using Git LFS or provided through a GitHub Release, depending on repository size limits.

If the files are stored with Git LFS, download them after cloning the repository using:

```bash
git lfs install
git lfs pull
```

If the files are provided through a GitHub Release, download the archive from the release page and unpack it into this `data/` folder.

## Reproducibility

The datasets in this folder are used by the scripts and notebook in the main project workflow. The preprocessing steps include:

1. reading ORCA trajectory and force files,
2. splitting the 500 K and 298 K datasets into train, validation and test subsets,
3. converting energies and forces to DeepMD-compatible units,
4. writing the final DeepMD `npy` datasets,
5. training and testing the DeepMD model.

The trained model was evaluated on the independent test set prepared from the 298 K trajectory.
