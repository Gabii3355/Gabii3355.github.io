#!/usr/bin/env python3
"""
03_prepare_lammps_run.py

Prepare input files for a LAMMPS molecular dynamics simulation with a trained DeepMD model.

Created files:
LAMMPS/conf.lmp
LAMMPS/in.lammps

The script also copies graph-compress.pb or graph.pb from train_out/ into the LAMMPS folder
if the model file is available.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ase.io import read


def default_project_dir() -> Path:
    """Return repository root when this script is stored in scripts/."""
    return Path(__file__).resolve().parents[1]


def read_type_symbols(type_map_path: Path) -> list[str]:
    """Read atom type order from DeepMD type_map.raw."""
    with open(type_map_path, "r") as f:
        return f.read().split()


def write_lammps_conf(
    xyz_path: Path,
    type_map_path: Path,
    conf_path: Path,
    box_size: float = 30.0,
) -> None:
    """Write a simple LAMMPS atomic data file from the first XYZ frame."""
    if not xyz_path.exists():
        raise FileNotFoundError(f"Missing XYZ file: {xyz_path}")

    if not type_map_path.exists():
        raise FileNotFoundError(f"Missing type_map.raw file: {type_map_path}")

    atoms = read(str(xyz_path), index=0, format="extxyz")
    type_symbols = read_type_symbols(type_map_path)

    print("type_map:", type_symbols)

    type_map = {symbol: i + 1 for i, symbol in enumerate(type_symbols)}
    print("LAMMPS atom types:", type_map)

    positions = atoms.get_positions()
    center = positions.mean(axis=0)
    positions = positions - center + box_size / 2

    masses = {
        "H": 1.008,
        "C": 12.011,
        "O": 15.999,
    }

    for atom in atoms:
        if atom.symbol not in type_map:
            raise ValueError(f"Atom symbol {atom.symbol} not found in type_map.raw")
        if atom.symbol not in masses:
            raise ValueError(f"Mass for atom symbol {atom.symbol} is not defined")

    conf_path.parent.mkdir(parents=True, exist_ok=True)

    with open(conf_path, "w") as f:
        f.write("Formic acid dimer for DeepMD LAMMPS\n\n")

        f.write(f"{len(atoms)} atoms\n")
        f.write(f"{len(type_symbols)} atom types\n\n")

        f.write(f"0.0 {box_size:.6f} xlo xhi\n")
        f.write(f"0.0 {box_size:.6f} ylo yhi\n")
        f.write(f"0.0 {box_size:.6f} zlo zhi\n\n")

        f.write("Masses\n\n")
        for symbol in type_symbols:
            atom_type = type_map[symbol]
            f.write(f"{atom_type} {masses[symbol]:.6f} # {symbol}\n")

        f.write("\nAtoms # atomic\n\n")
        for i, atom in enumerate(atoms, start=1):
            symbol = atom.symbol
            atom_type = type_map[symbol]
            x, y, z = positions[i - 1]
            f.write(f"{i} {atom_type} {x:.10f} {y:.10f} {z:.10f}\n")


def write_lammps_input(
    input_path: Path,
    model_filename: str,
    plugin_path: str | None = "/usr/local/lib/libdeepmd_lmp.so",
    temperature: float = 298.0,
    timestep: float = 0.0005,
    run_steps: int = 10000,
    thermo_freq: int = 100,
    dump_freq: int = 100,
) -> None:
    """Write the LAMMPS input script."""
    plugin_line = ""
    if plugin_path:
        plugin_line = f"plugin load {plugin_path}\n\n"

    lammps_input = f"""{plugin_line}units           metal
boundary        p p p
atom_style      atomic

neighbor        1.0 bin
neigh_modify    every 10 delay 0 check no

read_data       conf.lmp

pair_style      deepmd {model_filename}
pair_coeff      * *

velocity        all create {temperature:.1f} 12345 mom yes rot yes dist gaussian

fix             1 all nvt temp {temperature:.1f} {temperature:.1f} 0.1
fix             2 all momentum 100 linear 1 1 1 angular

timestep        {timestep}

thermo_style    custom step temp pe ke etotal press vol
thermo          {thermo_freq}

dump            1 all custom {dump_freq} fad_mlp.dump id type x y z

run             {run_steps}
"""

    input_path.parent.mkdir(parents=True, exist_ok=True)

    with open(input_path, "w") as f:
        f.write(lammps_input)


def copy_model_file(project_dir: Path, lammps_dir: Path, requested_model: str) -> str:
    """
    Copy trained model file into LAMMPS folder.

    Returns the model filename to be used in in.lammps.
    """
    lammps_dir.mkdir(parents=True, exist_ok=True)

    candidates = [
        project_dir / "train_out" / requested_model,
        project_dir / "train_out" / "graph-compress.pb",
        project_dir / "train_out" / "graph.pb",
        project_dir / requested_model,
        project_dir / "graph-compress.pb",
        project_dir / "graph.pb",
    ]

    for source in candidates:
        if source.exists():
            destination = lammps_dir / source.name
            shutil.copy2(source, destination)
            print(f"Copied model: {source} -> {destination}")
            return source.name

    print("Warning: no graph.pb or graph-compress.pb model file was found.")
    print("The LAMMPS input file will still be written using:", requested_model)
    return requested_model


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare conf.lmp and in.lammps for DeepMD/LAMMPS simulation."
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
        help="LAMMPS output folder name. Default: LAMMPS.",
    )
    parser.add_argument(
        "--model",
        default="graph-compress.pb",
        help="Model filename to use in pair_style deepmd. Default: graph-compress.pb.",
    )
    parser.add_argument(
        "--plugin-path",
        default="/usr/local/lib/libdeepmd_lmp.so",
        help=(
            "Path to libdeepmd_lmp.so. Use an empty string to omit the plugin load line. "
            "Default: /usr/local/lib/libdeepmd_lmp.so."
        ),
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=298.0,
        help="MD simulation temperature in K. Default: 298.",
    )
    parser.add_argument(
        "--run-steps",
        type=int,
        default=10000,
        help="Number of LAMMPS MD steps. Default: 10000.",
    )
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()

    raw_dir = project_dir / "data" / "raw"
    npy_dir = project_dir / "data" / "deepmd" / "npy_format"
    lammps_dir = project_dir / args.lammps_dir_name

    xyz_path = raw_dir / "trajectory_298.xyz"
    type_map_path = npy_dir / "train" / "type_map.raw"

    conf_path = lammps_dir / "conf.lmp"
    input_path = lammps_dir / "in.lammps"

    model_filename = copy_model_file(
        project_dir=project_dir,
        lammps_dir=lammps_dir,
        requested_model=args.model,
    )

    plugin_path = args.plugin_path if args.plugin_path.strip() else None

    write_lammps_conf(
        xyz_path=xyz_path,
        type_map_path=type_map_path,
        conf_path=conf_path,
    )

    write_lammps_input(
        input_path=input_path,
        model_filename=model_filename,
        plugin_path=plugin_path,
        temperature=args.temperature,
        run_steps=args.run_steps,
    )

    print("\nSaved LAMMPS configuration file:")
    print(conf_path)
    print("\nSaved LAMMPS input file:")
    print(input_path)
    print("\nTo run LAMMPS:")
    print(f"cd {lammps_dir}")
    print("lmp -in in.lammps")


if __name__ == "__main__":
    main()
