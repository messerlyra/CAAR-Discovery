#!/usr/bin/env python3
"""Plot a timings.csv (from src/timing/timing_server.py) as a percent-utilization timeline.

Usage: plot_timings.py [--bin SECONDS] FOM_runs/nodes_*/timings.csv ...
Writes timings.png next to each input.

The directory name must contain nodes_<N>MD_<N>QM_<N>ML (same regexp as
run_FOM_worker.sh); N is a node count.  100% is N nodes and 8*N jobs for MD
and QM (8 GPUs per node), and N nodes / N jobs for ML.
"""
import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

# task_id prefix -> short task type
PREFIX = {"builder": "BL", "sampling": "MD", "rootstock": "QM", "training": "ML"}
TYPES = ["BL", "MD", "QM", "ML"]
COLORS = {"BL": "#7a7a7a", "MD": "#1f77b4", "QM": "#d95f02", "ML": "#2ca02c"}
# columns of the feature array
FEATURES = (["t_hours"]
            + [f"jobs_{t}" for t in TYPES]
            + [f"err_{t}" for t in TYPES]
            + [f"nodes_{t}" for t in ("MD", "QM", "ML")]
            + [f"nodeerr_{t}" for t in ("MD", "QM", "ML")])
GPUS_PER_NODE = 8

DIR_RE = re.compile(r"nodes_(\d+)MD_(\d+)QM_(\d+)ML")
REC_START = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?,")


def read_records(path):
    """Yield (datetime, task_id, status, node).

    A record starts at a line beginning with an ISO timestamp; any following
    lines that do not (multi-line error text) belong to it.  The node is the
    text after the record's last comma; the status is its first line only.
    """
    chunks = []
    with open(path, errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if REC_START.match(line):
                chunks.append([line])
            elif chunks:
                chunks[-1].append(line)
    for lines in chunks:
        text = "\n".join(lines)
        head, sep, node = text.rpartition(",")
        parts = head.split(",", 2)
        if not sep or len(parts) < 3:
            continue
        ts, task_id, status = parts
        try:
            t = datetime.fromisoformat(ts)
        except ValueError:
            continue
        yield t, task_id, status.split("\n")[0].strip(), node.strip()


def task_type(task_id):
    return PREFIX.get(re.split(r"[.\-]", task_id)[0])


def pair_jobs(recs, t0):
    """Return (jobs, errors, stats).

    jobs: list of (start_sec, end_sec, type, node).  The collector drops
    messages under load, so some jobs have only a start or only an end; the
    missing side is imputed with the median duration of fully paired jobs of
    that type.  errors: list of (sec, type, node).
    """
    sec = lambda t: (t - t0).total_seconds()
    starts, ends, errors = {}, {}, []
    for t, tid, status, node in recs:
        typ = task_type(tid)
        if typ is None:
            continue
        if status == "start":
            starts[tid] = (sec(t), typ, node)
        elif status == "end":
            ends[tid] = (sec(t), typ, node)
        elif status.startswith("error"):
            ends[tid] = (sec(t), typ, node)
            errors.append((sec(t), typ, node))
    dur = defaultdict(list)
    for tid in starts.keys() & ends.keys():
        dur[starts[tid][1]].append(ends[tid][0] - starts[tid][0])
    med = {k: float(np.median(v)) for k, v in dur.items()}
    err_set = set(errors)
    jobs, stats = [], defaultdict(int)
    for tid in starts.keys() | ends.keys():
        if tid in starts and tid in ends:
            (s, typ, node), e = starts[tid], ends[tid][0]
            jobs.append((s, max(e, s), typ, node))
        elif tid in starts:
            s, typ, node = starts[tid]
            stats[f"{typ} start-only"] += 1
            jobs.append((s, s + med.get(typ, 0.0), typ, node))
        else:
            e, typ, node = ends[tid]
            if (e, typ, node) in err_set:  # error before any start: never ran
                continue
            stats[f"{typ} end-only"] += 1
            jobs.append((max(e - med.get(typ, 0.0), 0.0), e, typ, node))
    return jobs, errors, dict(stats)


def build_timeline(records, bin_s):
    """Return (features array [nbin x len(FEATURES)], t0 datetime, stats).

    jobs_*     : time-averaged number of running jobs in the bin
    err_*      : number of error terminations in the bin
    nodes_*    : number of distinct nodes with a running job in the bin
    nodeerr_*  : number of distinct nodes that have had an error up to the bin
    """
    recs = sorted(records)
    t0 = recs[0][0].replace(hour=0, minute=0, second=0, microsecond=0)
    jobs, errors, stats = pair_jobs(recs, t0)
    tmin = min([j[0] for j in jobs] + [e[0] for e in errors])
    tmax = max([j[1] for j in jobs] + [e[0] for e in errors])
    lo = np.floor(tmin / bin_s) * bin_s
    nbin = int(np.ceil((tmax - lo) / bin_s)) + 1
    edges = lo + bin_s * np.arange(nbin + 1)

    out = np.zeros((nbin, len(FEATURES)))
    col = {n: i for i, n in enumerate(FEATURES)}
    out[:, 0] = (edges[:-1] + bin_s / 2) / 3600
    nodes = {t: [set() for _ in range(nbin)] for t in ("MD", "QM", "ML")}
    errnodes = {t: [set() for _ in range(nbin)] for t in ("MD", "QM", "ML")}

    for s, e, typ, node in jobs:
        i0 = int((s - lo) // bin_s)
        i1 = min(int((e - lo) // bin_s), nbin - 1)
        for i in range(i0, i1 + 1):
            ov = min(e, edges[i + 1]) - max(s, edges[i])
            if ov > 0:
                out[i, col[f"jobs_{typ}"]] += ov / bin_s
            if typ in nodes:
                nodes[typ][i].add(node)
    for s, typ, node in errors:
        i = min(int((s - lo) // bin_s), nbin - 1)
        out[i, col[f"err_{typ}"]] += 1
        if typ in errnodes:
            errnodes[typ][i].add(node)

    for typ in nodes:
        out[:, col[f"nodes_{typ}"]] = [len(x) for x in nodes[typ]]
        seen = set()
        for i, x in enumerate(errnodes[typ]):  # cumulative set of errored nodes
            seen |= x
            out[i, col[f"nodeerr_{typ}"]] = len(seen)
    return out, t0, stats


def to_percent(out, njobs):
    """Scale to percent.  njobs: dict type -> total jobs (100%).

    Node percent is out of (jobs+7)//8.  BL has no count in the directory
    name, so it is scaled to its own peak concurrency.
    """
    pct = out.copy()
    col = {n: i for i, n in enumerate(FEATURES)}
    denom = dict(njobs)
    denom["BL"] = max(out[:, col["jobs_BL"]].max(), 1)
    for t in TYPES:
        for pre in ("jobs", "err"):
            pct[:, col[f"{pre}_{t}"]] *= 100 / denom[t]
    for t in ("MD", "QM", "ML"):
        nmax = (njobs[t] + GPUS_PER_NODE - 1) // GPUS_PER_NODE
        for pre in ("nodes", "nodeerr"):
            pct[:, col[f"{pre}_{t}"]] *= 100 / nmax
    return pct


def plot(pct, t0, title, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    col = {n: i for i, n in enumerate(FEATURES)}
    t = pct[:, 0]
    fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    for T in TYPES:
        ax[0].plot(t, pct[:, col[f"jobs_{T}"]], color=COLORS[T], label=f"{T} jobs")
    for T in ("BL", "MD", "QM"):
        cum = np.cumsum(pct[:, col[f"err_{T}"]])
        ax[0].fill_between(t, 0, cum, color=COLORS[T], alpha=0.3, label=f"{T} cum. errors")
    ax[0].set_ylabel("% of total jobs")
    for T in ("MD", "QM", "ML"):
        ax[1].plot(t, pct[:, col[f"nodes_{T}"]], color=COLORS[T], label=f"{T} nodes")
        ax[1].plot(t, pct[:, col[f"nodeerr_{T}"]], color=COLORS[T], ls="--", label=f"{T} errored nodes (cum.)")
    ax[1].set_ylabel("% of total nodes")
    ax[1].set_xlabel(f"hours since {t0:%Y-%m-%d} 00:00")
    for a in ax:
        a.grid(alpha=0.3)
        a.legend(loc="upper right", ncol=2, frameon=False, fontsize=8)
    ax[0].set_title(title)
    fig.tight_layout()
    fig.savefig(png, dpi=150)
    plt.close(fig)


def process(path, bin_s):
    path = Path(path)
    m = DIR_RE.search(str(path.parent))
    if not m:
        print(f"{path}: directory name does not match nodes_<N>MD_<N>QM_<N>ML; skipped", file=sys.stderr)
        return False
    nn = dict(zip(("MD", "QM", "ML"), map(int, m.groups())))
    njobs = {"MD": nn["MD"] * GPUS_PER_NODE, "QM": nn["QM"] * GPUS_PER_NODE, "ML": nn["ML"]}
    recs = list(read_records(path))
    if not recs:
        print(f"{path}: no records; skipped", file=sys.stderr)
        return False
    out, t0, stats = build_timeline(recs, bin_s)
    if stats:
        print(f"  imputed from dropped messages: {stats}")
    pct = to_percent(out, njobs)
    png = path.with_name("timings.png")
    plot(pct, t0, f"{path.parent.name} ({len(recs)} records, {bin_s:g}s bins)", png)
    print(f"{path}: {len(recs)} records, {len(out)} bins -> {png}")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+", help="timings.csv files")
    ap.add_argument("--bin", type=float, default=60.0, help="time-bin width in seconds (default 60)")
    args = ap.parse_args()
    ok = [process(f, args.bin) for f in args.files]
    sys.exit(0 if any(ok) else 1)


if __name__ == "__main__":
    main()
