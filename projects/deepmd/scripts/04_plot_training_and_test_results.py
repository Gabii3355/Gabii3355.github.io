#!/usr/bin/env python3
"""
Plot DeepMD training, AIMD energy data and final dp test metrics.

The script creates portfolio/report-ready PNG figures:
  - learning_curve_rmse.png
  - learning_curve_energy_rmse.png
  - learning_curve_force_rmse.png
  - aimd_energy_over_time.png
  - aimd_relative_energy_over_time.png
  - energy_histogram.png
  - relative_energy_histogram.png
  - dp_test_error_metrics.png

Example:
    python scripts/04_plot_training_and_test_results.py \
        --lcurve out/lcurve.out \
        --energy-298 data/deepmd_npy/FAD_298/set.000/energy.npy \
        --energy-500 data/deepmd_npy/FAD_500/set.000/energy.npy \
        --plots-dir figures
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_ERROR_METRICS = {
    "Energy MAE [eV]": 2.250587e-03,
    "Energy RMSE [eV]": 2.887742e-03,
    "Force MAE [eV/A]": 2.304947e-02,
    "Force RMSE [eV/A]": 2.941914e-02,
}


def save_or_show(path: Path, show: bool) -> None:
    """Save current matplotlib figure and optionally display it."""
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    if show:
        plt.show()
    plt.close()
    print(f"Saved: {path}")


def require_columns(data: np.ndarray, required: list[str], source: Path) -> None:
    names = data.dtype.names or ()
    missing = [column for column in required if column not in names]
    if missing:
        raise ValueError(f"Missing columns in {source}: {missing}. Available columns: {names}")


def plot_lcurve(lcurve_path: Path, plots_dir: Path, show: bool) -> None:
    """Create learning curve plots from DeepMD lcurve.out."""

    lcurve = np.genfromtxt(lcurve_path, names=True)

    require_columns(lcurve, ["step", "rmse_trn", "rmse_val"], lcurve_path)

    plt.figure(figsize=(8, 5))
    plt.plot(lcurve["step"], lcurve["rmse_trn"], label="Training RMSE")
    plt.plot(lcurve["step"], lcurve["rmse_val"], label="Validation RMSE")
    plt.xlabel("Training step")
    plt.ylabel("RMSE")
    plt.yscale("log")
    plt.grid(True)
    plt.legend()
    plt.title("Learning curve: training and validation RMSE")
    save_or_show(plots_dir / "learning_curve_rmse.png", show)

    if {"rmse_e_trn", "rmse_e_val"}.issubset(lcurve.dtype.names):
        plt.figure(figsize=(8, 5))
        plt.plot(lcurve["step"], lcurve["rmse_e_trn"], label="Training energy RMSE")
        plt.plot(lcurve["step"], lcurve["rmse_e_val"], label="Validation energy RMSE")
        plt.xlabel("Training step")
        plt.ylabel("Energy RMSE [eV]")
        plt.yscale("log")
        plt.grid(True)
        plt.legend()
        plt.title("Energy RMSE during training")
        save_or_show(plots_dir / "learning_curve_energy_rmse.png", show)

    if {"rmse_f_trn", "rmse_f_val"}.issubset(lcurve.dtype.names):
        plt.figure(figsize=(8, 5))
        plt.plot(lcurve["step"], lcurve["rmse_f_trn"], label="Training force RMSE")
        plt.plot(lcurve["step"], lcurve["rmse_f_val"], label="Validation force RMSE")
        plt.xlabel("Training step")
        plt.ylabel("Force RMSE [eV/A]")
        plt.yscale("log")
        plt.grid(True)
        plt.legend()
        plt.title("Force RMSE during training")
        save_or_show(plots_dir / "learning_curve_force_rmse.png", show)


def plot_aimd_energies(energy_298_path: Path, energy_500_path: Path, plots_dir: Path, show: bool) -> None:
    """Plot absolute and relative AIMD energy traces and histograms."""

    energy_298 = np.load(energy_298_path).flatten()
    energy_500 = np.load(energy_500_path).flatten()

    frames_298 = np.arange(len(energy_298))
    frames_500 = np.arange(len(energy_500))

    plt.figure(figsize=(8, 5))
    plt.plot(frames_298, energy_298, label="FAD 298 K")
    plt.plot(frames_500, energy_500, label="FAD 500 K")
    plt.xlabel("Frame")
    plt.ylabel("Energy [eV]")
    plt.grid(True)
    plt.legend()
    plt.title("AIMD potential energy over time")
    save_or_show(plots_dir / "aimd_energy_over_time.png", show)

    energy_298_rel = energy_298 - energy_298.min()
    energy_500_rel = energy_500 - energy_500.min()

    plt.figure(figsize=(8, 5))
    plt.plot(frames_298, energy_298_rel, label="FAD 298 K")
    plt.plot(frames_500, energy_500_rel, label="FAD 500 K")
    plt.xlabel("Frame")
    plt.ylabel("Relative energy [eV]")
    plt.grid(True)
    plt.legend()
    plt.title("Relative AIMD potential energy over time")
    save_or_show(plots_dir / "aimd_relative_energy_over_time.png", show)

    plt.figure(figsize=(8, 5))
    plt.hist(energy_298, bins=40, alpha=0.6, label="FAD 298 K")
    plt.hist(energy_500, bins=40, alpha=0.6, label="FAD 500 K")
    plt.xlabel("Energy [eV]")
    plt.ylabel("Number of frames")
    plt.grid(True)
    plt.legend()
    plt.title("Energy distribution in AIMD datasets")
    save_or_show(plots_dir / "energy_histogram.png", show)

    plt.figure(figsize=(8, 5))
    plt.hist(energy_298_rel, bins=40, alpha=0.6, label="FAD 298 K")
    plt.hist(energy_500_rel, bins=40, alpha=0.6, label="FAD 500 K")
    plt.xlabel("Relative energy [eV]")
    plt.ylabel("Number of frames")
    plt.grid(True)
    plt.legend()
    plt.title("Relative energy distribution in AIMD datasets")
    save_or_show(plots_dir / "relative_energy_histogram.png", show)


def read_metrics(metrics_csv: Path | None) -> dict[str, float]:
    """
    Read optional metrics CSV.

    Expected columns:
      - metric
      - value
    """
    if metrics_csv is None:
        return DEFAULT_ERROR_METRICS

    df = pd.read_csv(metrics_csv)
    if not {"metric", "value"}.issubset(df.columns):
        raise ValueError("Metrics CSV must contain columns: metric, value")

    return dict(zip(df["metric"], df["value"]))


def plot_error_metrics(metrics: dict[str, float], plots_dir: Path, show: bool) -> None:
    """Plot MAE/RMSE values from dp test."""

    metrics_df = pd.DataFrame(
        [{"metric": metric, "value": value} for metric, value in metrics.items()]
    )
    metrics_df.to_csv(plots_dir / "dp_test_error_metrics.csv", index=False)

    plt.figure(figsize=(8, 5))
    plt.bar(metrics.keys(), metrics.values())
    plt.ylabel("Error value")
    plt.yscale("log")
    plt.xticks(rotation=30, ha="right")
    plt.grid(True, axis="y")
    plt.title("Model prediction errors from dp test")
    save_or_show(plots_dir / "dp_test_error_metrics.png", show)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot DeepMD training and test results.")
    parser.add_argument("--lcurve", type=Path, default=Path("out/lcurve.out"))
    parser.add_argument("--energy-298", type=Path, default=Path("data/deepmd_npy/FAD_298/set.000/energy.npy"))
    parser.add_argument("--energy-500", type=Path, default=Path("data/deepmd_npy/FAD_500/set.000/energy.npy"))
    parser.add_argument("--plots-dir", type=Path, default=Path("figures"))
    parser.add_argument("--metrics-csv", type=Path, default=None)
    parser.add_argument("--show", action="store_true", help="Display plots while saving.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    args.plots_dir.mkdir(parents=True, exist_ok=True)

    plot_lcurve(args.lcurve, args.plots_dir, args.show)
    plot_aimd_energies(args.energy_298, args.energy_500, args.plots_dir, args.show)
    plot_error_metrics(read_metrics(args.metrics_csv), args.plots_dir, args.show)

    print(f"\nAll plots saved in: {args.plots_dir}")


if __name__ == "__main__":
    main()
