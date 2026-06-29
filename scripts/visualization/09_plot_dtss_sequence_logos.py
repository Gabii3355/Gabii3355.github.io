import re
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.textpath import TextPath
from matplotlib.patches import PathPatch
from matplotlib.transforms import Affine2D
from matplotlib.font_manager import FontProperties

# ============================================================
# DTSS consensus-like sequence logo — readable version
# ============================================================
# This version DOES NOT use logomaker, because negative values in
# logomaker can make letters look inverted/upside down.
#
# Here, letters are always upright:
#   DTSS < 0  -> favorable for reaction -> above baseline
#   DTSS > 0  -> unfavorable for reaction -> below baseline
#
# Letter height is proportional to abs(DTSS), but rescaled so that
# letters are smaller and more readable.
#
# Expected input files:
#   DTSS_C_A.txt
#   DTSS_C_B.txt
#   DTSS_5mC_A.txt
#   DTSS_5mC_B.txt
#
# Accepted line formats:
#   A_pos4_G_base_H   -2.158
#   pos4_G            -2.158
#   4G                -2.158
# ============================================================

# ===== SETTINGS =====
folder_path = Path(".")
output_folder = Path("DTSS_consensus_logos")
output_folder.mkdir(exist_ok=True)

# Positions shown in the logo
selected_positions = [4, 7, 8]

# Relative labels with central cytosine at position 6
# Position 5 is excluded from analysis, therefore:
# 4 -> -2, 7 -> +1, 8 -> +2
relative_position_labels = {
    4: "-2",
    7: "+1",
    8: "+2"
}

# Continuous x-axis positions, without gaps
plot_position_map = {
    4: 1,
    7: 2,
    8: 3
}

base_order = ["A", "C", "T", "G"]

base_colors = {
    "A": "green",
    "C": "blue",
    "T": "violet",
    "G": "red"
}

# Layout:
# rows = A-DNA, B-DNA
# columns = C, 5mC
plot_layout = [
    [("C", "A"), ("5mC", "A")],
    [("C", "B"), ("5mC", "B")]
]

row_labels = ["A-DNA", "B-DNA"]

# Font sizes
axis_number_fontsize = 12
axis_label_fontsize = 14
row_label_fontsize = 14
column_header_fontsize = 15
legend_fontsize = 12

# Logo visual settings
# Increase max_stack_height if letters are too small.
# Decrease max_stack_height if letters are too large.
max_stack_height = 1.35

# Minimum letter height; values below this are not drawn.
# Use e.g. 0.05 if you want to remove almost-zero effects.
min_draw_height = 0.03

letter_width = 0.78
letter_font = FontProperties(family="DejaVu Sans", weight="bold")


# ===== FILE FINDER =====
def find_dtss_file(molecule, dna_type):
    """
    Finds files such as:
    DTSS_C_A.txt
    DTSS_C_B.txt
    DTSS_5mC_A.txt
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


# ===== PARSER =====
def parse_position_and_base(text):
    """
    Extracts position and base from strings such as:
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


# ===== LOAD DTSS FILE =====
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
            dtss = None
            for token in reversed(parts_line):
                try:
                    dtss = float(token.replace(",", "."))
                    break
                except ValueError:
                    continue

            if dtss is None:
                continue

            position, base = parse_position_and_base(line)

            if position is None or base is None:
                continue

            if position not in selected_positions:
                continue

            # Negative DTSS favors reaction. We store the original DTSS.
            data.append([
                position,
                plot_position_map[position],
                relative_position_labels[position],
                base,
                dtss
            ])

    df = pd.DataFrame(
        data,
        columns=["Position", "PlotPosition", "RelativeLabel", "Base", "DTSS"]
    )

    if not df.empty:
        df["DTSS"] = df["DTSS"].round(2)
        df.loc[df["DTSS"] == -0.0, "DTSS"] = 0.0

    return df


# ===== LETTER DRAWING =====
def draw_letter(ax, letter, x_center, y_bottom, height, color):
    """
    Draws one upright letter with a defined height in data units.
    The letter is centered at x_center and starts at y_bottom.
    """
    if height <= 0:
        return

    text_path = TextPath((0, 0), letter, size=1, prop=letter_font)
    bbox = text_path.get_extents()

    original_width = bbox.width
    original_height = bbox.height

    if original_width == 0 or original_height == 0:
        return

    scale_y = height / original_height
    scale_x = letter_width / original_width

    # Use the smaller x scale if letter would be too wide
    scale = min(scale_x, scale_y)

    scaled_width = original_width * scale
    scaled_height = original_height * scale

    x_left = x_center - scaled_width / 2
    y_shift = y_bottom

    transform = (
        Affine2D()
        .translate(-bbox.x0, -bbox.y0)
        .scale(scale, scale)
        .translate(x_left, y_shift)
        + ax.transData
    )

    patch = PathPatch(
        text_path,
        transform=transform,
        facecolor=color,
        edgecolor=color,
        linewidth=0.5,
        alpha=0.95
    )

    ax.add_patch(patch)


def draw_logo_for_position(ax, position_df, x_center, scale_factor):
    """
    Draws all letters for one position.
    DTSS < 0: above baseline
    DTSS > 0: below baseline
    Letters are stacked and always upright.
    """
    favorable = []    # above baseline
    unfavorable = []  # below baseline

    for base in base_order:
        row = position_df[position_df["Base"] == base]

        if row.empty:
            continue

        dtss = float(row["DTSS"].iloc[0])
        height = abs(dtss) * scale_factor

        if height < min_draw_height:
            continue

        if dtss < 0:
            favorable.append((base, height))
        elif dtss > 0:
            unfavorable.append((base, height))

    # Draw smaller letters first and larger letters on top
    favorable = sorted(favorable, key=lambda x: x[1])
    unfavorable = sorted(unfavorable, key=lambda x: x[1])

    # Above baseline
    y = 0.0
    for base, height in favorable:
        draw_letter(ax, base, x_center, y, height, base_colors[base])
        y += height

    # Below baseline: letters remain upright, stacked downward
    y = 0.0
    for base, height in unfavorable:
        y -= height
        draw_letter(ax, base, x_center, y, height, base_colors[base])


# ===== LOAD ALL DATA TO DETERMINE SCALE =====
all_abs_values = []
all_dfs = {}

for row in plot_layout:
    for molecule, dna_type in row:
        file_path = find_dtss_file(molecule, dna_type)

        if file_path is None:
            print(f"Brak pliku: DTSS_{molecule}_{dna_type}.txt")
            continue

        df = load_dtss_file(file_path)
        all_dfs[(molecule, dna_type)] = df
        all_abs_values.extend(df["DTSS"].abs().tolist())

if len(all_abs_values) == 0:
    raise ValueError("Nie znaleziono żadnych wartości DTSS dla wybranych pozycji.")

# Scale letters so the largest single letter is readable, not huge
max_abs_dtss = max(all_abs_values)
scale_factor = max_stack_height / max_abs_dtss

# Y range is based on possible total stacked height
max_positive_stack = 0.0
max_negative_stack = 0.0

for df in all_dfs.values():
    for position in selected_positions:
        pos_df = df[df["Position"] == position]

        favorable_sum = pos_df[pos_df["DTSS"] < 0]["DTSS"].abs().sum() * scale_factor
        unfavorable_sum = pos_df[pos_df["DTSS"] > 0]["DTSS"].abs().sum() * scale_factor

        max_positive_stack = max(max_positive_stack, favorable_sum)
        max_negative_stack = max(max_negative_stack, unfavorable_sum)

ymax = max_positive_stack * 1.25
ymin = -max_negative_stack * 1.25

# Ensure minimum visible range
ymax = max(ymax, 1.0)
ymin = min(ymin, -1.0)

print("Logo scale factor:", scale_factor)
print("Y range:", ymin, ymax)


# ===== CREATE FIGURE =====
# A4 portrait
fig, axes = plt.subplots(
    2,
    2,
    figsize=(8.27, 11.69),
    sharex=True,
    sharey=True
)

x_ticks = [plot_position_map[pos] for pos in selected_positions]
x_tick_labels = [relative_position_labels[pos] for pos in selected_positions]


# ===== PLOT =====
for i, row in enumerate(plot_layout):
    for j, (molecule, dna_type) in enumerate(row):

        ax = axes[i, j]
        df = all_dfs.get((molecule, dna_type), pd.DataFrame())

        if df.empty:
            ax.text(
                0.5,
                0.5,
                "Missing data",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=12
            )
            continue

        # Baseline
        ax.axhline(0, color="black", linewidth=1.2)

        # Light background regions
        ax.axhspan(0, ymax, color="green", alpha=0.035, zorder=0)
        ax.axhspan(ymin, 0, color="red", alpha=0.035, zorder=0)

        # Draw letters for each position
        for position in selected_positions:
            pos_df = df[df["Position"] == position]
            x_center = plot_position_map[position]
            draw_logo_for_position(ax, pos_df, x_center, scale_factor)

        if i == 0:
            ax.set_title(
                molecule,
                fontsize=column_header_fontsize,
                fontweight="bold",
                pad=10
            )

        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_tick_labels, fontsize=axis_number_fontsize)

        ax.set_xlim(0.45, len(selected_positions) + 0.55)
        ax.set_ylim(ymin, ymax)

        # Hide numeric values on Y axis because this is a schematic logo plot.
        # The direction is shown by position relative to the baseline,
        # and the magnitude is shown by letter size.
        ax.set_yticklabels([])
        ax.tick_params(axis="y", left=False, labelleft=False)
        ax.tick_params(axis="x", labelsize=axis_number_fontsize)

        ax.grid(False)

        ax.text(
            0.97,
            0.94,
            "DTSS < 0: favorable",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=10,
            color="green"
        )

        ax.text(
            0.97,
            0.06,
            "DTSS > 0: unfavorable",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=10,
            color="darkred"
        )


# ===== COMMON AXIS LABELS =====
fig.text(
    0.50,
    0.075,
    "Nucleotide position relative to deamination site",
    ha="center",
    va="center",
    fontsize=axis_label_fontsize
)

fig.text(
    0.075,
    0.50,
    "Relative DTSS effect",
    ha="center",
    va="center",
    rotation=90,
    fontsize=axis_label_fontsize
)


# ===== ROW LABELS =====
row_y_positions = [0.70, 0.32]

for label, y in zip(row_labels, row_y_positions):
    fig.text(
        0.025,
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
        linewidth=4,
        label=base
    )
    legend_handles.append(handle)

fig.legend(
    legend_handles,
    ["Adenine", "Cytosine", "Thymine", "Guanine"],
    loc="lower center",
    ncol=4,
    fontsize=legend_fontsize,
    frameon=False,
    bbox_to_anchor=(0.5, 0.015)
)


# ===== MAIN TITLE =====
fig.suptitle(
    "DTSS consensus sequence logos",
    fontsize=16,
    y=0.965
)


# ===== SPACING =====
fig.subplots_adjust(
    top=0.91,
    bottom=0.13,
    left=0.14,
    right=0.98,
    hspace=0.28,
    wspace=0.14
)


# ===== SAVE =====
output_png = output_folder / "DTSS_consensus_sequence_logos_positions_4_7_8_no_y_numbers.png"
output_pdf = output_folder / "DTSS_consensus_sequence_logos_positions_4_7_8_no_y_numbers.pdf"

plt.savefig(output_png, dpi=300, bbox_inches="tight")
plt.savefig(output_pdf, bbox_inches="tight")

plt.show()
plt.close()

print(f"Zapisano PNG: {output_png}")
print(f"Zapisano PDF: {output_pdf}")
