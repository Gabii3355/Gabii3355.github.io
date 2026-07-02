#!/usr/bin/env python3
"""
Prepare LAMMPS input files for an MLP simulation with a compressed DeepMD model.

The script creates:
  - conf.lmp
  - in.lammps

It uses the first frame from the 298 K trajectory and places the molecule in a
cubic simulation box.

Example:
    python scripts/03_prepare_lammps_run.py \
        --trajectory data/raw/trajectory_298.xyz \
        --type-map data/deepmd_npy/FAD_298/type_map.raw \
        --model graph-compress.pb \
        --output-dir lammps
"""

from __future__ import annotations

import argparse
from pathlib import Path

import ase.io


DEFAULT_MASSES = {
    "H": 1.008,
    "C": 12.011,
    "O": 15.999,
}


def read_type_symbols(type_map_path: Path) -> list[str]:
    """Read DeepMD type_map.raw, for example: H C O."""
    with type_map_path.open("r", encoding="utf-8") as file:
        return file.read().split()


def write_lammps_data(
    trajectory_path: Path,
    type_map_path: Path,
    output_path: Path,
    box_size: float,
) -> None:
    """Create LAMMPS data file from the first trajectory frame."""

    atoms = ase.io.read(str(trajectory_path), index=0, format="extxyz")
    type_symbols = read_type_symbols(type_map_path)
    type_map = {symbol: index + 1 for index, symbol in enumerate(type_symbols)}

    positions = atoms.get_positions()
    center = positions.mean(axis=0)
    positions = positions - center + box_size / 2.0

    with output_path.open("w", encoding="utf-8") as file:
        file.write("Formic acid dimer for DeepMD LAMMPS\n\n")
        file.write(f"{len(atoms)} atoms\n")
        file.write(f"{len(type_symbols)} atom types\n\n")

        file.write(f"0.0 {box_size:.6f} xlo xhi\n")
        file.write(f"0.0 {box_size:.6f} ylo yhi\n")
        file.write(f"0.0 {box_size:.6f} zlo zhi\n\n")

        file.write("Masses\n\n")
        for symbol in type_symbols:
            if symbol not in DEFAULT_MASSES:
                raise ValueError(f"No mass defined for atom symbol: {symbol}")
            file.write(f"{type_map[symbol]} {DEFAULT_MASSES[symbol]}\n")

        file.write("\nAtoms # atomic\n\n")
        for atom_id, atom in enumerate(atoms, start=1):
            symbol = atom.symbol
            atom_type = type_map[symbol]
            x, y, z = positions[atom_id - 1]
            file.write(f"{atom_id} {atom_type} {x:.10f} {y:.10f} {z:.10f}\n")


def write_lammps_input(
    output_path: Path,
    data_file: str,
    model_file: str,
    plugin_path: str,
    temperature: float,
    timestep: float,
    n_steps: int,
    thermo_freq: int,
    dump_freq: int,
    random_seed: int,
) -> None:
    """Write in.lammps for a DeepMD LAMMPS simulation."""

    plugin_line = f"plugin load {plugin_path}\n\n" if plugin_path else ""

    lammps_input = f"""{plugin_line}units           metal
boundary        p p p
atom_style      atomic

neighbor        1.0 bin
neigh_modify    every 10 delay 0 check no

read_data       {data_file}

pair_style      deepmd {model_file}
pair_coeff      * *

velocity        all create {temperature:.1f} {random_seed} mom yes rot yes dist gaussian

fix             1 all nvt temp {temperature:.1f} {temperature:.1f} 0.1
fix             2 all momentum 100 linear 1 1 1 angular

timestep        {timestep}

thermo_style    custom step temp pe ke etotal press vol
thermo          {thermo_freq}

dump            1 all custom {dump_freq} fad_mlp.dump id type x y z

run             {n_steps}
"""

    with output_path.open("w", encoding="utf-8") as file:
        file.write(lammps_input)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare LAMMPS files for DeepMD simulation.")
    parser.add_argument("--trajectory", type=Path, default=Path("data/raw/trajectory_298.xyz"))
    parser.add_argument("--type-map", type=Path, default=Path("data/deepmd_npy/FAD_298/type_map.raw"))
    parser.add_argument("--model", default="graph-compress.pb")
    parser.add_argument("--output-dir", type=Path, default=Path("lammps"))
    parser.add_argument("--box-size", type=float, default=30.0)
    parser.add_argument("--plugin-path", default="/usr/local/lib/libdeepmd_lmp.so")
    parser.add_argument("--temperature", type=float, default=298.0)
    parser.add_argument("--timestep", type=float, default=0.0005)
    parser.add_argument("--n-steps", type=int, default=10000)
    parser.add_argument("--thermo-freq", type=int, default=100)
    parser.add_argument("--dump-freq", type=int, default=100)
    parser.add_argument("--random-seed", type=int, default=12345)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    data_file = args.output_dir / "conf.lmp"
    input_file = args.output_dir / "in.lammps"

    write_lammps_data(
        trajectory_path=args.trajectory,
        type_map_path=args.type_map,
        output_path=data_file,
        box_size=args.box_size,
    )

    write_lammps_input(
        output_path=input_file,
        data_file=data_file.name,
        model_file=args.model,
        plugin_path=args.plugin_path,
        temperature=args.temperature,
        timestep=args.timestep,
        n_steps=args.n_steps,
        thermo_freq=args.thermo_freq,
        dump_freq=args.dump_freq,
        random_seed=args.random_seed,
    )

    print(f"Saved LAMMPS data file:  {data_file}")
    print(f"Saved LAMMPS input file: {input_file}")
    print("\nNext command:")
    print(f"cd {args.output_dir} && lmp -i in.lammps")


if __name__ == "__main__":
    main()
