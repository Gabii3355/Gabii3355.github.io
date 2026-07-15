#!/usr/bin/env python3
"""
05_analyze_lammps_trajectory.py

Analyze the LAMMPS trajectory generated with the DeepMD model.

Input files:
LAMMPS/log.lammps
LAMMPS/fad_mlp.dump

Output files:
LAMMPS/lammps_log_data.csv
LAMMPS/first_frame_atoms.csv
LAMMPS/mlp_bond_distances.csv
plots/mlp_bond_length_histogram.png
plots/mlp_potential_energy_histogram.png
plots/mlp_potential_energy_vs_step.png
plots/mlp_temperature_vs_step.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def default_project_dir() -> Path:
    """Return repository root when this script is stored in scripts/."""
    return Path(__file__).resolve().parents[1]


def resolve_lammps_dir(project_dir: Path, lammps_dir_name: str) -> Path:
    """
    Resolve LAMMPS directory.

    The current project uses LAMMPS/ by default.
    If it does not exist but mlp_simulation/ exists, use mlp_simulation/ as a fallback.
    """
    preferred = project_dir / lammps_dir_name
    fallback = project_dir / "mlp_simulation"

    if preferred.exists():
        return preferred

    if fallback.exists():
        print(f"Using fallback LAMMPS directory: {fallback}")
        return fallback

    return preferred


def read_lammps_log(log_path: Path) -> pd.DataFrame:
    """Read the thermodynamic table from log.lammps."""
    rows = []
    header = None
    reading = False

    with open(log_path, "r") as f:
        for line in f:
            parts = line.split()

            if (
                len(parts) >= 5
                and parts[0] == "Step"
                and "Temp" in parts
                and "PotEng" in parts
            ):
                header = parts
                reading = True
                continue

            if reading:
                try:
                    values = [float(x) for x in parts]

                    if len(values) == len(header):
                        rows.append(values)
                    else:
                        reading = False

                except ValueError:
                    reading = False

    if header is None:
        raise ValueError("Could not find thermo table header in log.lammps.")

    if len(rows) == 0:
        raise ValueError("Thermo table header was found, but no numeric data rows were read.")

    log_df = pd.DataFrame(rows, columns=header)

    if "Step" in log_df.columns:
        log_df["Step"] = log_df["Step"].astype(int)

    return log_df


def read_first_dump_frame(dump_path: Path) -> pd.DataFrame:
    """Read the first frame from a LAMMPS dump file."""
    with open(dump_path, "r") as f:
        lines = f.readlines()

    atom_header_idx = None
    columns = None
    natoms = None

    for i, line in enumerate(lines):
        if line.startswith("ITEM: ATOMS"):
            atom_header_idx = i
            columns = line.split()[2:]
            break

    if atom_header_idx is None or columns is None:
        raise ValueError("Could not find 'ITEM: ATOMS' section in dump file.")

    for j in range(atom_header_idx, 0, -1):
        if lines[j].startswith("ITEM: NUMBER OF ATOMS"):
            natoms = int(lines[j + 1].strip())
            break

    if natoms is None:
        raise ValueError("Could not find number of atoms in dump file.")

    atom_lines = lines[atom_header_idx + 1 : atom_header_idx + 1 + natoms]

    first_frame_df = pd.DataFrame(
        [line.split() for line in atom_lines],
        columns=columns,
    )

    for col in first_frame_df.columns:
        first_frame_df[col] = pd.to_numeric(first_frame_df[col])

    return first_frame_df


def read_lammps_dump(dump_path: Path) -> tuple[list[int], list[pd.DataFrame]]:
    """Read all frames from a LAMMPS dump file."""
    timesteps = []
    frames = []

    with open(dump_path, "r") as f:
        lines = f.readlines()

    i = 0

    while i < len(lines):
        if lines[i].startswith("ITEM: TIMESTEP"):
            step = int(lines[i + 1].strip())

            if not lines[i + 2].startswith("ITEM: NUMBER OF ATOMS"):
                raise ValueError("Unexpected dump format: missing NUMBER OF ATOMS")

            natoms = int(lines[i + 3].strip())

            atom_header_idx = None
            for j in range(i + 4, len(lines)):
                if lines[j].startswith("ITEM: ATOMS"):
                    atom_header_idx = j
                    break

            if atom_header_idx is None:
                raise ValueError("Could not find ITEM: ATOMS section")

            columns = lines[atom_header_idx].split()[2:]
            atom_lines = lines[atom_header_idx + 1 : atom_header_idx + 1 + natoms]

            frame = pd.DataFrame(
                [line.split() for line in atom_lines],
                columns=columns,
            )

            for col in frame.columns:
                frame[col] = pd.to_numeric(frame[col])

            frame = frame.sort_values("id").reset_index(drop=True)

            timesteps.append(step)
            frames.append(frame)

            i = atom_header_idx + 1 + natoms
        else:
            i += 1

    if len(frames) == 0:
        raise ValueError("No frames were read from the LAMMPS dump file.")

    return timesteps, frames


def read_type_map(project_dir: Path) -> dict[int, str]:
    """
    Read DeepMD type_map.raw and convert it to a LAMMPS type dictionary.

    Fallback:
    1 = H, 2 = C, 3 = O
    """
    type_map_path = project_dir / "data" / "deepmd" / "npy_format" / "train" / "type_map.raw"

    if type_map_path.exists():
        with open(type_map_path, "r") as f:
            symbols = f.read().split()
        return {i + 1: symbol for i, symbol in enumerate(symbols)}

    print("Warning: type_map.raw not found. Using default atom type mapping: 1=H, 2=C, 3=O")
    return {
        1: "H",
        2: "C",
        3: "O",
    }


def distance(a: np.ndarray, b: np.ndarray) -> float:
    """Euclidean distance between two atoms."""
    return float(np.linalg.norm(a - b))


def calculate_bond_lengths(
    timesteps: list[int],
    frames: list[pd.DataFrame],
    type_map: dict[int, str],
) -> pd.DataFrame:
    """Calculate selected C-H, C-O and O-H bond distances from LAMMPS dump frames."""
    bond_rules = {
        ("C", "H"): (0.8, 1.3),
        ("C", "O"): (1.0, 1.6),
        ("H", "O"): (0.7, 1.2),
    }

    bond_labels = {
        ("C", "H"): "C-H",
        ("C", "O"): "C-O",
        ("H", "O"): "O-H",
    }

    bond_records = []

    for step, frame in zip(timesteps, frames):
        required_columns = ["id", "type", "x", "y", "z"]

        for column in required_columns:
            if column not in frame.columns:
                raise ValueError(
                    f"Column '{column}' not found in dump frame. "
                    f"Available columns: {frame.columns.tolist()}"
                )

        coords = frame[["x", "y", "z"]].values
        types = frame["type"].astype(int).values
        ids = frame["id"].astype(int).values

        for i in range(len(frame)):
            for j in range(i + 1, len(frame)):
                elem_i = type_map[types[i]]
                elem_j = type_map[types[j]]

                pair = tuple(sorted([elem_i, elem_j]))
                d = distance(coords[i], coords[j])

                if pair in bond_rules:
                    d_min, d_max = bond_rules[pair]

                    if d_min <= d <= d_max:
                        bond_records.append(
                            {
                                "Step": step,
                                "Atom_i": ids[i],
                                "Atom_j": ids[j],
                                "Element_i": elem_i,
                                "Element_j": elem_j,
                                "Bond_type": bond_labels[pair],
                                "Distance_A": d,
                            }
                        )

    bond_df = pd.DataFrame(bond_records)

    if len(bond_df) == 0:
        raise ValueError("No bond distances were detected. Check atom types or distance cutoffs.")

    return bond_df


def save_lammps_plots(log_df: pd.DataFrame, bond_df: pd.DataFrame, plots_dir: Path) -> None:
    """Save trajectory analysis plots."""
    required_columns = ["Step", "Temp", "PotEng"]

    for column in required_columns:
        if column not in log_df.columns:
            raise ValueError(
                f"Column '{column}' not found in log_df. "
                f"Available columns: {log_df.columns.tolist()}"
            )

    plt.figure(figsize=(8, 5))
    for bond_type in sorted(bond_df["Bond_type"].unique()):
        subset = bond_df[bond_df["Bond_type"] == bond_type]
        plt.hist(
            subset["Distance_A"],
            bins=30,
            alpha=0.5,
            label=bond_type,
        )

    plt.xlabel("Bond distance [Å]")
    plt.ylabel("Count")
    plt.title("Distribution of selected bond lengths in MLP trajectory")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(plots_dir / "mlp_bond_length_histogram.png", dpi=300)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.hist(log_df["PotEng"], bins=30)
    plt.xlabel("Potential energy [eV]")
    plt.ylabel("Count")
    plt.title("Distribution of potential energy in MLP trajectory")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(plots_dir / "mlp_potential_energy_histogram.png", dpi=300)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(log_df["Step"], log_df["PotEng"])
    plt.xlabel("MD step")
    plt.ylabel("Potential energy [eV]")
    plt.title("LAMMPS MLP potential energy during simulation")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(plots_dir / "mlp_potential_energy_vs_step.png", dpi=300)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(log_df["Step"], log_df["Temp"])
    plt.xlabel("MD step")
    plt.ylabel("Temperature [K]")
    plt.title("Temperature during LAMMPS MLP simulation")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(plots_dir / "mlp_temperature_vs_step.png", dpi=300)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze LAMMPS log and dump files from DeepMD MLP simulation."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=default_project_dir(),
        help="Project root directory. Default: repository root inferred from scripts/.",
    )
    parser.add_argument(
        "--lammps-dir-name",
        default="LAMMPS",
        help="LAMMPS output folder name. Default: LAMMPS. Fallback: mlp_simulation.",
    )
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    lammps_dir = resolve_lammps_dir(project_dir, args.lammps_dir_name)
    plots_dir = project_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    log_path = lammps_dir / "log.lammps"
    dump_path = lammps_dir / "fad_mlp.dump"

    if not log_path.exists():
        raise FileNotFoundError(f"Cannot find log.lammps file: {log_path}")

    if not dump_path.exists():
        raise FileNotFoundError(f"Cannot find dump file: {dump_path}")

    log_df = read_lammps_log(log_path)
    log_csv = lammps_dir / "lammps_log_data.csv"
    log_df.to_csv(log_csv, index=False)

    print("LAMMPS log columns:")
    print(log_df.columns.tolist())
    print("\nFirst rows:")
    print(log_df.head())
    print("\nLast rows:")
    print(log_df.tail())
    print("\nBasic statistics:")
    print(log_df.describe())
    print("\nSaved:")
    print(log_csv)

    first_frame_df = read_first_dump_frame(dump_path)
    first_frame_csv = lammps_dir / "first_frame_atoms.csv"
    first_frame_df.to_csv(first_frame_csv, index=False)

    print("\nFirst frame atoms:")
    print(first_frame_df)
    print("\nSaved first frame table to:")
    print(first_frame_csv)

    timesteps, frames = read_lammps_dump(dump_path)

    print("\nNumber of frames read:", len(frames))
    print("First timestep:", timesteps[0])
    print("Last timestep:", timesteps[-1])
    print("Columns:", frames[0].columns.tolist())

    type_map = read_type_map(project_dir)
    print("Atom type map:", type_map)

    bond_df = calculate_bond_lengths(timesteps, frames, type_map)
    bond_csv = lammps_dir / "mlp_bond_distances.csv"
    bond_df.to_csv(bond_csv, index=False)

    print("\nDetected bond distances:")
    print(bond_df.head())
    print("Number of detected distances:", len(bond_df))
    print("Saved bond distances to:")
    print(bond_csv)

    save_lammps_plots(log_df, bond_df, plots_dir)

    print("\nSaved plots to:")
    print(plots_dir)

    print("\nGenerated files:")
    for file in sorted(plots_dir.iterdir()):
        if file.suffix == ".png":
            print(file.name)


if __name__ == "__main__":
    main()
