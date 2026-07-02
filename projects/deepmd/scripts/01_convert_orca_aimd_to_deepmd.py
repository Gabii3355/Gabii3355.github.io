#!/usr/bin/env python3
"""
Convert ORCA AIMD XYZ files to DeepMD npy datasets.

This script was cleaned up from the original notebook used for the formic acid
dimer MLP project. It reads:
  - trajectory_298.xyz and forces_298.xyz
  - trajectory_500.xyz and forces_500.xyz

and creates:
  - FAD_298/
  - FAD_500/

in DeepMD npy format.

Example:
    python scripts/01_convert_orca_aimd_to_deepmd.py \
        --trajectory-298 data/raw/trajectory_298.xyz \
        --forces-298 data/raw/forces_298.xyz \
        --trajectory-500 data/raw/trajectory_500.xyz \
        --forces-500 data/raw/forces_500.xyz \
        --output-dir data/deepmd_npy
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import ase.io
import dpdata
import numpy as np


HARTREE_TO_EV = 27.211386245988
BOHR_TO_ANGSTROM = 0.529177210903


def read_orca_forces_and_energies(
    forces_path: Path,
    atom_symbols: tuple[str, ...] = ("H", "C", "O"),
) -> tuple[np.ndarray, np.ndarray]:
    """
    Read potential energies and forces from an ORCA AIMD force XYZ file.

    Energies are converted from Hartree to eV.
    Forces are converted to eV/Angstrom.

    The script recognizes force units from the frame header:
      - Hartree/Angstrom
      - Hartree/Bohr
    """

    energies_hartree: list[float] = []
    forces_raw: list[list[float]] = []
    force_unit: str | None = None

    energy_pattern = re.compile(
        r"E_Pot\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)"
    )

    with forces_path.open("r", encoding="utf-8") as file:
        for line in file:
            line_stripped = line.strip()

            if not line_stripped:
                continue

            match = energy_pattern.search(line_stripped)
            if match:
                energies_hartree.append(float(match.group(1)))

                if "Hartree/Angstrom" in line_stripped or "Hartree/Ang" in line_stripped:
                    force_unit = "Hartree/Angstrom"
                elif "Hartree/Bohr" in line_stripped:
                    force_unit = "Hartree/Bohr"

            parts = line_stripped.split()

            if len(parts) >= 4 and parts[0] in atom_symbols:
                try:
                    fx, fy, fz = map(float, parts[1:4])
                    forces_raw.append([fx, fy, fz])
                except ValueError:
                    continue

    energies_hartree_array = np.asarray(energies_hartree, dtype=float)
    forces_raw_array = np.asarray(forces_raw, dtype=float)

    energies_ev = energies_hartree_array * HARTREE_TO_EV

    if force_unit == "Hartree/Angstrom":
        forces_ev_angstrom = forces_raw_array * HARTREE_TO_EV
    elif force_unit == "Hartree/Bohr":
        forces_ev_angstrom = forces_raw_array * (HARTREE_TO_EV / BOHR_TO_ANGSTROM)
    else:
        raise ValueError(
            f"Could not detect force units in {forces_path}. "
            "Expected header text such as 'Hartree/Angstrom' or 'Hartree/Bohr'."
        )

    return energies_ev, forces_ev_angstrom


def process_deepmd_data(
    trajectory_path: Path,
    forces_path: Path,
    output_dir: Path,
    output_name: str,
) -> None:
    """Convert one trajectory and matching ORCA force file into DeepMD npy format."""

    print(f"\nProcessing dataset: {output_name}")
    print(f"Trajectory: {trajectory_path}")
    print(f"Forces:     {forces_path}")

    ase_frames = ase.io.read(str(trajectory_path), index=":", format="extxyz")

    data = dpdata.System()
    for atoms in ase_frames:
        frame = dpdata.System(atoms, fmt="ase/structure")
        data.append(frame)

    n_frames = len(data)
    n_atoms = data.get_natoms()

    print(f"Frames in trajectory: {n_frames}")
    print(f"Atoms per frame:      {n_atoms}")

    energies_ev, forces_flat = read_orca_forces_and_energies(forces_path)

    print(f"Energies found:       {len(energies_ev)}")
    print(f"Force vectors found:  {len(forces_flat)}")

    if len(energies_ev) > n_frames:
        print(f"Warning: extra energies ignored: {len(energies_ev) - n_frames}")
        energies_ev = energies_ev[:n_frames]
    elif len(energies_ev) < n_frames:
        raise ValueError(f"Expected {n_frames} energies, found {len(energies_ev)}.")

    expected_force_vectors = n_frames * n_atoms

    if len(forces_flat) > expected_force_vectors:
        print(f"Warning: extra force vectors ignored: {len(forces_flat) - expected_force_vectors}")
        forces_flat = forces_flat[:expected_force_vectors]
    elif len(forces_flat) < expected_force_vectors:
        raise ValueError(
            f"Expected {expected_force_vectors} force vectors, found {len(forces_flat)}."
        )

    forces = forces_flat.reshape(n_frames, n_atoms, 3)

    data.data["energies"] = energies_ev
    data.data["forces"] = forces

    final_output_path = output_dir / output_name
    final_output_path.mkdir(parents=True, exist_ok=True)

    data.to_deepmd_npy(str(final_output_path))

    check_energy = np.load(final_output_path / "set.000" / "energy.npy")
    check_force = np.load(final_output_path / "set.000" / "force.npy")
    check_coord = np.load(final_output_path / "set.000" / "coord.npy")

    print(f"Saved DeepMD dataset to: {final_output_path}")
    print(f"energy.npy shape: {check_energy.shape}")
    print(f"force.npy shape:  {check_force.shape}")
    print(f"coord.npy shape:  {check_coord.shape}")
    print(f"Energy range [eV]: {check_energy.min():.6f} to {check_energy.max():.6f}")
    print(f"Force range [eV/A]: {check_force.min():.6f} to {check_force.max():.6f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert ORCA AIMD data to DeepMD npy format."
    )
    parser.add_argument("--trajectory-298", type=Path, default=Path("data/raw/trajectory_298.xyz"))
    parser.add_argument("--forces-298", type=Path, default=Path("data/raw/forces_298.xyz"))
    parser.add_argument("--trajectory-500", type=Path, default=Path("data/raw/trajectory_500.xyz"))
    parser.add_argument("--forces-500", type=Path, default=Path("data/raw/forces_500.xyz"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/deepmd_npy"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    process_deepmd_data(
        trajectory_path=args.trajectory_298,
        forces_path=args.forces_298,
        output_dir=args.output_dir,
        output_name="FAD_298",
    )

    process_deepmd_data(
        trajectory_path=args.trajectory_500,
        forces_path=args.forces_500,
        output_dir=args.output_dir,
        output_name="FAD_500",
    )


if __name__ == "__main__":
    main()
