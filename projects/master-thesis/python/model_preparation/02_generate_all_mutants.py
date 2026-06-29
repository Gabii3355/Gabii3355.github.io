from pathlib import Path
from pymol import cmd

# run mutate_ssdna.py
# run mutate_all.py
# mutate_all

INPUT_MODELS = {
    "A": "A-DNA-prepared.pdb",
    "B": "B-DNA-prepared.pdb",
}

# Mutuje wszystkie pozycje poza centralną cytozyną reakcyjną nr 6
POSITIONS_TO_MUTATE = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11]
BASES = ["A", "C", "G", "T"]
OUTPUT_DIR = Path("mutants_all")
TEMP_OBJECT = "temp_dna"
TEMP_SELECTION = "mut_residue"


def _ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _check_input_files():
    missing = [fname for fname in INPUT_MODELS.values() if not Path(fname).exists()]
    if missing:
        raise FileNotFoundError(
            "Nie znaleziono plików wejściowych: " + ", ".join(missing)
        )


def _safe_delete(name):
    if name in cmd.get_names("all"):
        cmd.delete(name)


def _cleanup_temp_items():
    _safe_delete(TEMP_SELECTION)
    _safe_delete(TEMP_OBJECT)


def _ensure_mutate_command_available():
    try:
        commands = cmd.keyword.keys()
    except Exception:
        commands = {}

    if "mutate_ssdna" not in commands:
        raise RuntimeError(
            "Komenda 'mutate_ssdna' nie jest załadowana. "
            "Najpierw wykonaj w PyMOL: run mutate_ssdna.py"
        )


def _mutate_one(model_tag, input_pdb, position, new_base):
    _cleanup_temp_items()
    cmd.load(input_pdb, TEMP_OBJECT)

    residue_query = f"{TEMP_OBJECT} and resi {position}"
    atom_count = cmd.select(TEMP_SELECTION, residue_query)

    if atom_count <= 0:
        _cleanup_temp_items()
        raise ValueError(
            f"Selekcja jest pusta dla modelu {model_tag}, pozycji {position}. "
            f"Sprawdź numerację reszt w pliku {input_pdb}."
        )

    print(f"Mutuję model {model_tag}: pozycja {position} -> {new_base}")
    cmd.do(f"mutate_ssdna {TEMP_SELECTION}, {new_base}")
    cmd.sort()

    out_name = f"{model_tag}_pos{position}_{new_base}.pdb"
    out_path = OUTPUT_DIR / out_name
    cmd.save(str(out_path), TEMP_OBJECT)

    _cleanup_temp_items()
    print(f"Zapisano: {out_path}")


def mutate_all():
    _check_input_files()
    _ensure_output_dir()
    _ensure_mutate_command_available()

    total = 0
    for model_tag, input_pdb in INPUT_MODELS.items():
        for position in POSITIONS_TO_MUTATE:
            for new_base in BASES:
                _mutate_one(model_tag, input_pdb, position, new_base)
                total += 1

    print("=" * 60)
    print(f"Gotowe. Wygenerowano {total} struktur w katalogu: {OUTPUT_DIR}")
    print("Centralna reszta nr 6 nie była mutowana.")
    print("=" * 60)


cmd.extend("mutate_all", mutate_all)
