# Formic acid dimer MLP scripts

Cleaned Python scripts exported from the original Jupyter notebook.

Recommended order:

```bash
python scripts/01_convert_orca_aimd_to_deepmd.py
python scripts/02_make_deepmd_input.py
dp train input.json
dp freeze -o graph.pb
dp compress -i graph.pb -o graph-compress.pb
python scripts/03_prepare_lammps_run.py
cd lammps && lmp -i in.lammps
python ../scripts/04_plot_training_and_test_results.py
python ../scripts/05_analyze_lammps_trajectory.py
```

Large raw files such as XYZ trajectories, NPY datasets, model checkpoints and LAMMPS dumps are not included here.
