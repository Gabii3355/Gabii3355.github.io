#!/usr/bin/env python3
"""
Analyze a LAMMPS trajectory produced with the compressed DeepMD model.

The script reads:
  - log.lammps
  - fad_mlp.dump

and creates:
  - lammps_log_data.csv
  - rmsd_vs_first_frame.csv
  - mlp_bond_distances.csv
  - RMSD, energy, temperature and bond length plots

Example:
    python scripts/05_analyze_lammps_trajectory.py \
        --log-file lammps/log.lammps \
        --dump-file lammps/fad_mlp.dump \
        --output-dir lammps/analysis
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_TYPE_MAP = {
    1: "H",
    2: "C",
    3: "O",
}

DEFAULT_BOND_RULES = {
    ("C", "H"): (0.8, 1.3),
    ("C", "O"): (1.0, 1.6),
    ("H", "O"): (0.7, 1.2),
}


def read_lammps_log(log_path: Path) -> pd.DataFrame:
    """Read the thermodynamic table from log.lammps."""

    rows: list[list[float]] = []
    header: list[str] | None = None
    reading = False

    with log_path.open("r", encoding="utf-8", errors="replace") as file:
        for line in file:
            parts = line.split()

            if len(parts) >= 5 and parts[0] == "Step" and "Temp" in parts and "PotEng" in parts:
                header = parts
                reading = True
                continue

            if reading:
                try:
                    values = [float(item) for item in parts]
                except ValueError:
                    reading = False
                    continue

                if header is not None and len(values) == len(header):
                    rows.append(values)
                else:
                    reading = False

    if header is None:
        raise ValueError(f"Could not find LAMMPS thermodynamic table in {log_path}")

    return pd.DataFrame(rows, columns=header)


def read_lammps_dump(dump_path: Path) -> tuple[np.ndarray, list[pd.DataFrame]]:
    """Read a LAMMPS custom dump with columns including id, type, x, y, z."""

    frames: list[pd.DataFrame] = []
    timesteps: list[int] = []

    with dump_path.open("r", encoding="utf-8", errors="replace") as file:
        lines = file.readlines()

    i = 0
    while i < len(lines):
        if lines[i].strip() == "ITEM: TIMESTEP":
            step = int(lines[i + 1].strip())
            natoms = int(lines[i + 3].strip())

            atom_header_idx = None
            for j in range(i, min(i + 20, len(lines))):
                if lines[j].startswith("ITEM: ATOMS"):
                    atom_header_idx = j
                    break

            if atom_header_idx is None:
                raise ValueError("Could not find ITEM: ATOMS section in dump file.")

            columns = lines[atom_header_idx].split()[2:]
            atom_lines = lines[atom_header_idx + 1 : atom_header_idx + 1 + natoms]

            frame = pd.DataFrame(
                [line.split() for line in atom_lines],
                columns=columns,
            )

            for column in frame.columns:
                frame[column] = pd.to_numeric(frame[column])

            frame = frame.sort_values("id").reset_index(drop=True)

            timesteps.append(step)
            frames.append(frame)

            i = atom_header_idx + 1 + natoms
        else:
            i += 1

    if not frames:
        raise ValueError(f"No frames found in dump file: {dump_path}")

    return np.asarray(timesteps), frames


def get_coordinate_columns(frame: pd.DataFrame) -> list[str]:
    """Return coordinate column names."""
    if {"x", "y", "z"}.issubset(frame.columns):
        return ["x", "y", "z"]
    if {"xu", "yu", "zu"}.issubset(frame.columns):
        return ["xu", "yu", "zu"]
    raise ValueError("Dump file must contain x/y/z or xu/yu/zu coordinate columns.")


def calculate_rmsd(timesteps: np.ndarray, frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Calculate RMSD relative to the first frame, without structural alignment."""

    coord_columns = get_coordinate_columns(frames[0])
    reference = frames[0][coord_columns].to_numpy()

    rmsd_values = []
    for frame in frames:
        coords = frame[coord_columns].to_numpy()
        diff = coords - reference
        rmsd = np.sqrt(np.mean(np.sum(diff**2, axis=1)))
        rmsd_values.append(rmsd)

    return pd.DataFrame({"Step": timesteps, "RMSD_A": rmsd_values})


def calculate_bond_distances(
    timesteps: np.ndarray,
    frames: list[pd.DataFrame],
    type_map: dict[int, str],
    bond_rules: dict[tuple[str, str], tuple[float, float]],
) -> pd.DataFrame:
    """Detect selected bond lengths using simple distance windows."""

    records: list[dict] = []

    for step, frame in zip(timesteps, frames):
        coord_columns = get_coordinate_columns(frame)
        coords = frame[coord_columns].to_numpy()
        atom_types = frame["type"].astype(int).to_numpy()
        atom_ids = frame["id"].astype(int).to_numpy()

        for i in range(len(frame)):
            for j in range(i + 1, len(frame)):
                elem_i = type_map.get(atom_types[i])
                elem_j = type_map.get(atom_types[j])

                if elem_i is None or elem_j is None:
                    continue

                pair = tuple(sorted((elem_i, elem_j)))
                distance = float(np.linalg.norm(coords[i] - coords[j]))

                if pair in bond_rules:
                    d_min, d_max = bond_rules[pair]
                    if d_min <= distance <= d_max:
                        records.append(
                            {
                                "Step": step,
                                "Atom_i": atom_ids[i],
                                "Atom_j": atom_ids[j],
                                "Bond_type": f"{pair[0]}-{pair[1]}",
                                "Distance_A": distance,
                            }
                        )

    return pd.DataFrame(records)


def save_plot(path: Path, show: bool) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    if show:
        plt.show()
    plt.close()
    print(f"Saved: {path}")


def plot_rmsd(rmsd_df: pd.DataFrame, output_dir: Path, show: bool) -> None:
    plt.figure(figsize=(8, 5))
    plt.plot(rmsd_df["Step"], rmsd_df["RMSD_A"])
    plt.xlabel("MD step")
    plt.ylabel("RMSD [A]")
    plt.title("RMSD of MLP trajectory relative to the first structure")
    plt.grid(True)
    save_plot(output_dir / "mlp_rmsd_vs_first_structure.png", show)


def plot_bond_distances(bond_df: pd.DataFrame, output_dir: Path, show: bool) -> None:
    if bond_df.empty:
        print("No bond distances detected. Skipping bond histogram.")
        return

    plt.figure(figsize=(8, 5))
    for bond_type in sorted(bond_df["Bond_type"].unique()):
        subset = bond_df[bond_df["Bond_type"] == bond_type]
        plt.hist(subset["Distance_A"], bins=30, alpha=0.5, label=bond_type)

    plt.xlabel("Bond distance [A]")
    plt.ylabel("Count")
    plt.title("Distribution of selected bond lengths in MLP trajectory")
    plt.legend()
    plt.grid(True)
    save_plot(output_dir / "mlp_bond_length_histogram.png", show)


def plot_lammps_log(log_df: pd.DataFrame, output_dir: Path, show: bool) -> None:
    if "PotEng" in log_df.columns:
        plt.figure(figsize=(8, 5))
        plt.hist(log_df["PotEng"], bins=30)
        plt.xlabel("Potential energy [eV]")
        plt.ylabel("Count")
        plt.title("Distribution of potential energy in MLP trajectory")
        plt.grid(True)
        save_plot(output_dir / "mlp_potential_energy_distribution.png", show)

        plt.figure(figsize=(8, 5))
        plt.plot(log_df["Step"], log_df["PotEng"])
        plt.xlabel("MD step")
        plt.ylabel("Potential energy [eV]")
        plt.title("LAMMPS MLP potential energy during simulation")
        plt.grid(True)
        save_plot(output_dir / "mlp_potential_energy_vs_step.png", show)

    if "Temp" in log_df.columns:
        plt.figure(figsize=(8, 5))
        plt.plot(log_df["Step"], log_df["Temp"])
        plt.xlabel("MD step")
        plt.ylabel("Temperature [K]")
        plt.title("Temperature during LAMMPS MLP simulation")
        plt.grid(True)
        save_plot(output_dir / "mlp_temperature_vs_step.png", show)


def parse_type_map(items: list[str]) -> dict[int, str]:
    """Parse values like 1:H 2:C 3:O."""
    type_map: dict[int, str] = {}
    for item in items:
        key, value = item.split(":", 1)
        type_map[int(key)] = value
    return type_map


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze DeepMD LAMMPS trajectory.")
    parser.add_argument("--log-file", type=Path, default=Path("lammps/log.lammps"))
    parser.add_argument("--dump-file", type=Path, default=Path("lammps/fad_mlp.dump"))
    parser.add_argument("--output-dir", type=Path, default=Path("lammps/analysis"))
    parser.add_argument(
        "--type-map",
        nargs="+",
        default=["1:H", "2:C", "3:O"],
        help="LAMMPS atom type mapping, for example: 1:H 2:C 3:O",
    )
    parser.add_argument("--show", action="store_true", help="Display plots while saving.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    type_map = parse_type_map(args.type_map)

    print(f"Reading log file:  {args.log_file}")
    log_df = read_lammps_log(args.log_file)
    log_csv = args.output_dir / "lammps_log_data.csv"
    log_df.to_csv(log_csv, index=False)
    print(f"Saved: {log_csv}")

    print(f"Reading dump file: {args.dump_file}")
    timesteps, frames = read_lammps_dump(args.dump_file)
    print(f"Number of frames: {len(frames)}")
    print(f"Number of atoms:  {len(frames[0])}")

    rmsd_df = calculate_rmsd(timesteps, frames)
    rmsd_csv = args.output_dir / "rmsd_vs_first_frame.csv"
    rmsd_df.to_csv(rmsd_csv, index=False)
    print(f"Saved: {rmsd_csv}")

    bond_df = calculate_bond_distances(
        timesteps=timesteps,
        frames=frames,
        type_map=type_map,
        bond_rules=DEFAULT_BOND_RULES,
    )
    bond_csv = args.output_dir / "mlp_bond_distances.csv"
    bond_df.to_csv(bond_csv, index=False)
    print(f"Saved: {bond_csv}")

    plot_rmsd(rmsd_df, args.output_dir, args.show)
    plot_bond_distances(bond_df, args.output_dir, args.show)
    plot_lammps_log(log_df, args.output_dir, args.show)

    print(f"\nAnalysis files saved in: {args.output_dir}")


if __name__ == "__main__":
    main()
