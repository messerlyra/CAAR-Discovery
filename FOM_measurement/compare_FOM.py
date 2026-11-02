
#!/usr/bin/env python3
"""Compare ALF FOM and extrapolated MD/QM/ML times across node counts."""

import argparse
import csv
import math
import re
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


STAGES = {
    "md": "MD Sampling",
    "qm": "QM Labeling",
    "ml": "ML Training",
}


def parse_duration(value):
    """Convert HH:MM:SS.ss to seconds."""
    hours, minutes, seconds = value.strip().split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def extract_results(output):
    """Extract FOM, configuration counts, and extrapolated stage times."""

    match = re.search(
        r"FOM\s*\((?:components|comp)/hour\)\s*:\s*([\d,]+(?:\.\d+)?)",
        output,
        re.I,
    )

    if not match:
        raise ValueError("Could not extract FOM from analyzer output.")

    result = {
        "fom": float(match.group(1).replace(",", ""))
    }

    section = re.search(
        r"Stage Durations:\s*(.*?)(?:\n\s*(?:Figure of Merit|Time Distribution):|\Z)",
        output,
        re.S | re.I,
    )

    if not section:
        raise ValueError("Could not find Stage Durations section.")

    for key, label in [*STAGES.items(), ("total", "Total")]:
        duration = re.search(
            r"^\s*" + re.escape(label) + r"\s*:\s*(\d+:\d+:[\d.]+)",
            section.group(1),
            re.M,
        )

        if not duration:
            raise ValueError(f"Could not extract {label} duration.")

        result[f"{key}_time"] = parse_duration(
            duration.group(1)
        )

    count_patterns = {
        "md_trajectories": (
            r"Trajectories analyzed\s*:\s*([\d,]+)"
        ),
        "qm_calcs": (
            r"Extrapolated QM calcs\s*:\s*([\d,]+)"
        ),
    }

    for key, pattern in count_patterns.items():
        count = re.search(pattern, output, re.I)

        if not count:
            raise ValueError(
                f"Could not extract {key} from analyzer output."
            )

        result[key] = int(count.group(1).replace(",", ""))

    return result


def find_alf_directory(base_path, nodes):
    """
    Find an ALF directory matching nodes_NMD_*.

    Example:
        nodes_4MD_4QM_1ML
        nodes_512MD_64QM_1ML
    """
    pattern = f"nodes_{nodes}MD_*"

    matches = sorted(
        path for path in base_path.glob(pattern)
        if path.is_dir()
    )

    if not matches:
        raise FileNotFoundError(
            f"No directory matching {pattern}"
        )

    if len(matches) > 1:
        raise ValueError(
            f"Multiple directories match {pattern}: {matches}"
        )

    return matches[0]


def run_analysis(
    analyzer,
    alf_dir,
    timestep,
    md_duration,
    epochs,
    results_dir,
):
    """
    Run analyze_FOM.py and save its original output
    in the shared results directory.
    """

    command = [
        sys.executable,
        str(analyzer),
        "--alf_path",
        str(alf_dir),
        "--timestep",
        str(timestep),
        "--md-duration",
        str(md_duration),
        "--epochs",
        str(epochs),
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    # Save individual ALF results in the shared results directory.
    report = (
        results_dir / f"FOM_results_{alf_dir.name}.txt"
    )

    report.write_text(
        completed.stdout,
        encoding="utf-8",
    )

    if completed.returncode != 0:
        if completed.stderr:
            error_file = (
                results_dir / f"FOM_error_{alf_dir.name}.txt"
            )

            error_file.write_text(
                completed.stderr,
                encoding="utf-8",
            )

        raise RuntimeError(
            f"Analyzer failed for {alf_dir}: "
            f"{completed.stderr.strip()}"
        )

    return extract_results(completed.stdout)


def calculate_scaling(results):
    """Calculate ideal FOM scaling and stage time percentages."""

    results.sort(key=lambda r: r["nodes"])

    baseline = results[0]
    base_nodes = baseline["nodes"]
    base_fom = baseline["fom"]

    if base_fom <= 0:
        raise ValueError("Baseline FOM must be positive.")

    for row in results:
        nodes = row["nodes"]

        row["ideal_fom"] = (
            base_fom * nodes / base_nodes
        )

        row["efficiency_percent"] = (
            100 * row["fom"] / row["ideal_fom"]
        )

        total = row["total_time"]

        if total <= 0:
            raise ValueError(
                f"Nonpositive total time for {nodes} nodes."
            )

        row["total_time_hours"] = total / 3600

        for stage in STAGES:
            duration = row[f"{stage}_time"]

            if duration <= 0:
                raise ValueError(
                    f"Nonpositive {stage} time for {nodes} nodes."
                )

            row[f"{stage}_time_hours"] = duration / 3600

            row[f"{stage}_percent"] = (
                100 * duration / total
            )


def save_csv(results, output_file):
    """Save comparison results with controlled numeric precision."""

    columns = [
        "nodes",
        "directory",
        "md_trajectories",
        "qm_calcs",
        "fom",
        "ideal_fom",
        "efficiency_percent",
        "md_time_hours",
        "qm_time_hours",
        "ml_time_hours",
        "total_time_hours",
        "md_percent",
        "qm_percent",
        "ml_percent",
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
        )

        writer.writeheader()

        for result in results:
            row = {}

            for key in columns:
                value = result[key]

                # FOM: no decimal places
                if key in ("fom", "ideal_fom"):
                    row[key] = f"{value:.0f}"

                # Percentages: 5 significant figures
                elif key.endswith("_percent"):
                    row[key] = f"{value:.5g}"

                # Hours: 3 significant figures
                elif key.endswith("_hours"):
                    row[key] = f"{value:.3g}"

                else:
                    row[key] = value

            writer.writerow(row)


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
        description="Compare ALF FOM and MD/QM/ML scaling."
    )

    parser.add_argument(
        "--alf_path",
        type=Path,
        default=Path.cwd(),
        help="Parent directory containing nodes_NMD_* folders.",
    )

    parser.add_argument(
        "--nodes",
        type=int,
        nargs="+",
        required=True,
        help="Node counts to compare.",
    )

    parser.add_argument(
        "--timestep",
        type=float,
        default=0.25,
        help="MD timestep in fs (default: 0.25).",
    )

    parser.add_argument(
        "--md-duration",
        type=float,
        default=10.0,
        help="Target MD duration in ps (default: 10).",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=500,
        help="Target ML epochs (default: 500).",
    )

    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=None,
        help="Figure output directory (default: alf_path/figures).",
    )

    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Results directory (default: alf_path/results).",
    )

    parser.add_argument(
        "--analyzer",
        type=Path,
        default=(
            Path(__file__).resolve().parent
            / "analyze_FOM.py"
        ),
        help="Path to analyze_FOM.py.",
    )

    args = parser.parse_args()

    base_path = args.alf_path.expanduser().resolve()
    analyzer = args.analyzer.expanduser().resolve()

    figures_dir = (
        args.figures_dir.expanduser().resolve()
        if args.figures_dir is not None
        else base_path / "figures"
    )

    results_dir = (
        args.results_dir.expanduser().resolve()
        if args.results_dir is not None
        else base_path / "results"
    )

    if not base_path.is_dir():
        parser.error(
            f"Directory not found: {base_path}"
        )

    if not analyzer.is_file():
        parser.error(
            f"Analyzer not found: {analyzer}"
        )

    if not args.nodes or any(n <= 0 for n in args.nodes):
        parser.error("Node counts must be positive.")

    if any(
        not math.isfinite(x) or x <= 0
        for x in (args.timestep, args.md_duration)
    ):
        parser.error(
            "Timestep and MD duration must be finite positive numbers."
        )

    if args.epochs <= 0:
        parser.error("Epoch count must be positive.")

    # Create the results directory before running analyses.
    results_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = []

    print(
        "\nALF FOM Comparison\n"
        + "=" * 60
    )

    for nodes in sorted(set(args.nodes)):

        print(f"\nAnalyzing {nodes} nodes...")

        try:
            alf_dir = find_alf_directory(
                base_path,
                nodes,
            )

            result = run_analysis(
                analyzer,
                alf_dir,
                args.timestep,
                args.md_duration,
                args.epochs,
                results_dir,
            )

            result.update(
                nodes=nodes,
                directory=alf_dir.name,
            )

            results.append(result)

            print(f"  Directory : {alf_dir.name}")
            print(f"  FOM       : {result['fom']:.0f}")
            print(
                f"  MD time   : "
                f"{result['md_time'] / 3600:.3g} h"
            )
            print(
                f"  QM time   : "
                f"{result['qm_time'] / 3600:.3g} h"
            )
            print(
                f"  ML time   : "
                f"{result['ml_time'] / 3600:.3g} h"
            )

        except Exception as exc:
            print(
                f"  ERROR: {exc}",
                file=sys.stderr,
            )

    if not results:
        parser.error(
            "No successful analyses were found."
        )

    calculate_scaling(results)

    figures_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    save_csv(
        results,
        results_dir / "FOM_comparison.csv",
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

    print(
        f"\nCSV results: "
        f"{results_dir / 'FOM_comparison.csv'}"
    )

    print(
        f"Figures directory: {figures_dir}"
    )

    print(
        f"Individual FOM reports: {results_dir}"
    )


if __name__ == "__main__":
    main()

