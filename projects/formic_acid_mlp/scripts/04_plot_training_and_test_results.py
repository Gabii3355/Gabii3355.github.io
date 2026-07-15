#!/usr/bin/env python3
"""
04_plot_training_and_test_results.py

Create plots for DeepMD training and test results.

Input files:
train_out/lcurve.out
data/deepmd/npy_format/train/set.000/energy.npy
data/deepmd/npy_format/validation/set.000/energy.npy
data/deepmd/npy_format/test/set.000/energy.npy

Output:
plots/*.png
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


def save_learning_curve_plots(lcurve_path: Path, plots_dir: Path) -> pd.DataFrame:
    """Read lcurve.out and save training/validation RMSE plots."""
    lcurve = pd.read_csv(
        lcurve_path,
        sep=r"\s+",
        comment="#",
        names=[
            "step",
            "rmse_val",
            "rmse_trn",
            "rmse_e_val",
            "rmse_e_trn",
            "rmse_f_val",
            "rmse_f_trn",
            "lr",
        ],
    )

    print("Learning curve:")
    print(lcurve.head())
    print(lcurve.tail())

    plt.figure(figsize=(8, 5))
    plt.plot(lcurve["step"], lcurve["rmse_trn"], label="Training RMSE")
    plt.plot(lcurve["step"], lcurve["rmse_val"], label="Validation RMSE")
    plt.xlabel("Training step")
    plt.ylabel("RMSE")
    plt.yscale("log")
    plt.grid(True)
    plt.legend()
    plt.title("Learning curve: training and validation RMSE")
    plt.tight_layout()
    plt.savefig(plots_dir / "learning_curve_rmse.png", dpi=300)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(lcurve["step"], lcurve["rmse_e_trn"], label="Training energy RMSE")
    plt.plot(lcurve["step"], lcurve["rmse_e_val"], label="Validation energy RMSE")
    plt.xlabel("Training step")
    plt.ylabel("Energy RMSE [eV]")
    plt.yscale("log")
    plt.grid(True)
    plt.legend()
    plt.title("Energy RMSE during training")
    plt.tight_layout()
    plt.savefig(plots_dir / "learning_curve_energy_rmse.png", dpi=300)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(lcurve["step"], lcurve["rmse_f_trn"], label="Training force RMSE")
    plt.plot(lcurve["step"], lcurve["rmse_f_val"], label="Validation force RMSE")
    plt.xlabel("Training step")
    plt.ylabel("Force RMSE [eV/Å]")
    plt.yscale("log")
    plt.grid(True)
    plt.legend()
    plt.title("Force RMSE during training")
    plt.tight_layout()
    plt.savefig(plots_dir / "learning_curve_force_rmse.png", dpi=300)
    plt.close()

    return lcurve


def save_energy_dataset_plots(
    energy_train_path: Path,
    energy_validation_path: Path,
    energy_test_path: Path,
    plots_dir: Path,
) -> None:
    """Save AIMD energy plots and histograms."""
    energy_500 = np.load(energy_train_path).flatten()
    energy_validation = np.load(energy_validation_path).flatten()
    energy_test = np.load(energy_test_path).flatten()
    energy_298 = np.concatenate([energy_validation, energy_test])

    frames_298 = np.arange(len(energy_298))
    frames_500 = np.arange(len(energy_500))

    plt.figure(figsize=(8, 5))
    plt.plot(frames_298, energy_298, label="FAD 298 K")
    plt.plot(frames_500, energy_500, label="FAD 500 K")
    plt.xlabel("Frame")
    plt.ylabel("Energy [eV]")
    plt.grid(True)
    plt.legend()
    plt.title("AIMD potential energy")
    plt.tight_layout()
    plt.savefig(plots_dir / "aimd_energy.png", dpi=300)
    plt.close()

    energy_298_rel = energy_298 - energy_298.min()
    energy_500_rel = energy_500 - energy_500.min()

    plt.figure(figsize=(8, 5))
    plt.plot(frames_298, energy_298_rel, label="FAD 298 K")
    plt.plot(frames_500, energy_500_rel, label="FAD 500 K")
    plt.xlabel("Frame")
    plt.ylabel("Relative energy [eV]")
    plt.grid(True)
    plt.legend()
    plt.title("Relative AIMD potential energy")
    plt.tight_layout()
    plt.savefig(plots_dir / "aimd_relative_energy.png", dpi=300)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.hist(energy_298, bins=40, alpha=0.6, label="FAD 298 K")
    plt.hist(energy_500, bins=40, alpha=0.6, label="FAD 500 K")
    plt.xlabel("Energy [eV]")
    plt.ylabel("Number of frames")
    plt.grid(True)
    plt.legend()
    plt.title("Energy distribution in AIMD datasets")
    plt.tight_layout()
    plt.savefig(plots_dir / "energy_histogram.png", dpi=300)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.hist(energy_298_rel, bins=40, alpha=0.6, label="FAD 298 K")
    plt.hist(energy_500_rel, bins=40, alpha=0.6, label="FAD 500 K")
    plt.xlabel("Relative energy [eV]")
    plt.ylabel("Number of frames")
    plt.grid(True)
    plt.legend()
    plt.title("Relative energy distribution in AIMD datasets")
    plt.tight_layout()
    plt.savefig(plots_dir / "relative_energy_histogram.png", dpi=300)
    plt.close()


def save_dp_test_error_plot(plots_dir: Path) -> None:
    """
    Save a bar plot of final dp test metrics.

    Values are taken from the project notebook's latest test run on the independent test set.
    """
    error_metrics = {
        "Energy MAE [eV]": 1.972925e-03,
        "Energy RMSE [eV]": 2.492732e-03,
        "Force MAE [eV/Å]": 1.909769e-02,
        "Force RMSE [eV/Å]": 2.477943e-02,
    }

    plt.figure(figsize=(8, 5))
    plt.bar(error_metrics.keys(), error_metrics.values())
    plt.ylabel("Error value")
    plt.yscale("log")
    plt.xticks(rotation=30, ha="right")
    plt.grid(True, axis="y")
    plt.title("Model prediction errors from dp test")
    plt.tight_layout()
    plt.savefig(plots_dir / "dp_test_error_metrics.png", dpi=300)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create plots for DeepMD training and testing results."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=default_project_dir(),
        help="Project root directory. Default: repository root inferred from scripts/.",
    )
    parser.add_argument(
        "--skip-test-metrics",
        action="store_true",
        help="Skip the dp test error metrics plot.",
    )
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()

    train_out_dir = project_dir / "train_out"
    npy_dir = project_dir / "data" / "deepmd" / "npy_format"
    plots_dir = project_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    lcurve_path = train_out_dir / "lcurve.out"
    energy_train_path = npy_dir / "train" / "set.000" / "energy.npy"
    energy_validation_path = npy_dir / "validation" / "set.000" / "energy.npy"
    energy_test_path = npy_dir / "test" / "set.000" / "energy.npy"

    required_files = [
        lcurve_path,
        energy_train_path,
        energy_validation_path,
        energy_test_path,
    ]

    for path in required_files:
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

    save_learning_curve_plots(lcurve_path, plots_dir)
    save_energy_dataset_plots(
        energy_train_path=energy_train_path,
        energy_validation_path=energy_validation_path,
        energy_test_path=energy_test_path,
        plots_dir=plots_dir,
    )

    if not args.skip_test_metrics:
        save_dp_test_error_plot(plots_dir)

    print("Saved plots to:")
    print(plots_dir)

    print("\nGenerated files:")
    for file in sorted(plots_dir.iterdir()):
        if file.suffix == ".png":
            print(file.name)


if __name__ == "__main__":
    main()
