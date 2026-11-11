# Figure of Merit (FOM) Measurement

This directory contains the tools for measuring and analyzing the Figure of Merit (FOM) of the Active Learning Framework (ALF) workflow.

## 1. Introduction to Figure of Merit (FOM)

The **Figure of Merit (FOM)** is defined as the number of force components learned per hour. It is used to evaluate the scaling efficiency of the ALF workflow as compute resources are increased.

### The Formula

$$\mathrm{FOM} = \frac{N_{\mathrm{QM}} \times N_{\mathrm{atoms}} \times 3}{t_{\mathrm{MD}} + t_{\mathrm{QM}} + t_{\mathrm{ML}}} \times 3600 \mathrm{sec/hr}$$

Where:
- $N_{\mathrm{QM}}$ = completed QM calculations per batch $\times$ number of QM batches.
- $N_{\mathrm{atoms}}$ = number of atoms per configuration.
- $t_{\mathrm{MD}}, t_{\mathrm{QM}}, t_{\mathrm{ML}}$ = extrapolated execution times in seconds for the MD Sampling, QM Labeling, and ML Training stages, respectively.

**Output unit:** Force components learned per hour.

---

## 2. Running the FOM Suite

### Workflow
The FOM measurement process follows a three-step sequence:
1.  **`prepare_FOM.sh $nodes`**: Sets up the test directory for size `$nodes`, generates configurations, and prepares precomputed HDF5 copies.

    This creates a `test_dir` named like `FOM_runs/nodes_8MD_8QM_1ML`.

2.  **`run_FOM.sh $nodes`**: Launches the test for size `$nodes` in a detached `tmux` session.

3.  **`run_FOM_worker.sh $test_dir`**: The actual execution script run inside `$test_dir` that manages the `alframework` run and the timing collector.

### Configuration
The prepare and run scripts use `$nodes` (aka `NODE_COUNT`) to set `NNODES_MD`, `NNODES_QM`, and `NNODES_ML`
as the smaller of nodes or `NODE_MAX_MD`, `NODE_MAX_QM`, `NODE_MAX_ML`.

This caps the number of nodes allocated to each stage at the maximum parallelism supported by each stage.

### Execution
To launch a test for a specific node count:
```bash
./run_FOM.sh <node_count>
```
This launches the worker (`run_FOM_worker.sh`) as a process whose tree is managed by a tmux session. Each test is organized into a directory named `nodes_<MD>MD_<QM>QM_<ML>ML` inside `FOM_runs/`, which serves as the primary identifier for that run.

---

## 3. Diagnostics & Monitoring

Monitoring the progress of a run can be done by checking the following files in the test directory:

- **`alf_FOM.log`**: Captures the `alframework` stdout. This is the primary log for monitoring the overall run.

  `cat FOM_runs/nodes_8MD_8QM_1ML/alf_FOM.log | grep -v ':[ 0-9]*$'`

- **`status_FOM.txt`**: Records job completion counts. The contents of this file are printed to `alf_FOM.log` every minute.

  `diff -b FOM_template/status_FOM.txt FOM_runs/nodes_8MD_8QM_1ML/status_FOM.txt`

- **`runinfo/`**: Contains the stdout and stderr of the `sbatch` jobs managed by Parsl.

  `wc FOM_runs/nodes_8MD_8QM_1ML/runinfo/*/submit_scripts/*.std*`

---

## 4. Analyzing Results

### Single Run Analysis (`analyze_FOM.py`)
This script calculates the FOM for a single ALF run. It extrapolates the original execution times to target MD durations and ML training epochs.

**Usage:**
```bash
python analyze_FOM.py --alf_path /path/to/test_dir [options]
```

### Comparative Analysis (`calculate_results.py`)
This script aggregates results gathered by `analyse_FOM.py` to evaluate scaling.
It compares the measured FOM against an ideal linear scaling model to determine efficiency,
then saves its output in a format `plot_results.py` can use.

**Usage:**
```bash
python3 calculate_results.py [--results FOM_runs/results]
```

### FOM visualization (`plot_results.py`)
**Usage:**
```bash
python3 plot_results.py
```

Reads from `--results FOM_runs/results` and writes to `--figures-dir FOM_runs/figures` by default.

---

## 5. Output Reference

### Directory Structure
```text
$BASE_DIR/                   # This directory

FOM_runs/                    # OUTPUT_BASE  (generated)
├── nodes_1MD_1QM_1ML/       # Individual test directory
│   ├── alf_FOM.log          # Run log
│   ├── status_FOM.txt       # Job status
│   ├── timings.csv          # Timing server's collected log file
│   ├── timings.csv.pid      # The pid of the timing server (a process within the tmux session)
│   ├── tmux.info            # Reminder where the tmux for this session is running
│   └── runinfo/             # Parsl sbatch logs
├── results/                 # Analysis outputs
│   ├── FOM_comparison.csv   # Summary table
│   └── FOM_results_*.txt    # Individual run reports
└── figures/                 # Scaling plots
    ├── FOM_vs_nodes.png     # Measured vs. Ideal FOM
    └── ...
```

### File Glossary
- **`FOM_comparison.csv`**: A summary table containing node counts, extrapolated times, measured FOM, and scaling efficiency.
- **`FOM_results_*.txt`**: Detailed reports for each individual run, preserving the output of `analyze_FOM.py`.

### Figure Guide
| File | Description |
|---|---|
| `FOM_vs_nodes.png` | Measured FOM vs. ideal linear scaling |
| `FOM_scaling_efficiency.png` | FOM scaling efficiency (%) |
| `MD_time_vs_nodes.png` | MD execution time vs. number of nodes |
| `QM_time_vs_nodes.png` | QM execution time vs. number of nodes |
| `ML_time_vs_nodes.png` | ML execution time vs. number of nodes |
| `Stage_percent_vs_nodes.png` | MD/QM/ML contributions (%) vs. number of nodes |

---

## 6. Methodology Details

For the specific logic used to measure and extrapolate MD, QM, and ML timings, refer to the implementation in `analyze_FOM.py`.
