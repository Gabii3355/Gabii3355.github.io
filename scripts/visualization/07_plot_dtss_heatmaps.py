import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Rectangle
from pathlib import Path

# ============================================================
# DTSS heatmaps grid
# ============================================================
# This script creates heatmaps for DTSS values only:
# rows = A-DNA and B-DNA
# columns = C and 5mC
#
# Expected input files:
#     DTSS_C_A.txt
#     DTSS_5mC_A.txt
#     DTSS_C_B.txt
#     DTSS_5mC_B.txt
#
# Accepted line formats:
#     A_pos4_G_base_H   -2.158
#     pos4_G            -2.158
#     4G                -2.158
#
# Position 5 is skipped from the analysis.
# Position labels are relative to central cytosine in position 6:
#     1 -> -5
#     2 -> -4
#     3 -> -3
#     4 -> -2
#     7 -> +1
#     8 -> +2
#     9 -> +3
#     10 -> +4
#     11 -> +5
# ============================================================

# ===== SETTINGS =====
folder_path = Path(".")   # folder with DTSS_*.txt files

output_folder = Path("DTSS_heatmaps_A4")
output_folder.mkdir(exist_ok=True)

# Order of nucleotides on Y axis
nucleotide_order = ["A", "C", "T", "G"]

# Grid layout:
# rows = DNA form
# columns = reacting system
row_order = ["A", "B"]
column_order = ["C", "5mC"]

row_labels = ["A-DNA", "B-DNA"]

# Position labels relative to central cytosine in position 6
relative_position_labels = {
    1: "-5",
    2: "-4",
    3: "-3",
    4: "-2",
    5: "-1",   # skipped later
    6: "0",    # central position, skipped if present
    7: "+1",
    8: "+2",
    9: "+3",
    10: "+4",
    11: "+5"
}

# Row background colors
row_background_colors = {
    "A": "#f2f2f2",
    "B": "#e4e4e4"
}

# Font sizes
annotation_fontsize = 9
axis_number_fontsize = 12
axis_label_fontsize = 14
row_label_fontsize = 14
column_header_fontsize = 15
title_fontsize = 16
colorbar_fontsize = 12


# ===== PARSE POSITION AND BASE =====
def parse_position_and_base(text):
    """
    Extracts position and nucleotide from names such as:
    A_pos4_G_base_H
    pos4_G
    4G
    4_G
    """
    pos_match = re.search(r"(?:pos|position)_?(\d+)", text, flags=re.IGNORECASE)

    if pos_match:
        position = int(pos_match.group(1))
    else:
        compact_match = re.search(r"\b(\d+)\s*[_-]?\s*([ACTG])\b", text, flags=re.IGNORECASE)
        if not compact_match:
            return None, None
        position = int(compact_match.group(1))

    base_after_pos = re.search(
        r"(?:pos|position)_?\d+[_-]?([ACTG])(?:_|$|\s)",
        text,
        flags=re.IGNORECASE
    )

    if base_after_pos:
        return position, base_after_pos.group(1).upper()

    compact_base = re.search(r"\b\d+\s*[_-]?\s*([ACTG])\b", text, flags=re.IGNORECASE)
    if compact_base:
        return position, compact_base.group(1).upper()

    parts = re.split(r"[_\-\s]+", text)
    bases = [p.upper() for p in parts if p.upper() in ["A", "C", "T", "G"]]

    if len(bases) == 0:
        return None, None

    # Last base token is safest for names like A_pos4_G_base_H
    return position, bases[-1]


# ===== FIND DTSS FILE =====
def find_dtss_file(molecule, dna_type):
    """
    Finds files such as:
    DTSS_C_A.txt
    DTSS_5mC_A.txt
    DTSS_C_B.txt
    DTSS_5mC_B.txt
    """
    target_molecule = molecule.lower()
    target_dna = dna_type.lower()

    for file_path in folder_path.glob("*.txt"):
        parts = file_path.stem.split("_")

        if len(parts) != 3:
            continue

        prefix, file_molecule, file_dna = parts

        if (
            prefix.lower() == "dtss"
            and file_molecule.lower() == target_molecule
            and file_dna.lower() == target_dna
        ):
            return file_path

    return None


# ===== LOAD ONE DTSS FILE =====
def load_dtss_file(file_path):
    data = []

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            parts_line = line.split()

            if len(parts_line) < 2:
                continue

            # Find numeric value from the end of the line
            value = None
            for token in reversed(parts_line):
                try:
                    value = float(token.replace(",", "."))
                    break
                except ValueError:
                    continue

            if value is None:
                continue

            position, nucleotide = parse_position_and_base(line)

            if position is None or nucleotide is None:
                continue

            # Skip position 5 because it was excluded from the final analysis
            if position == 5:
                continue

            # Skip central position if present
            if position == 6:
                continue

            data.append([position, nucleotide, value])

    df = pd.DataFrame(data, columns=["Position", "Nucleotide", "DTSS"])

    if df.empty:
        return pd.DataFrame(index=nucleotide_order)

    df["Position"] = df["Position"].astype(int)

    heatmap_data = df.pivot(
        index="Nucleotide",
        columns="Position",
        values="DTSS"
    )

    # Sort positions
    heatmap_data = heatmap_data.reindex(sorted(heatmap_data.columns), axis=1)

    # Set nucleotide order
    heatmap_data = heatmap_data.reindex(
        [n for n in nucleotide_order if n in heatmap_data.index]
    )

    # Round values to one decimal place
    heatmap_data = heatmap_data.round(1)

    # Remove -0.0
    heatmap_data = heatmap_data.mask(heatmap_data == -0.0, 0.0)

    return heatmap_data


# ===== COLLECT FILES AND GLOBAL COLOR SCALE =====
dtss_files = []
all_dtss_values = []

for dna_type in row_order:
    for molecule in column_order:
        file_path = find_dtss_file(molecule, dna_type)

        if file_path is None:
            print(f"Brak pliku: DTSS_{molecule}_{dna_type}.txt")
            continue

        dtss_files.append(file_path)

        heatmap_data = load_dtss_file(file_path)
        values = heatmap_data.to_numpy().flatten()
        values = [v for v in values if pd.notna(v)]
        all_dtss_values.extend(values)

if len(all_dtss_values) == 0:
    raise ValueError("Nie znaleziono żadnych wartości DTSS po pominięciu pozycji 5.")

# Symmetric color scale around zero for easier comparison
abs_max = max(abs(min(all_dtss_values)), abs(max(all_dtss_values)))
global_vmin = -abs_max
global_vmax = abs_max

print("Global DTSS color scale:")
print("vmin =", global_vmin)
print("vmax =", global_vmax)


# ===== CREATE ONE LARGE A4 LANDSCAPE FIGURE, GRID 2 x 2 =====
fig, axes = plt.subplots(
    nrows=2,
    ncols=2,
    figsize=(11.69, 8.27),
    sharex=True,
    sharey=False
)

# Common colorbar on the right
cbar_ax = fig.add_axes([0.925, 0.20, 0.018, 0.60])

# Spacing before row backgrounds
fig.subplots_adjust(
    top=0.86,
    bottom=0.14,
    left=0.145,
    right=0.895,
    hspace=0.12,
    wspace=0.05
)


# ===== ROW BACKGROUNDS =====
fig.canvas.draw()

for row_idx, dna_type in enumerate(row_order):
    left_pos = axes[row_idx, 0].get_position()
    right_pos = axes[row_idx, 1].get_position()

    x0 = left_pos.x0 - 0.012
    y0 = left_pos.y0 - 0.015
    x1 = right_pos.x1 + 0.012
    y1 = left_pos.y1 + 0.015

    rect = Rectangle(
        (x0, y0),
        x1 - x0,
        y1 - y0,
        transform=fig.transFigure,
        facecolor=row_background_colors[dna_type],
        edgecolor="none",
        zorder=-10
    )

    fig.patches.append(rect)


# ===== PLOT HEATMAPS =====
for row_idx, dna_type in enumerate(row_order):
    for col_idx, molecule in enumerate(column_order):

        ax = axes[row_idx, col_idx]
        ax.set_facecolor(row_background_colors[dna_type])

        file_path = find_dtss_file(molecule, dna_type)

        if file_path is None:
            print(f"Brak pliku: DTSS_{molecule}_{dna_type}.txt")
            ax.set_visible(False)
            continue

        heatmap_data = load_dtss_file(file_path)

        # X labels = relative positions
        x_labels = [
            relative_position_labels.get(int(pos), str(pos))
            for pos in heatmap_data.columns
        ]

        show_cbar = (row_idx == 0 and col_idx == 1)

        hm = sns.heatmap(
            heatmap_data,
            annot=True,
            cmap="coolwarm",
            center=0,
            vmin=global_vmin,
            vmax=global_vmax,
            linewidths=0.5,
            linecolor="white",
            fmt=".1f",
            ax=ax,
            cbar=show_cbar,
            cbar_ax=cbar_ax if show_cbar else None,
            cbar_kws={"label": "DTSS [kcal/mol]"},
            annot_kws={"fontsize": annotation_fontsize}
        )

        # No individual heatmap titles
        ax.set_title("")

        # Y labels: letters only in the left column
        y_positions = [i + 0.5 for i in range(len(nucleotide_order))]
        ax.set_yticks(y_positions)

        if col_idx == 0:
            ax.set_ylabel("")
            ax.set_yticklabels(nucleotide_order, rotation=0, fontsize=axis_number_fontsize)
            ax.tick_params(axis="y", labelsize=axis_number_fontsize, labelleft=True, left=True, pad=3)
        else:
            ax.set_ylabel("")
            ax.set_yticklabels([])
            ax.tick_params(axis="y", labelleft=False, left=False)

        # X tick labels
        ax.set_xlabel("")
        ax.set_xticklabels(x_labels, rotation=0, fontsize=axis_number_fontsize)
        ax.tick_params(axis="x", labelsize=axis_number_fontsize)

        # Borders
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(0.9)
            spine.set_color("black")


# ===== COLORBAR FORMAT =====
cbar = axes[0, 1].collections[0].colorbar
if cbar is not None:
    cbar.ax.tick_params(labelsize=axis_number_fontsize)
    cbar.set_label("DTSS [kcal/mol]", fontsize=colorbar_fontsize)


# ===== COLUMN HEADERS =====
for col_idx, label in enumerate(column_order):
    pos = axes[0, col_idx].get_position()
    x = (pos.x0 + pos.x1) / 2
    fig.text(
        x,
        0.900,
        label,
        ha="center",
        va="center",
        fontsize=column_header_fontsize,
        fontweight="bold"
    )


# ===== ROW LABELS =====
for row_idx, label in enumerate(row_labels):
    pos = axes[row_idx, 0].get_position()
    y = (pos.y0 + pos.y1) / 2
    fig.text(
        0.065,
        y,
        label,
        ha="center",
        va="center",
        rotation=90,
        fontsize=row_label_fontsize,
        fontweight="bold"
    )


# ===== GLOBAL Y AXIS LABEL =====
fig.text(
    0.108,
    0.50,
    "Neighboring nucleotides",
    ha="center",
    va="center",
    rotation=90,
    fontsize=axis_label_fontsize
)


# ===== GLOBAL X AXIS LABEL =====
fig.text(
    0.515,
    0.075,
    "Nucleotide position relative to deamination site",
    ha="center",
    va="center",
    fontsize=axis_label_fontsize
)


# ===== MAIN TITLE =====
fig.suptitle("DTSS values", fontsize=title_fontsize, y=0.965)


# ===== SAVE =====
output_png = output_folder / "DTSS_heatmaps_grid_2x2_A4_landscape.png"
output_pdf = output_folder / "DTSS_heatmaps_grid_2x2_A4_landscape.pdf"

plt.savefig(output_png, dpi=300, bbox_inches="tight")
plt.savefig(output_pdf, bbox_inches="tight")

plt.show()
plt.close()

print(f"Zapisano PNG: {output_png}")
print(f"Zapisano PDF: {output_pdf}")
