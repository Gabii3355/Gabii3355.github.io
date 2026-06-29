import re
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ============================================================
# DAS vs CAMM plot for positions 4, 7 and 8
# Fixed version: ignores header lines and parses positions robustly.
# ============================================================

# ===== SETTINGS =====
folder_path = Path(".")  # folder z plikami CAMM_*.txt i Das_*.txt

output_folder = Path("Das_CAMM_lineplots_A4")
output_folder.mkdir(exist_ok=True)

plot_layout = [
    [("C", "S", "A"), ("5mC", "S", "A")],
    [("C", "TS", "A"), ("5mC", "TS", "A")],
    [("C", "S", "B"), ("5mC", "S", "B")],
    [("C", "TS", "B"), ("5mC", "TS", "B")]
]

row_labels = ["A-DNA S", "A-DNA TS", "B-DNA S", "B-DNA TS"]

# Pozycje analizowane:
# 4 -> -2, 7 -> +1, 8 -> +2
selected_positions = [4, 7, 8]
position_labels = {
    4: "-2",
    7: "+1",
    8: "+2"
}

base_colors = {
    "A": "green",
    "C": "blue",
    "T": "violet",
    "G": "red"
}

base_order = ["A", "C", "T", "G"]
base_legend_labels = ["Adenine", "Cytosine", "Thymine", "Guanine"]

axis_number_fontsize = 12
axis_label_fontsize = 14
row_label_fontsize = 14
column_header_fontsize = 14
legend_fontsize = 12

component_order = ["Das", "CAMM"]

# Na osi X: osobna grupa dla Das i osobna dla CAMM
component_x_start = {
    "Das": 1,
    "CAMM": 5
}

# Krótkie kreski dla A/C/T/G w obrębie jednej pozycji,
# żeby kolory się nie nakładały całkowicie.
base_segments = {
    "A": (-0.30, -0.16),
    "C": (-0.10,  0.04),
    "T": ( 0.10,  0.24),
    "G": ( 0.30,  0.44)
}

line_width = 3.0


# ===== FIND FILE =====
def find_component_file(component, molecule, state, dna_type):
    """
    Szuka pliku, np.:
    CAMM_C_S_A.txt
    CAMM_5mC_TS_B.txt
    Das_C_TS_A.txt
    Das_5mC_S_B.txt
    """
    target_component = component.lower()
    target_molecule = molecule.lower()
    target_state = state.lower()
    target_dna = dna_type.lower()

    for file_path in folder_path.glob("*.txt"):
        parts = file_path.stem.split("_")

        # oczekujemy np. ["CAMM", "C", "S", "A"]
        if len(parts) != 4:
            continue

        file_component, file_molecule, file_state, file_dna = parts

        if (
            file_component.lower() == target_component
            and file_molecule.lower() == target_molecule
            and file_state.lower() == target_state
            and file_dna.lower() == target_dna
        ):
            return file_path

    return None


# ===== PARSE LINE =====
def parse_position_and_base(text):
    """
    Wyciąga pozycję i nukleotyd z nazw typu:
    A_pos4_G_base_H
    pos4_G
    4G
    4_G

    Jeżeli linia jest nagłówkiem, np. zawiera "TS" zamiast pozycji,
    funkcja zwraca None, None i taka linia jest pomijana.
    """
    # pozycja: pos4, pos_4, position4, position_4
    pos_match = re.search(r"(?:pos|position)_?(\d+)", text, flags=re.IGNORECASE)

    if pos_match:
        position = int(pos_match.group(1))
    else:
        # fallback dla zapisu np. 4G albo 4_G
        compact_match = re.search(r"\b(\d+)\s*[_-]?\s*([ACTG])\b", text, flags=re.IGNORECASE)
        if not compact_match:
            return None, None
        position = int(compact_match.group(1))

    # baza po pozycji, np. pos4_G
    base_after_pos = re.search(
        r"(?:pos|position)_?\d+[_-]?([ACTG])(?:_|$|\s)",
        text,
        flags=re.IGNORECASE
    )

    if base_after_pos:
        base = base_after_pos.group(1).upper()
        return position, base

    # fallback dla zapisu 4G
    compact_base = re.search(r"\b\d+\s*[_-]?\s*([ACTG])\b", text, flags=re.IGNORECASE)
    if compact_base:
        base = compact_base.group(1).upper()
        return position, base

    # ostatni fallback: szukamy tokenów A/C/T/G, ale nie bierzemy pierwszego tokenu
    # ze wzoru A_pos4_G_base_H, bo pierwsze A może oznaczać nić/model, a nie bazę.
    parts = re.split(r"[_\-\s]+", text)
    bases = [p.upper() for p in parts if p.upper() in ["A", "C", "T", "G"]]

    if len(bases) == 0:
        return None, None

    base = bases[-1]
    return position, base


# ===== LOAD ONE FILE =====
def load_component_file(file_path, component):
    data = []

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            parts_line = line.split()

            if len(parts_line) < 2:
                continue

            # Szukamy pierwszej liczby w linii od końca, bo czasem są nagłówki/kolumny.
            value = None
            for token in reversed(parts_line):
                try:
                    value = float(token.replace(",", "."))
                    break
                except ValueError:
                    continue

            if value is None:
                continue

            # Do parsowania nazwy bierzemy całą linię, a nie tylko split_name[1],
            # żeby uniknąć błędu typu int("TS").
            position, base = parse_position_and_base(line)

            if position is None or base is None:
                continue

            if position not in selected_positions:
                continue

            data.append([component, position, position_labels[position], base, value])

    df = pd.DataFrame(
        data,
        columns=["Component", "Position", "PositionLabel", "Base", "Value"]
    )

    if not df.empty:
        df["Value"] = df["Value"].round(1)
        df.loc[df["Value"] == -0.0, "Value"] = 0.0

    return df


# ===== LOAD SYSTEM DATA =====
def load_system_data(molecule, state, dna_type):
    all_dfs = []

    for component in component_order:
        file_path = find_component_file(component, molecule, state, dna_type)

        if file_path is None:
            print(f"Brak pliku: {component}_{molecule}_{state}_{dna_type}.txt")
            continue

        df = load_component_file(file_path, component)

        if df.empty:
            print(f"Plik znaleziony, ale brak danych dla pozycji 4, 7, 8: {file_path}")
            continue

        all_dfs.append(df)

    if len(all_dfs) == 0:
        return pd.DataFrame(columns=["Component", "Position", "PositionLabel", "Base", "Value"])

    return pd.concat(all_dfs, ignore_index=True)


# ===== GLOBAL Y SCALE =====
all_values = []

for row in plot_layout:
    for molecule, state, dna_type in row:
        df = load_system_data(molecule, state, dna_type)
        all_values.extend(df["Value"].tolist())

if len(all_values) == 0:
    raise ValueError("Nie znaleziono żadnych wartości Das/CAMM dla pozycji 4, 7 i 8.")

global_ymin = min(all_values)
global_ymax = max(all_values)

y_margin = 0.12 * (global_ymax - global_ymin)
global_ymin -= y_margin
global_ymax += y_margin

print("Global Das/CAMM y scale:")
print("ymin =", global_ymin)
print("ymax =", global_ymax)


# ===== CREATE FIGURE =====
# A4 pionowo
fig, axes = plt.subplots(
    4,
    2,
    figsize=(8.27, 11.69),
    sharex=True,
    sharey=True
)

x_ticks = []
x_tick_labels = []

for component in component_order:
    start = component_x_start[component]
    for k, position in enumerate(selected_positions):
        x_ticks.append(start + k)
        x_tick_labels.append(position_labels[position])

component_label_positions = {
    "Das": component_x_start["Das"] + 1,
    "CAMM": component_x_start["CAMM"] + 1
}


# ===== PLOT =====
for i, row in enumerate(plot_layout):
    for j, (molecule, state, dna_type) in enumerate(row):

        ax = axes[i, j]
        df = load_system_data(molecule, state, dna_type)

        if df.empty:
            ax.text(
                0.5,
                0.5,
                "Missing data",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=10
            )
            ax.set_xticks(x_ticks)
            ax.set_xticklabels(x_tick_labels, fontsize=axis_number_fontsize)
            continue

        # Tło dla grup Das i CAMM
        ax.axvspan(0.5, 3.5, color="lightgray", alpha=0.20, zorder=0)
        ax.axvspan(4.5, 7.5, color="lightgray", alpha=0.35, zorder=0)

        ax.axhline(0, color="black", linewidth=0.9, zorder=1)
        ax.axvline(4.0, color="black", linewidth=0.7, alpha=0.5, zorder=1)

        for component in component_order:
            start = component_x_start[component]

            for position_idx, position in enumerate(selected_positions):
                base_x = start + position_idx

                for base in base_order:
                    value_row = df[
                        (df["Component"] == component)
                        & (df["Position"] == position)
                        & (df["Base"] == base)
                    ]

                    if value_row.empty:
                        continue

                    value = float(value_row["Value"].iloc[0])
                    x0, x1 = base_segments[base]

                    ax.hlines(
                        y=value,
                        xmin=base_x + x0,
                        xmax=base_x + x1,
                        color=base_colors[base],
                        linewidth=line_width,
                        zorder=3
                    )

        if i == 0:
            ax.set_title(
                molecule,
                fontsize=column_header_fontsize,
                fontweight="bold",
                pad=10
            )

        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_tick_labels, fontsize=axis_number_fontsize)

        ax.set_xlim(0.4, 7.6)
        ax.set_ylim(global_ymin, global_ymax)

        ax.tick_params(axis="y", labelsize=axis_number_fontsize)
        ax.tick_params(axis="x", labelsize=axis_number_fontsize)

        ax.grid(axis="y", linestyle=":", linewidth=0.6, alpha=0.7, zorder=0)

        # Podpisy Das/CAMM tylko pod dolnym wierszem
        if i == 3:
            for component, xpos in component_label_positions.items():
                ax.text(
                    xpos,
                    global_ymin - 0.13 * (global_ymax - global_ymin),
                    component,
                    ha="center",
                    va="top",
                    fontsize=axis_label_fontsize,
                    fontweight="bold",
                    clip_on=False
                )


# ===== COMMON AXIS LABELS =====
fig.text(
    0.50,
    0.070,
    "Nucleotide position relative to central cytosine (pos. 6)",
    ha="center",
    va="center",
    fontsize=axis_label_fontsize
)

fig.text(
    0.105,
    0.50,
    "Interaction energy component [kcal/mol]",
    ha="center",
    va="center",
    rotation=90,
    fontsize=axis_label_fontsize
)


# ===== ROW LABELS =====
row_y_positions = [0.835, 0.625, 0.415, 0.205]

for label, y in zip(row_labels, row_y_positions):
    fig.text(
        0.035,
        y,
        label,
        ha="center",
        va="center",
        rotation=90,
        fontsize=row_label_fontsize,
        fontweight="bold"
    )


# ===== LEGEND =====
legend_handles = []

for base in base_order:
    handle = plt.Line2D(
        [0],
        [0],
        color=base_colors[base],
        linewidth=line_width,
        label=base
    )
    legend_handles.append(handle)

fig.legend(
    legend_handles,
    base_legend_labels,
    loc="lower center",
    ncol=4,
    fontsize=legend_fontsize,
    frameon=False,
    bbox_to_anchor=(0.5, 0.015)
)


# ===== SPACING =====
fig.subplots_adjust(
    top=0.93,
    bottom=0.13,
    left=0.17,
    right=0.97,
    hspace=0.34,
    wspace=0.16
)


# ===== SAVE =====
output_png = output_folder / "Das_CAMM_positions_4_7_8_grid_A4_portrait_FIXED.png"
output_pdf = output_folder / "Das_CAMM_positions_4_7_8_grid_A4_portrait_FIXED.pdf"

plt.savefig(output_png, dpi=300, bbox_inches="tight")
plt.savefig(output_pdf, bbox_inches="tight")

plt.show()
plt.close()

print(f"Zapisano PNG: {output_png}")
print(f"Zapisano PDF: {output_pdf}")
