#!/usr/bin/env python3
"""
Create DeepMD-kit input.json for the formic acid dimer MLP project.

The default settings reproduce the configuration from the original notebook:
  - descriptor: se_e2_a
  - cutoff: 6.0 Angstrom
  - descriptor neurons: [10, 20, 40]
  - fitting net neurons: [100, 100, 100]
  - training steps: 50,000
  - training data: FAD_500
  - validation data: FAD_298

Example:
    python scripts/02_make_deepmd_input.py \
        --training-system data/deepmd_npy/FAD_500 \
        --validation-system data/deepmd_npy/FAD_298 \
        --output input.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_int_list(value: str) -> list[int]:
    """Parse comma-separated integers, for example: '1,4,2'."""
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def build_input_config(
    training_system: str,
    validation_system: str,
    type_map: list[str],
    sel: list[int],
    numb_steps: int,
    start_lr: float,
    stop_lr: float,
    decay_steps: int,
) -> dict:
    """Build a DeepMD-kit input configuration dictionary."""

    return {
        "model": {
            "type_map": type_map,
            "descriptor": {
                "type": "se_e2_a",
                "rcut": 6.00,
                "rcut_smth": 0.50,
                "sel": sel,
                "neuron": [10, 20, 40],
                "resnet_dt": False,
                "axis_neuron": 4,
                "seed": 1,
            },
            "fitting_net": {
                "neuron": [100, 100, 100],
                "resnet_dt": True,
                "seed": 1,
            },
        },
        "learning_rate": {
            "type": "exp",
            "decay_steps": decay_steps,
            "start_lr": start_lr,
            "stop_lr": stop_lr,
        },
        "loss": {
            "type": "ener",
            "start_pref_e": 0.02,
            "limit_pref_e": 1,
            "start_pref_f": 1000,
            "limit_pref_f": 1,
            "start_pref_v": 0,
            "limit_pref_v": 0,
        },
        "training": {
            "training_data": {
                "systems": [training_system],
                "batch_size": "auto",
            },
            "validation_data": {
                "systems": [validation_system],
                "batch_size": "auto",
                "numb_btch": 1,
            },
            "numb_steps": numb_steps,
            "seed": 10,
            "disp_file": "lcurve.out",
            "disp_freq": 1000,
            "save_freq": 10000,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create DeepMD-kit input.json.")
    parser.add_argument("--training-system", default="data/deepmd_npy/FAD_500")
    parser.add_argument("--validation-system", default="data/deepmd_npy/FAD_298")
    parser.add_argument("--output", type=Path, default=Path("input.json"))
    parser.add_argument("--type-map", default="H,C,O")
    parser.add_argument(
        "--sel",
        default="1,4,2",
        help="Descriptor sel values. Default follows the original notebook.",
    )
    parser.add_argument("--numb-steps", type=int, default=50000)
    parser.add_argument("--start-lr", type=float, default=1.0e-3)
    parser.add_argument("--stop-lr", type=float, default=3.51e-8)
    parser.add_argument("--decay-steps", type=int, default=5000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    type_map = [item.strip() for item in args.type_map.split(",") if item.strip()]
    sel = parse_int_list(args.sel)

    config = build_input_config(
        training_system=args.training_system,
        validation_system=args.validation_system,
        type_map=type_map,
        sel=sel,
        numb_steps=args.numb_steps,
        start_lr=args.start_lr,
        stop_lr=args.stop_lr,
        decay_steps=args.decay_steps,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)

    print(f"Saved DeepMD-kit input file to: {args.output}")
    print("\nNext command:")
    print(f"dp train {args.output}")


if __name__ == "__main__":
    main()
