from pathlib import Path
import re
from pymol import cmd

# Script for each mutant:
# - reads from the filename which position was mutated,
# - removes ONLY the nitrogenous base from that position,
# - writes separately:
# 1) the same base without additional H
# 2) the same base after adding H

#   run extract_bases.py
#   extract_mutated_bases

INPUT_DIR = Path("mutants_all")
OUTPUT_RAW_DIR = Path("bases_only_mutated_raw")
OUTPUT_H_DIR = Path("bases_only_mutated_with_H")
TEMP_OBJECT = "temp_dna"
TEMP_BASE_RAW = "temp_base_raw"
TEMP_BASE_H = "temp_base_h"
EXPECTED_COUNT = 80

# The file name must be in the following format: A_pos5_T.pdb or B_pos10_G.pdb
MUTANT_PATTERN = re.compile(r"^([AB])_pos(\d+)_([ACGT])\.pdb$", re.IGNORECASE)

BASE_ATOMS = {
    "A": ["N9", "C8", "N7", "C5", "C6", "N6", "N1", "C2", "N3", "C4"],
    "G": ["N9", "C8", "N7", "C5", "C6", "O6", "N1", "C2", "N2", "N3", "C4"],
    "C": ["N1", "C2", "O2", "N3", "C4", "N4", "C5", "C6"],
    "T": ["N1", "C2", "O2", "N3", "C4", "O4", "C5", "C5M", "C6"],
}


def _safe_delete(name):
    if name in cmd.get_names("all"):
        cmd.delete(name)


def _ensure_output_dirs():
    OUTPUT_RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_H_DIR.mkdir(parents=True, exist_ok=True)


def _mutant_files():
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Nie znaleziono katalogu: {INPUT_DIR}")

    files = []
    for path in sorted(INPUT_DIR.glob("*.pdb")):
        if MUTANT_PATTERN.match(path.name):
            files.append(path)
        else:
            print(f"Pomijam plik o niepasującej nazwie: {path.name}")
    return files


def _parse_mutant_filename(path):
    match = MUTANT_PATTERN.match(path.name)
    if not match:
        raise ValueError(f"Invalid mutant file name: {path.name}")

    model_tag = match.group(1).upper()
    position = int(match.group(2))
    base = match.group(3).upper()
    return model_tag, position, base


def _build_base_selection(object_name, position, base):
    atom_names = BASE_ATOMS[base]
    atoms_expr = "+".join(atom_names)
    return f"({object_name} and resi {position} and name {atoms_expr})"


def _extract_one(mutant_path):
    model_tag, position, base = _parse_mutant_filename(mutant_path)

    _safe_delete(TEMP_OBJECT)
    _safe_delete(TEMP_BASE_RAW)
    _safe_delete(TEMP_BASE_H)

    cmd.load(str(mutant_path), TEMP_OBJECT)

    base_selection = _build_base_selection(TEMP_OBJECT, position, base)
    atom_count = cmd.count_atoms(base_selection)
    if atom_count == 0:
        _safe_delete(TEMP_OBJECT)
        raise ValueError(
            f"No base atoms found for file {mutant_path.name} "
            f"(position {position}, base {base})."
        )

    # 1) Writing the base itself without additional H
    cmd.create(TEMP_BASE_RAW, base_selection)
    cmd.remove(f"{TEMP_BASE_RAW} and hydro")
    cmd.sort(TEMP_BASE_RAW)

    raw_name = f"{model_tag}_pos{position}_{base}_base_raw.pdb"
    raw_path = OUTPUT_RAW_DIR / raw_name
    cmd.save(str(raw_path), TEMP_BASE_RAW)

    # 2) Separate copy of the same rule and adding H
    cmd.create(TEMP_BASE_H, TEMP_BASE_RAW)
    cmd.h_add(TEMP_BASE_H)
    cmd.sort(TEMP_BASE_H)

    h_name = f"{model_tag}_pos{position}_{base}_base_H.pdb"
    h_path = OUTPUT_H_DIR / h_name
    cmd.save(str(h_path), TEMP_BASE_H)

    _safe_delete(TEMP_BASE_H)
    _safe_delete(TEMP_BASE_RAW)
    _safe_delete(TEMP_OBJECT)

    print(f"Zapisano RAW: {raw_path}")
    print(f"Zapisano H:   {h_path}")



def extract_mutated_bases():
    _ensure_output_dirs()
    files = _mutant_files()

    if not files:
        raise FileNotFoundError(
            f"No mutant files found in directory: {INPUT_DIR}"
        )

    raw_saved = 0
    h_saved = 0
    for mutant_path in files:
        _extract_one(mutant_path)
        raw_saved += 1
        h_saved += 1

    print("=" * 60)
    print(f"Done. Processed mutants: {len(files)}")
    print(f"Raw rules: {raw_saved} -> {OUTPUT_RAW_DIR}")
    print(f"Rules from H: {h_saved} -> {OUTPUT_H_DIR}")
    if raw_saved != EXPECTED_COUNT or h_saved != EXPECTED_COUNT:
        print(
           f"Warning: Expected {EXPECTED_COUNT} mutants, but saved "
           f"RAW={raw_saved}, H={h_saved}. Check the mutants_all directory."
        )
    print("=" * 60)


cmd.extend("extract_bases", extract_mutated_bases)
