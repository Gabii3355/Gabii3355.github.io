#!/usr/bin/env python3
"""
01_convert_orca_aimd_to_deepmd.py

Prepare train/validation/test datasets for DeepMD-kit from ORCA AIMD XYZ files.

Dataset split used in this project:
- full 500 K dataset -> training set
- 20% of 298 K dataset -> validation set
- remaining 80% of 298 K dataset -> independent test set

Input files:
data/raw/trajectory_298.xyz
data/raw/forces_298.xyz
data/raw/trajectory_500.xyz
data/raw/forces_500.xyz

Output folders:
data/deepmd/train/
data/deepmd/validation/
data/deepmd/test/
data/deepmd/npy_format/train/
data/deepmd/npy_format/validation/
data/deepmd/npy_format/test/
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
from pathlib import Path

import numpy as np
import dpdata
from ase.io import read


HARTREE_TO_EV = 27.211386245988


def default_project_dir() -> Path:
    """Return repository root when this script is stored in scripts/."""
    return Path(__file__).resolve().parents[1]


def read_xyz_frames(path: Path) -> list[list[str]]:
    """Read a multi-frame XYZ file as a list of frames."""
    frames: list[list[str]] = []

    with open(path, "r") as f:
        while True:
            first = f.readline()

            if not first:
                break

            if not first.strip():
                continue

            n_atoms = int(first.strip())
            comment = f.readline()
            atoms = [f.readline() for _ in range(n_atoms)]

            frames.append([first, comment] + atoms)

    return frames


def write_xyz_frames(frames: list[list[str]], path: Path) -> None:
    """Write selected XYZ frames to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        for frame in frames:
            f.writelines(frame)


def split_validation_test(
    n_frames: int,
    validation_ratio: float = 0.20,
    seed: int = 42,
) -> tuple[list[int], list[int]]:
    """Split 298 K frame indices into validation and test subsets."""
    indices = list(range(n_frames))

    random.seed(seed)
    random.shuffle(indices)

    n_validation = int(validation_ratio * n_frames)

    validation_idx = indices[:n_validation]
    test_idx = indices[n_validation:]

    return validation_idx, test_idx


def extract_energy_from_comment(comment: str) -> float:
    """
    Extract E_Pot value from an XYZ comment line.

    Example:
    ORCA AIMD Force Step 0, t=0.00 fs, E_Pot=-378.87723896 Hartree
    """
    match = re.search(
        r"E_Pot\s*=\s*([-+]?\d+(?:\.\d+)?(?:[EeDd][-+]?\d+)?)",
        comment,
    )

    if match is None:
        raise ValueError(f"Could not find E_Pot in comment line:\n{comment}")

    return float(match.group(1).replace("D", "E"))


def read_forces_and_energies(forces_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Read a multi-frame XYZ-like ORCA force file.

    Input units:
    - energy: Hartree
    - forces: Hartree/Angstrom

    Output units for DeepMD/LAMMPS metal units:
    - energy: eV
    - forces: eV/Angstrom
    """
    energies = []
    forces = []

    with open(forces_path, "r") as f:
        while True:
            first_line = f.readline()

            if not first_line:
                break

            if not first_line.strip():
                continue

            n_atoms = int(first_line.strip())
            comment = f.readline().strip()

            energy_hartree = extract_energy_from_comment(comment)
            energy_ev = energy_hartree * HARTREE_TO_EV
            energies.append(energy_ev)

            frame_forces = []

            for _ in range(n_atoms):
                parts = f.readline().split()

                if len(parts) < 4:
                    raise ValueError(
                        f"Incorrect force line in {forces_path}:\n{parts}"
                    )

                fx, fy, fz = [float(x) * HARTREE_TO_EV for x in parts[1:4]]
                frame_forces.append([fx, fy, fz])

            forces.append(frame_forces)

    return np.array(energies), np.array(forces)


def convert_xyz_to_deepmd_npy(
    trajectory_path: Path,
    forces_path: Path,
    output_dir: Path,
) -> None:
    """Convert trajectory and force XYZ files into DeepMD npy format."""
    print("\nProcessing:")
    print(f"Trajectory: {trajectory_path}")
    print(f"Forces:     {forces_path}")

    if not trajectory_path.exists():
        raise FileNotFoundError(f"Missing trajectory file: {trajectory_path}")

    if not forces_path.exists():
        raise FileNotFoundError(f"Missing forces file: {forces_path}")

    ase_frames = read(str(trajectory_path), index=":", format="extxyz")

    data = dpdata.System()

    for atoms in ase_frames:
        data.append(dpdata.System(atoms, fmt="ase/structure"))

    n_frames = len(data)
    n_atoms = data.get_natoms()

    energies, forces = read_forces_and_energies(forces_path)

    if len(energies) != n_frames:
        raise ValueError(
            f"Energy/frame mismatch for {forces_path}: "
            f"{len(energies)} energies, but {n_frames} trajectory frames."
        )

    if forces.shape != (n_frames, n_atoms, 3):
        raise ValueError(
            f"Force shape mismatch for {forces_path}: "
            f"expected {(n_frames, n_atoms, 3)}, got {forces.shape}."
        )

    data.data["energies"] = energies
    data.data["forces"] = forces

    if output_dir.exists():
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    data.to("deepmd/npy", str(output_dir))

    print(f"Saved DeepMD npy data to: {output_dir}")
    print(f"Frames: {n_frames}")
    print(f"Atoms per frame: {n_atoms}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert ORCA AIMD trajectory and force files to DeepMD-kit npy datasets."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=default_project_dir(),
        help="Project root directory. Default: repository root inferred from scripts/.",
    )
    parser.add_argument(
        "--validation-ratio",
        type=float,
        default=0.20,
        help="Fraction of 298 K data used for validation. Default: 0.20.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for splitting 298 K data. Default: 42.",
    )
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()

    raw_dir = project_dir / "data" / "raw"
    deepmd_dir = project_dir / "data" / "deepmd"
    npy_dir = deepmd_dir / "npy_format"

    trajectory_298 = raw_dir / "trajectory_298.xyz"
    forces_298 = raw_dir / "forces_298.xyz"
    trajectory_500 = raw_dir / "trajectory_500.xyz"
    forces_500 = raw_dir / "forces_500.xyz"

    train_dir = deepmd_dir / "train"
    validation_dir = deepmd_dir / "validation"
    test_dir = deepmd_dir / "test"

    for folder in [train_dir, validation_dir, test_dir, npy_dir]:
        folder.mkdir(parents=True, exist_ok=True)

    print("Project folder:", project_dir)
    print("Raw data folder:", raw_dir)
    print("DeepMD folder:", deepmd_dir)

    trajectory_500_frames = read_xyz_frames(trajectory_500)
    forces_500_frames = read_xyz_frames(forces_500)

    trajectory_298_frames = read_xyz_frames(trajectory_298)
    forces_298_frames = read_xyz_frames(forces_298)

    if len(trajectory_500_frames) != len(forces_500_frames):
        raise ValueError(
            f"Frame mismatch for 500 K: "
            f"{len(trajectory_500_frames)} trajectory frames, "
            f"{len(forces_500_frames)} force frames"
        )

    if len(trajectory_298_frames) != len(forces_298_frames):
        raise ValueError(
            f"Frame mismatch for 298 K: "
            f"{len(trajectory_298_frames)} trajectory frames, "
            f"{len(forces_298_frames)} force frames"
        )

    write_xyz_frames(
        trajectory_500_frames,
        train_dir / "trajectory_train_500K.xyz",
    )
    write_xyz_frames(
        forces_500_frames,
        train_dir / "forces_train_500K.xyz",
    )

    validation_idx, test_idx = split_validation_test(
        n_frames=len(trajectory_298_frames),
        validation_ratio=args.validation_ratio,
        seed=args.seed,
    )

    write_xyz_frames(
        [trajectory_298_frames[i] for i in validation_idx],
        validation_dir / "trajectory_validation_298K.xyz",
    )
    write_xyz_frames(
        [forces_298_frames[i] for i in validation_idx],
        validation_dir / "forces_validation_298K.xyz",
    )

    write_xyz_frames(
        [trajectory_298_frames[i] for i in test_idx],
        test_dir / "trajectory_test_298K.xyz",
    )
    write_xyz_frames(
        [forces_298_frames[i] for i in test_idx],
        test_dir / "forces_test_298K.xyz",
    )

    split_summary = {
        "strategy": "500 K for training; 298 K split into validation and test",
        "seed": args.seed,
        "validation_ratio": args.validation_ratio,
        "train": {
            "temperature": "500 K",
            "frames": len(trajectory_500_frames),
            "trajectory_file": str(train_dir / "trajectory_train_500K.xyz"),
            "forces_file": str(train_dir / "forces_train_500K.xyz"),
        },
        "validation": {
            "temperature": "298 K",
            "frames": len(validation_idx),
            "trajectory_file": str(validation_dir / "trajectory_validation_298K.xyz"),
            "forces_file": str(validation_dir / "forces_validation_298K.xyz"),
            "indices_from_298K": validation_idx,
        },
        "test": {
            "temperature": "298 K",
            "frames": len(test_idx),
            "trajectory_file": str(test_dir / "trajectory_test_298K.xyz"),
            "forces_file": str(test_dir / "forces_test_298K.xyz"),
            "indices_from_298K": test_idx,
        },
    }

    with open(deepmd_dir / "split_summary.json", "w") as f:
        json.dump(split_summary, f, indent=4)

    print("\nDataset split completed.")
    print("=" * 60)
    print(f"Training set:   500 K, {len(trajectory_500_frames)} frames")
    print(f"Validation set: 298 K, {len(validation_idx)} frames")
    print(f"Test set:       298 K, {len(test_idx)} frames")
    print("Split summary saved to:", deepmd_dir / "split_summary.json")

    split_files = {
        "train": {
            "trajectory": train_dir / "trajectory_train_500K.xyz",
            "forces": train_dir / "forces_train_500K.xyz",
            "output": npy_dir / "train",
        },
        "validation": {
            "trajectory": validation_dir / "trajectory_validation_298K.xyz",
            "forces": validation_dir / "forces_validation_298K.xyz",
            "output": npy_dir / "validation",
        },
        "test": {
            "trajectory": test_dir / "trajectory_test_298K.xyz",
            "forces": test_dir / "forces_test_298K.xyz",
            "output": npy_dir / "test",
        },
    }

    for split_name, paths in split_files.items():
        print("\n" + "=" * 70)
        print(f"Converting {split_name.upper()} set")

        convert_xyz_to_deepmd_npy(
            trajectory_path=paths["trajectory"],
            forces_path=paths["forces"],
            output_dir=paths["output"],
        )

    print("\nAll datasets converted to DeepMD npy format.")
    print("Output folder:", npy_dir)


if __name__ == "__main__":
    main()
