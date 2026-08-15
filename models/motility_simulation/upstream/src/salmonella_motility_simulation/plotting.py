"""Functions for plotting static and interactive simulation figures."""

import json
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
from salmonella_motility_simulation import classes


def panel_annotation(params: classes.MotilityParameters) -> str:
    """Build a compact annotation box for one panel."""
    return (
        f"motile {params.motile_fraction:.2f}\n"
        f"run {params.run_speed_um_s:.1f} um/s\n"
        f"reorient {params.reorientation_rate_s:.2f} 1/s\n"
        f"stall {params.stall_probability:.2f}"
    )


def _ordered_panels(
    panel_results: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    """Return deterministic phenotype/media order with matching panel list."""
    phenotypes = sorted(set(panel["phenotype"] for panel in panel_results))
    media = sorted(set(panel["medium"] for panel in panel_results))
    panel_by_key = {
        (panel["phenotype"], panel["medium"]): panel for panel in panel_results
    }

    ordered: list[dict[str, Any]] = []
    for phenotype in phenotypes:
        for medium in media:
            panel = panel_by_key.get((phenotype, medium))
            if panel is not None:
                ordered.append(panel)
    return phenotypes, media, ordered


def plot_figure(
    config: dict[str, Any], panel_results: list[dict[str, Any]], prefix: Path
) -> None:
    """Generate summary figure with one panel per simulation."""

    suffix = "tracks.png"
    png_path = prefix.parent / f"{prefix.name}_{suffix}"

    # state definitions for plotting
    state_stalled: int = config["states"]["stalled"]
    state_nonmotile: int = config["states"]["non_motile"]
    box_width_um: float = config["simulation"]["box_width_um"]
    box_height_um: float = config["simulation"]["box_height_um"]

    # get deterministic phenotype/media order from panel results
    phenotypes, media, ordered_panels = _ordered_panels(panel_results)

    # figure setup
    fig, axes = plt.subplots(
        len(phenotypes),
        len(media),
        figsize=(12, 12),
        facecolor="#f8f6f1",
        squeeze=False,
    )
    fig.subplots_adjust(
        top=0.85, bottom=0.07, left=0.12, right=0.985, hspace=0.11, wspace=0.02
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            color=ordered_panels[i * len(media)]["sim"]["params"].color,
            lw=3,
            label=p,
        )
        for i, p in enumerate(phenotypes)
    ]
    fig.suptitle(
        "Single-cell motility simulation based on experimentally observed parameters",
        fontsize=18,
        y=0.95,
    )
    fig.text(
        0.5,
        0.91,
        "Run, reorientation, and non-motile states in liquid versus agarose-like obstacle mesh",
        ha="center",
        fontsize=12,
    )
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.91),
        ncol=len(phenotypes),
        frameon=False,
        fontsize=12,
    )

    for col, medium in enumerate(media):
        axes[0, col].set_title(
            "liquid" if medium == "liquid" else "agarose-like mesh", fontsize=16, pad=10
        )

    for row, phenotype in enumerate(phenotypes):
        print(f"Plotting phenotype {phenotype} ({row + 1} of {len(phenotypes)})...")
        fig.text(
            0.15,
            1 - (0.17 + (row * 0.8 / len(phenotypes))),
            ordered_panels[row * len(media) + col]["phenotype"],
            fontsize=16,
            va="center",
            ha="right",
        )
        for col, medium in enumerate(media):
            ax = axes[row, col]
            panel = ordered_panels[row * len(media) + col]
            params = panel["sim"]["params"]
            obstacles = None if medium == "liquid" else panel["sim"]["obstacles"]
            sim = panel["sim"]
            history = sim["history"]
            state_history = sim["state_history"]
            is_motile = sim["is_motile"]

            ax.set_facecolor("#fcfbf8")
            if obstacles is not None:
                for xo, yo, ro in zip(
                    obstacles.x_um, obstacles.y_um, obstacles.r_um, strict=True
                ):
                    ax.add_patch(
                        Circle(
                            (xo, yo),
                            ro,
                            facecolor="#cfcfcf",
                            edgecolor="none",
                            zorder=0,
                        )
                    )

            for i in range(history.shape[1]):
                alpha = 0.26 if is_motile[i] else 0.09
                lw = 1.15 if is_motile[i] else 0.8
                ax.plot(
                    history[:, i, 0],
                    history[:, i, 1],
                    color=params.color,
                    alpha=alpha,
                    lw=lw,
                    zorder=1,
                )
                final_state = int(state_history[-1, i])
                marker_color = (
                    params.color if final_state != state_nonmotile else "#b9b9b9"
                )
                marker = "s" if final_state == state_stalled else "o"
                ax.scatter(
                    history[-1, i, 0],
                    history[-1, i, 1],
                    s=19,
                    color=marker_color,
                    marker=marker,
                    edgecolor="none",
                    alpha=0.95,
                    zorder=3,
                )

            ax.text(
                0.02,
                0.98,
                panel_annotation(params),
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=9.8,
                color="#202020",
                bbox=dict(
                    boxstyle="round,pad=0.25",
                    facecolor=(1, 1, 1, 0.85),
                    edgecolor="none",
                ),
            )
            ax.set_xlim(0.0, box_width_um)
            ax.set_ylim(0.0, box_height_um)
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_linewidth(1.0)
                spine.set_edgecolor("#2e2e2e")

    png_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path = png_path.with_suffix(".svg")
    fig.savefig(
        str(png_path), dpi=240, facecolor=fig.get_facecolor(), bbox_inches="tight"
    )
    print(f"Saved track figure to {png_path}")
    fig.savefig(
        str(svg_path),
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
    )
    print(f"Saved track figure to {svg_path}")

    plt.close(fig)


def plot_summary(panel_results: list[dict[str, Any]], prefix: Path) -> None:
    """Histograms of per-cell track length, one panel per medium condition."""

    png_path = prefix.parent / f"{prefix.name}_summary.png"
    svg_path = png_path.with_suffix(".svg")

    phenotypes, media, ordered_panels = _ordered_panels(panel_results)

    # compute per-cell total path length for every panel
    # history shape: (n_steps, n_cells, 2)
    track_lengths: dict[tuple[str, str], np.ndarray] = {}
    for panel in ordered_panels:
        history = panel["sim"]["history"]  # (n_steps, n_cells, 2)
        steps = np.diff(history, axis=0)  # (n_steps-1, n_cells, 2)
        lengths = np.sum(np.sqrt((steps**2).sum(axis=2)), axis=0)  # (n_cells,)
        track_lengths[(panel["phenotype"], panel["medium"])] = lengths

    n_media = len(media)
    fig, axes = plt.subplots(
        1,
        n_media,
        figsize=(5 * n_media, 4),
        facecolor="#f8f6f1",
        squeeze=False,
    )
    fig.subplots_adjust(top=0.82, bottom=0.14, left=0.09, right=0.97, wspace=0.28)
    fig.suptitle("Track length distribution per medium / strain", fontsize=14, y=0.96)

    for col, medium in enumerate(media):
        ax = axes[0, col]
        ax.set_facecolor("#fcfbf8")
        ax.set_title(
            "liquid" if medium == "liquid" else "agarose-like mesh", fontsize=12
        )
        ax.set_xlabel("Track length (µm)", fontsize=10)
        ax.set_ylabel("Cell count", fontsize=10) if col == 0 else None

        legend_handles = []
        for phenotype in phenotypes:
            lengths = track_lengths.get((phenotype, medium))
            if lengths is None:
                continue
            # Retrieve the color stored in params for this panel
            panel = next(
                p
                for p in ordered_panels
                if p["phenotype"] == phenotype and p["medium"] == medium
            )
            color = panel["sim"]["params"].color
            ax.grid(alpha=0.3, zorder=-1)
            ax.hist(
                lengths,
                bins=range(0, 600, 10),
                alpha=0.6,
                color=color,
                edgecolor="none",
            )

            legend_handles.append(Line2D([0], [0], color=color, lw=3, label=phenotype))

        ax.legend(handles=legend_handles, frameon=False, fontsize=9)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)
            spine.set_edgecolor("#2e2e2e")

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        str(png_path), dpi=180, facecolor=fig.get_facecolor(), bbox_inches="tight"
    )
    print(f"Saved summary figure to {png_path}")
    fig.savefig(str(svg_path), facecolor=fig.get_facecolor(), bbox_inches="tight")
    print(f"Saved summary figure to {svg_path}")
    plt.close(fig)


def plot_figure_html(
    config: dict[str, Any], panel_results: list[dict[str, Any]], prefix: Path
) -> Path:
    """Generate a standalone interactive HTML replay for simulated tracks."""
    html_path = prefix.parent / f"{prefix.name}_tracks.html"

    phenotypes, media, ordered_panels = _ordered_panels(panel_results)

    payload_panels: list[dict[str, Any]] = []
    for panel_index, panel in enumerate(ordered_panels):
        sim = panel["sim"]
        params = sim["params"]
        obstacles = sim["obstacles"]
        obstacle_rows: list[list[float]] = []
        if obstacles is not None and obstacles.n_obstacles > 0:
            obstacle_rows = [
                [float(x), float(y), float(r)]
                for x, y, r in zip(obstacles.x_um, obstacles.y_um, obstacles.r_um)
            ]

        payload_panels.append(
            {
                "panelIndex": panel_index,
                "phenotype": panel["phenotype"],
                "medium": panel["medium"],
                "color": params.color,
                "annotation": panel_annotation(params).splitlines(),
                "dtS": float(panel["dt_s"]),
                "durationS": float(panel["duration_s"]),
                "boxWidthUm": float(sim["box_width_um"]),
                "boxHeightUm": float(sim["box_height_um"]),
                "history": sim["history"].tolist(),
                "stateHistory": sim["state_history"].astype(int).tolist(),
                "isMotile": sim["is_motile"].astype(bool).tolist(),
                "trackLengths": np.sum(
                    np.sqrt((np.diff(sim["history"], axis=0) ** 2).sum(axis=2)), axis=0
                ).tolist(),
                "obstacles": obstacle_rows,
            }
        )

    data_payload = {
        "title": "Single-cell motility simulation based on experimentally observed parameters",
        "subtitle": "Interactive replay with phenotype/medium filters, cell-count limit, and time slider",
        "stateCodes": {
            "stalled": int(config["states"]["stalled"]),
            "nonMotile": int(config["states"]["non_motile"]),
        },
        "phenotypes": phenotypes,
        "media": media,
        "panels": payload_panels,
    }

    html_template = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Motility simulation interactive replay</title>
    <style>
        :root {
            --ink: #15202b;
            --muted: #5d707f;
            --line: #dce5ea;
            --paper: #f5f8fa;
            --card: #ffffff;
            --teal: #0f766e;
            --shadow: 0 16px 35px rgba(13, 38, 53, 0.11);
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            color: var(--ink);
            background:
                radial-gradient(circle at 12% 8%, rgba(15, 118, 110, 0.16), transparent 28rem),
                radial-gradient(circle at 92% 18%, rgba(0, 114, 178, 0.12), transparent 24rem),
                linear-gradient(135deg, #edf3f6 0%, #f8fbfc 52%, #eef3f6 100%);
            font-family: Avenir Next, Avenir, Helvetica Neue, Helvetica, Arial, sans-serif;
            min-height: 100vh;
        }

        .shell {
            max-width: 1520px;
            margin: 0 auto;
            padding: 24px;
        }

        h1 {
            font-size: clamp(1.7rem, 2.8vw, 3rem);
            margin: 0;
            letter-spacing: -0.03em;
        }

        .subtitle {
            color: var(--muted);
            margin: 10px 0 18px;
            font-size: 1.01rem;
        }

        .controls {
            background: rgba(255, 255, 255, 0.87);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: var(--shadow);
            padding: 14px;
            margin-bottom: 16px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 12px;
        }

        .control-box {
            background: #f7fafc;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 10px 12px;
        }

        .label {
            font-size: 0.78rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            font-weight: 800;
            color: #2a404b;
            margin-bottom: 8px;
        }

        .options {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .option {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 4px 8px;
            border: 1px solid #d8e2e8;
            border-radius: 999px;
            background: #fff;
            font-size: 0.92rem;
        }

        .option input { accent-color: var(--teal); }

        input[type=\"range\"] {
            width: 100%;
            accent-color: var(--teal);
        }

        .value {
            color: #1f3945;
            font-weight: 800;
            font-variant-numeric: tabular-nums;
            margin-left: 6px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 14px;
        }

        .panel {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: var(--shadow);
            padding: 10px;
        }

        .panel-title {
            font-weight: 800;
            font-size: 1rem;
            margin: 0 0 8px;
            color: #16303d;
        }

        canvas {
            width: 100%;
            height: auto;
            aspect-ratio: 1.54;
            display: block;
            border-radius: 12px;
            border: 1px solid #ced7df;
            background: #fff;
        }

        .hint {
            color: var(--muted);
            font-size: 0.88rem;
            margin-top: 8px;
        }

        .summary-wrap {
            margin-top: 16px;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 14px;
            margin-top: 10px;
        }

        .summary-canvas {
            width: 100%;
            height: auto;
            aspect-ratio: 1.7;
        }
    </style>
</head>
<body>
    <main class="shell">
        <h1 id="title"></h1>
        <p class="subtitle" id="subtitle"></p>

        <section class="controls">
            <div class="control-box">
                <div class="label">Phenotype</div>
                <div class="options" id="phenotypeOptions"></div>
            </div>
            <div class="control-box">
                <div class="label">Medium</div>
                <div class="options" id="mediumOptions"></div>
            </div>
            <div class="control-box">
                <div class="label">Visible cells <span id="cellsValue" class="value"></span></div>
                <input id="cellsSlider" type="range" min="1" max="1" step="1" value="1">
            </div>
            <div class="control-box">
                <div class="label">Visible duration <span id="timeValue" class="value"></span></div>
                <input id="timeSlider" type="range" min="0" max="1" step="1" value="1">
            </div>
        </section>

        <section class="grid" id="panelGrid"></section>
        <p class="hint">Tip: move the time slider to replay track evolution and use phenotype/medium filters to focus on selected subgroups.</p>

        <section class="summary-grid" id="summaryGrid"></section>
    </main>

    <script>
        "use strict";

        const DATA = __DATA__;
        const PANEL_W = 740;
        const PANEL_H = 480;

        const state = {
            phenotypes: new Set(DATA.phenotypes),
            media: new Set(DATA.media),
            cells: 1,
            step: 0,
        };

        const grid = document.getElementById("panelGrid");
        const summaryGrid = document.getElementById("summaryGrid");
        const summarySection = document.getElementById("summarySection");
        const cards = new Map();
        const summaryCards = new Map();

        function makeCheckboxRow(value, checked, onChange) {
            const label = document.createElement("label");
            label.className = "option";
            const input = document.createElement("input");
            input.type = "checkbox";
            input.checked = checked;
            input.addEventListener("change", () => onChange(input.checked));
            const text = document.createElement("span");
            text.textContent = value;
            label.append(input, text);
            return label;
        }

        function setupOptionControls() {
            const phenotypeOptions = document.getElementById("phenotypeOptions");
            const mediumOptions = document.getElementById("mediumOptions");

            for (const phenotype of DATA.phenotypes) {
                phenotypeOptions.appendChild(
                    makeCheckboxRow(phenotype, true, (checked) => {
                        if (checked) {
                            state.phenotypes.add(phenotype);
                        } else if (state.phenotypes.size > 1) {
                            state.phenotypes.delete(phenotype);
                        }
                        applyVisibilityAndRedraw();
                    })
                );
            }

            for (const medium of DATA.media) {
                mediumOptions.appendChild(
                    makeCheckboxRow(medium, true, (checked) => {
                        if (checked) {
                            state.media.add(medium);
                        } else if (state.media.size > 1) {
                            state.media.delete(medium);
                        }
                        applyVisibilityAndRedraw();
                    })
                );
            }
        }

        function worldToCanvas(p, panel) {
            return {
                x: (p[0] / panel.boxWidthUm) * PANEL_W,
                y: (p[1] / panel.boxHeightUm) * PANEL_H,
            };
        }

        function drawPanel(card, panel) {
            const canvas = card.querySelector("canvas");
            const ctx = canvas.getContext("2d");
            canvas.width = PANEL_W;
            canvas.height = PANEL_H;

            ctx.clearRect(0, 0, PANEL_W, PANEL_H);
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, PANEL_W, PANEL_H);

            for (const obstacle of panel.obstacles) {
                const center = worldToCanvas(obstacle, panel);
                const r = (obstacle[2] / panel.boxWidthUm) * PANEL_W;
                ctx.beginPath();
                ctx.fillStyle = "#cfcfcf";
                ctx.arc(center.x, center.y, r, 0, Math.PI * 2);
                ctx.fill();
            }

            const maxStep = Math.min(state.step, panel.history.length - 1);
            const maxCells = Math.min(state.cells, panel.isMotile.length);
            const stateStalled = DATA.stateCodes.stalled;
            const stateNonMotile = DATA.stateCodes.nonMotile;

            for (let i = 0; i < maxCells; i += 1) {
                ctx.beginPath();
                const first = worldToCanvas(panel.history[0][i], panel);
                ctx.moveTo(first.x, first.y);
                for (let step = 1; step <= maxStep; step += 1) {
                    const point = worldToCanvas(panel.history[step][i], panel);
                    ctx.lineTo(point.x, point.y);
                }
                const motile = panel.isMotile[i];
                ctx.strokeStyle = panel.color;
                ctx.globalAlpha = motile ? 0.26 : 0.09;
                ctx.lineWidth = motile ? 2.0 : 1.2;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                ctx.stroke();

                const end = worldToCanvas(panel.history[maxStep][i], panel);
                const finalState = panel.stateHistory[maxStep][i];
                const markerColor = finalState === stateNonMotile ? "#b9b9b9" : panel.color;
                ctx.fillStyle = markerColor;
                ctx.globalAlpha = 0.95;
                if (finalState === stateStalled) {
                    const s = 8;
                    ctx.fillRect(end.x - s / 2, end.y - s / 2, s, s);
                } else {
                    ctx.beginPath();
                    ctx.arc(end.x, end.y, motile ? 4 : 3, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
            ctx.globalAlpha = 1;

            ctx.fillStyle = "rgba(255,255,255,0.85)";
            ctx.fillRect(10, 10, 198, 98);
            ctx.fillStyle = "#202020";
            ctx.font = "700 18px Avenir Next, Helvetica, Arial, sans-serif";
            for (let i = 0; i < panel.annotation.length; i += 1) {
                ctx.fillText(panel.annotation[i], 18, 34 + i * 22);
            }
        }

        function applyVisibilityAndRedraw() {
            let anyVisibleTrack = false;
            for (const panel of DATA.panels) {
                const card = cards.get(panel.panelIndex);
                if (!card) continue;
                const visible = state.phenotypes.has(panel.phenotype) && state.media.has(panel.medium);
                card.style.display = visible ? "block" : "none";
                if (visible) {
                    anyVisibleTrack = true;
                    drawPanel(card, panel);
                }
            }
            drawSummaryPanels();
            summarySection.style.display = anyVisibleTrack ? "block" : "none";
        }

        function computeVisibleTrackLengths(panel) {
            const maxStep = Math.min(state.step, panel.history.length - 1);
            const maxCells = Math.min(state.cells, panel.isMotile.length);
            const lengths = [];

            for (let i = 0; i < maxCells; i += 1) {
                let total = 0;
                for (let step = 1; step <= maxStep; step += 1) {
                    const prev = panel.history[step - 1][i];
                    const curr = panel.history[step][i];
                    const dx = curr[0] - prev[0];
                    const dy = curr[1] - prev[1];
                    total += Math.hypot(dx, dy);
                }
                lengths.push(total);
            }
            return lengths;
        }

        function drawSummaryCard(card, medium) {
            const canvas = card.querySelector("canvas");
            const ctx = canvas.getContext("2d");
            canvas.width = PANEL_W;
            canvas.height = 420;

            const visiblePanels = DATA.panels.filter(
                (p) =>
                    p.medium === medium &&
                    state.phenotypes.has(p.phenotype) &&
                    state.media.has(p.medium)
            );

            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            if (visiblePanels.length === 0) {
                card.style.display = "none";
                return;
            }
            card.style.display = "block";

            const visiblePanelData = visiblePanels.map((panel) => ({
                panel,
                lengths: computeVisibleTrackLengths(panel),
            }));

            let maxLength = 0;
            for (const { lengths } of visiblePanelData) {
                for (const len of lengths) {
                    if (len > maxLength) maxLength = len;
                }
            }
            maxLength = Math.max(maxLength, 10);

            const bins = 20;
            const binWidth = maxLength / bins;
            const allCounts = [];
            const perPanelCounts = [];

            for (const { panel, lengths } of visiblePanelData) {
                const counts = new Array(bins).fill(0);
                for (const len of lengths) {
                    const idx = Math.min(Math.floor(len / binWidth), bins - 1);
                    counts[idx] += 1;
                }
                perPanelCounts.push({ panel, counts });
                allCounts.push(...counts);
            }

            const maxCount = Math.max(...allCounts, 1);
            const margin = { left: 56, right: 16, top: 16, bottom: 42 };
            const chartW = canvas.width - margin.left - margin.right;
            const chartH = canvas.height - margin.top - margin.bottom;

            ctx.strokeStyle = "#d6e0e6";
            ctx.lineWidth = 1;
            for (let i = 0; i <= 4; i += 1) {
                const y = margin.top + (chartH * i) / 4;
                ctx.beginPath();
                ctx.moveTo(margin.left, y);
                ctx.lineTo(margin.left + chartW, y);
                ctx.stroke();
            }

            const barGroupWidth = chartW / bins;
            const barWidth = (barGroupWidth * 0.88) / perPanelCounts.length;
            perPanelCounts.forEach(({ panel, counts }, panelIdx) => {
                ctx.fillStyle = panel.color;
                ctx.globalAlpha = 0.58;
                for (let b = 0; b < bins; b += 1) {
                    const count = counts[b];
                    if (count === 0) continue;
                    const h = (count / maxCount) * chartH;
                    const x = margin.left + b * barGroupWidth + panelIdx * barWidth;
                    const y = margin.top + chartH - h;
                    ctx.fillRect(x, y, Math.max(barWidth - 1, 1), h);
                }
            });
            ctx.globalAlpha = 1;

            ctx.strokeStyle = "#314552";
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.moveTo(margin.left, margin.top);
            ctx.lineTo(margin.left, margin.top + chartH);
            ctx.lineTo(margin.left + chartW, margin.top + chartH);
            ctx.stroke();

            ctx.fillStyle = "#1d313d";
            ctx.font = "700 13px Avenir Next, Helvetica, Arial, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("Track length (um)", margin.left + chartW / 2, canvas.height - 12);
            ctx.save();
            ctx.translate(16, margin.top + chartH / 2);
            ctx.rotate(-Math.PI / 2);
            ctx.fillText("Cell count", 0, 0);
            ctx.restore();

            ctx.font = "12px Avenir Next, Helvetica, Arial, sans-serif";
            ctx.textAlign = "left";
            ctx.fillText("0", margin.left - 8, margin.top + chartH + 14);
            ctx.textAlign = "right";
            ctx.fillText(String(Math.round(maxLength)), margin.left + chartW, margin.top + chartH + 14);

            const legendY = margin.top + 4;
            let legendX = margin.left + 6;
            ctx.textAlign = "left";
            ctx.font = "12px Avenir Next, Helvetica, Arial, sans-serif";
            for (const { panel } of perPanelCounts) {
                ctx.fillStyle = panel.color;
                ctx.fillRect(legendX, legendY, 11, 11);
                legendX += 15;
                ctx.fillStyle = "#20333f";
                ctx.fillText(panel.phenotype, legendX, legendY + 10);
                legendX += ctx.measureText(panel.phenotype).width + 14;
            }
        }

        function drawSummaryPanels() {
            for (const medium of DATA.media) {
                const card = summaryCards.get(medium);
                if (!card) continue;
                drawSummaryCard(card, medium);
            }
        }

        function setupSliders() {
            const maxCells = Math.max(...DATA.panels.map((panel) => panel.isMotile.length));
            const maxStep = Math.max(...DATA.panels.map((panel) => panel.history.length - 1));
            const dtS = DATA.panels[0].dtS;

            const cellsSlider = document.getElementById("cellsSlider");
            const cellsValue = document.getElementById("cellsValue");
            const timeSlider = document.getElementById("timeSlider");
            const timeValue = document.getElementById("timeValue");

            cellsSlider.max = String(maxCells);
            cellsSlider.value = String(maxCells);
            state.cells = maxCells;
            cellsValue.textContent = String(maxCells);

            timeSlider.max = String(maxStep);
            timeSlider.value = String(maxStep);
            state.step = maxStep;
            timeValue.textContent = `${(maxStep * dtS).toFixed(2)} s`;

            cellsSlider.addEventListener("input", () => {
                state.cells = Number(cellsSlider.value);
                cellsValue.textContent = String(state.cells);
                applyVisibilityAndRedraw();
            });

            timeSlider.addEventListener("input", () => {
                state.step = Number(timeSlider.value);
                timeValue.textContent = `${(state.step * dtS).toFixed(2)} s`;
                applyVisibilityAndRedraw();
            });
        }

        function renderCards() {
            grid.innerHTML = "";
            for (const phenotype of DATA.phenotypes) {
                for (const medium of DATA.media) {
                    const panel = DATA.panels.find(
                        (p) => p.phenotype === phenotype && p.medium === medium
                    );
                    if (!panel) continue;

                    const card = document.createElement("article");
                    card.className = "panel";
                    const title = document.createElement("h3");
                    title.className = "panel-title";
                    title.textContent = `${panel.phenotype} / ${panel.medium}`;
                    const canvas = document.createElement("canvas");
                    canvas.setAttribute("aria-label", `${panel.phenotype} ${panel.medium} tracks`);
                    card.append(title, canvas);
                    grid.appendChild(card);
                    cards.set(panel.panelIndex, card);
                }
            }
        }

        function renderSummaryCards() {
            summaryGrid.innerHTML = "";
            for (const medium of DATA.media) {
                const card = document.createElement("article");
                card.className = "panel";
                const title = document.createElement("h3");
                title.className = "panel-title";
                title.textContent = `Track lengths / ${medium}`;
                const canvas = document.createElement("canvas");
                canvas.className = "summary-canvas";
                canvas.setAttribute("aria-label", `${medium} track length summary`);
                card.append(title, canvas);
                summaryGrid.appendChild(card);
                summaryCards.set(medium, card);
            }
        }

        function init() {
            document.getElementById("title").textContent = DATA.title;
            document.getElementById("subtitle").textContent = DATA.subtitle;
            setupOptionControls();
            renderCards();
            renderSummaryCards();
            setupSliders();
            applyVisibilityAndRedraw();
        }

        init();
    </script>
</body>
</html>
"""

    html = html_template.replace(
        "__DATA__", json.dumps(data_payload, separators=(",", ":"))
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    return html_path
