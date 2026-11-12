
#!/usr/bin/env python3
"""Compare ALF FOM and extrapolated MD/QM/ML times across node counts."""

import argparse
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


STAGES = {
    "md": "MD Sampling",
    "qm": "QM Labeling",
    "ml": "ML Training",
}

def set_sparse_xticks(ax, values, max_ticks=6):
    """Keep a readable subset of measured x coordinates."""

    values = sorted(set(values))

    if len(values) > max_ticks:
        indices = [
            round(i * (len(values) - 1) / (max_ticks - 1))
            for i in range(max_ticks)
        ]

        values = [
            values[i]
            for i in sorted(set(indices))
        ]

    ax.set_xticks(values)


def setup_plot(ax, nodes, ylabel, title):
    """Apply common formatting to node-count plots."""

    ax.set_xlabel("Number of Nodes")
    ax.set_ylabel(ylabel)
    ax.set_title(title)

    set_sparse_xticks(ax, nodes)

    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend()


def plot_fom(results, output_file):
    """Plot measured FOM and ideal linear scaling."""

    nodes = [r["nodes"] for r in results]

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(
        nodes,
        [r["fom"] for r in results],
        "o-",
        linewidth=2,
        label="Measured FOM",
    )

    ax.plot(
        nodes,
        [r["ideal_fom"] for r in results],
        "--",
        linewidth=2,
        label="Ideal Linear Scaling",
    )

    setup_plot(
        ax,
        nodes,
        "Force Components Learned per Hour",
        "ALF Figure of Merit Scaling",
    )

    fig.tight_layout()
    fig.savefig(output_file, dpi=300)
    plt.close(fig)


def plot_efficiency(results, output_file):
    """Plot overall FOM scaling efficiency."""

    nodes = [r["nodes"] for r in results]

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(
        nodes,
        [r["efficiency_percent"] for r in results],
        "o-",
        linewidth=2,
        label="Measured Efficiency",
    )

    ax.axhline(
        100,
        color="gray",
        linestyle="--",
        label="Ideal Linear Scaling (100%)",
    )

    setup_plot(
        ax,
        nodes,
        "Scaling Efficiency (%)",
        "ALF FOM Scaling Efficiency",
    )

    fig.tight_layout()
    fig.savefig(output_file, dpi=300)
    plt.close(fig)


def plot_stage_time(results, stage, output_file):
    """Plot extrapolated stage time versus number of nodes."""

    nodes = [r["nodes"] for r in results]

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(
        nodes,
        [r[f"{stage}_time_hours"] for r in results],
        "o-",
        linewidth=2,
        label="Measured Extrapolated Time",
    )

    setup_plot(
        ax,
        nodes,
        "Extrapolated Time (hours)",
        f"{STAGES[stage]} Time vs Nodes",
    )

    fig.tight_layout()
    fig.savefig(output_file, dpi=300)
    plt.close(fig)


def plot_stage_configs(results, stage, output_file):
    """Plot stage time against extrapolated QM configurations."""

    data = sorted(
        (
            r["qm_calcs"],
            r[f"{stage}_time_hours"],
        )
        for r in results
    )

    configs = [item[0] for item in data]
    times = [item[1] for item in data]

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(
        configs,
        times,
        "o-",
        linewidth=2,
        markersize=7,
        label=STAGES[stage],
    )

    ax.set_xlabel("Number of Configurations")
    ax.set_ylabel("Extrapolated Time (hours)")
    ax.set_title(
        f"{STAGES[stage]} Time vs Configurations"
    )

    ax.set_ylim(bottom=0)
    set_sparse_xticks(ax, configs)

    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_file, dpi=300)
    plt.close(fig)


def plot_stage_percent(results, x_type, output_file):
    """Plot the percentage of total time spent in each stage."""

    x_key = (
        "nodes"
        if x_type == "nodes"
        else "qm_calcs"
    )

    data = sorted(
        results,
        key=lambda r: r[x_key],
    )

    xs = [r[x_key] for r in data]

    fig, ax = plt.subplots(figsize=(8, 5))

    for stage, color in [
        ("md", "tab:blue"),
        ("qm", "tab:orange"),
        ("ml", "tab:green"),
    ]:
        ax.plot(
            xs,
            [r[f"{stage}_percent"] for r in data],
            "o-",
            linewidth=2,
            markersize=7,
            color=color,
            label=STAGES[stage],
        )

    ax.set_xlabel(
        "Number of Nodes"
        if x_type == "nodes"
        else "Number of Configurations"
    )

    ax.set_ylabel("Fraction of Total Time (%)")
    ax.set_title("ALF Workflow Time Distribution")

    ax.set_ylim(0, 100)

    set_sparse_xticks(ax, xs)

    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_file, dpi=300)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Plot ALF FOM scaling results."
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=None,
        help="Figure output directory (default: FOM_runs/figures).",
    )

    parser.add_argument(
        "--results",
        type=Path,
        default=None,
        help="Results directory (default: FOM_runs/results).",
    )

    args = parser.parse_args()
    base_path = Path("FOM_runs")

    figures_dir = (
        args.figures_dir.expanduser().resolve()
        if args.figures_dir is not None
        else base_path / "figures"
    )

    results_file = (
        args.results.expanduser().resolve()
        if args.results is not None
        else base_path / "results"
    ) / "results.json"

    with open(results_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    figures_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    plot_fom(
        results,
        figures_dir / "FOM_vs_nodes.png",
    )

    plot_efficiency(
        results,
        figures_dir / "FOM_scaling_efficiency.png",
    )

    for stage in STAGES:

        plot_stage_time(
            results,
            stage,
            figures_dir
            / f"{stage.upper()}_time_vs_nodes.png",
        )

        plot_stage_configs(
            results,
            stage,
            figures_dir
            / f"{stage.upper()}_time_vs_configs.png",
        )

    for x_type in ("nodes", "configs"):

        plot_stage_percent(
            results,
            x_type,
            figures_dir
            / f"Stage_percent_vs_{x_type}.png",
        )

    print(
        "\nComparison Summary\n"
        + "=" * 60
    )

    print(
        f"{'Nodes':>8} "
        f"{'FOM':>14} "
        f"{'Ideal FOM':>14} "
        f"{'Efficiency':>12}"
    )

    for row in results:
        print(
            f"{row['nodes']:8d} "
            f"{row['fom']:14.0f} "
            f"{row['ideal_fom']:14.0f} "
            f"{row['efficiency_percent']:11.2f}%"
        )

    print(f"Figures output to: {figures_dir}")

if __name__ == "__main__":
    main()
