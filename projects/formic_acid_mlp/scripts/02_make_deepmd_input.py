#!/usr/bin/env python3
"""
02_make_deepmd_input.py

Create the DeepMD-kit input.json file for training the formic acid dimer MLP.

Training data:
data/deepmd/npy_format/train

Validation data:
data/deepmd/npy_format/validation

The independent test set is not included in input.json. It is used later with dp test.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def default_project_dir() -> Path:
    """Return repository root when this script is stored in scripts/."""
    return Path(__file__).resolve().parents[1]


def build_input_config(
    train_system: Path,
    validation_system: Path,
    numb_steps: int = 50000,
) -> dict:
    """Build the DeepMD-kit input configuration."""
    return {
        "model": {
            "type_map": ["H", "C", "O"],
            "descriptor": {
                "type": "se_e2_a",
                "rcut": 6.00,
                "rcut_smth": 0.50,
                "sel": [4, 2, 4],
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
            "decay_steps": 5000,
            "start_lr": 0.001,
            "stop_lr": 3.51e-8,
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
                "systems": [str(train_system)],
                "batch_size": "auto",
            },
            "validation_data": {
                "systems": [str(validation_system)],
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create DeepMD-kit input.json for model training."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=default_project_dir(),
        help="Project root directory. Default: repository root inferred from scripts/.",
    )
    parser.add_argument(
        "--numb-steps",
        type=int,
        default=50000,
        help="Number of training steps. Default: 50000.",
    )
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    npy_dir = project_dir / "data" / "deepmd" / "npy_format"

    train_system = npy_dir / "train"
    validation_system = npy_dir / "validation"
    test_system = npy_dir / "test"

    for path in [train_system, validation_system]:
        if not path.exists():
            raise FileNotFoundError(f"Missing DeepMD npy folder: {path}")

    if not test_system.exists():
        print(f"Warning: test folder not found yet: {test_system}")
        print("The test set is not needed in input.json, but it is needed later for dp test.")

    input_json = project_dir / "input.json"
    input_config = build_input_config(
        train_system=train_system,
        validation_system=validation_system,
        numb_steps=args.numb_steps,
    )

    input_json.parent.mkdir(parents=True, exist_ok=True)

    with open(input_json, "w") as f:
        json.dump(input_config, f, indent=4)

    print("DeepMD input configuration saved to:")
    print(input_json)
    print("\nRun training from the output folder, for example:")
    print(f"mkdir -p {project_dir / 'train_out'}")
    print(f"cd {project_dir / 'train_out'}")
    print(f"dp train {input_json}")


if __name__ == "__main__":
    main()
