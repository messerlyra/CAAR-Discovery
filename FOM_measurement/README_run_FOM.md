# `run_FOM.sh`

`run_FOM.sh` runs ALF FOM tests using different numbers of MD compute nodes and automatically determines the QM and ML node allocations. It prepares precomputed QM HDF5 copies when additional QM batches are required. By default, tests run sequentially. The optional `--parallel` argument starts all tests concurrently in the same `tmux` window.

After all ALF tests complete successfully, the script automatically runs `compare_FOM.py` to analyze the results and generate FOM scaling plots.

## Configuration

Edit the node-count list and maximum node allocations near the beginning of the script:

```bash
NODE_COUNTS=(1 2 4 8)

NODE_MAX_MD=-1
NODE_MAX_QM=64
NODE_MAX_ML=1

readonly GPUS_PER_NODE=8

# Example full list:
# NODE_COUNTS=(1 2 4 8 16 32 64 128 256 512 1024 2048 4096 8192 9856)
```

`NODE_COUNTS` supplies the requested MD node counts. For each test, the effective MD node count is limited by `NODE_MAX_MD`, the QM node count is limited by `NODE_MAX_QM`, and the ML node count is limited by `NODE_MAX_ML`. A limit of `-1` means no additional cap for that stage. With the defaults, QM uses up to 64 nodes and ML uses one node.

The script uses the following fixed paths and names:

```text
Template directory:         FOM_template
Output directory:           FOM_runs
Precomputed HDF5 directory: h5store_precomputed
Template master file:       master_template.json
Template Frontier file:     frontier_template.py
TMUX session:               alf_FOM
GPUs per node:              8
Resource manifest:          FOM_runs/FOM_manifest.tsv
Worker script:              FOM_runs/run_FOM_worker.sh
Results directory:          FOM_runs/results
Figures directory:          FOM_runs/figures
```

The script does not accept template or output directories as command-line arguments. It uses a fixed CAAR environment script path.

## What the Script Does

For each value in `NODE_COUNTS`, the script:

1. Computes the effective stage allocations:

   ```text
   NNODES_MD = min(requested MD nodes, NODE_MAX_MD) when capped
   NNODES_QM = min(NNODES_MD, NODE_MAX_QM) when capped
   NNODES_ML = min(NNODES_MD, NODE_MAX_ML) when capped

   NCONFIGS_MD = NNODES_MD × 8
   NCONFIGS_QM = NNODES_QM × 8

   QM batches = NCONFIGS_MD / NCONFIGS_QM
   ```

   The script requires `NCONFIGS_MD` to be divisible by `NCONFIGS_QM`.

2. Copies `FOM_template` to `FOM_runs/nodes_<MD>MD_<QM>QM_<ML>ML`.

3. Renames `master_template.json` to `master_FOM.json` and `frontier_template.py` to `frontier_FOM.py`.

4. Replaces resource placeholders in both files:

   ```text
   NNODES_MD, NNODES_QM, NNODES_ML, NNODES
   NCONFIGS_MD, NCONFIGS_MD_MINUS_ONE, NCONFIGS_MD_PLUS_ONE
   NCONFIGS_QM, NCONFIGS_QM_MINUS_ONE, NCONFIGS_QM_PLUS_ONE
   ```

5. Copies `data-<NCONFIGS_QM>configs.h5` from `h5store_precomputed/` to the test's `h5store/` directory **QM batches minus one** times, because ALF creates one HDF5 file itself. Copies are named `data-<NCONFIGS_QM>configs-copy-0000.h5`, `...0001.h5`, etc. No precomputed file is required for a single batch.

6. Records each prepared test and its MD/QM/ML node counts in `FOM_manifest.tsv`.

7. Generates `run_FOM_worker.sh`, which reads the manifest and runs ALF with:

   ```bash
   python -u -m alframework --master master_FOM.json
   ```

8. After all tests finish successfully, automatically runs `compare_FOM.py` to calculate the FOM and generate comparison results.

The worker activates the CAAR environment for each test and writes ALF output to that test's log. Using the manifest ensures that execution uses the same stage allocations as directory preparation.

Without `--parallel`, tests run sequentially. After each test, the worker attempts to cancel leftover Slurm jobs named `ML_<MD nodes>nodes` for the configured user and waits two seconds. A failed ALF test stops the remaining sequence.

With `--parallel`, all tests are launched in the background and waited on individually; a failure does not cancel already-running tests, and the sequential Slurm cleanup is skipped.

## Running the Script

```bash
./run_FOM.sh
```

To start all node-count tests concurrently:

```bash
./run_FOM.sh --parallel
```

The script creates one detached `tmux` session with one window and keeps it open after execution:

```bash
tmux attach -t alf_FOM
```

ALF output is redirected to a separate log in each test directory rather than printed in the `tmux` window. The manifest and worker script remain in the output directory.

## Expected Output

With the default `NODE_COUNTS=(1 2 4 8)` and node limits, the following directories are created:

```text
FOM_runs/nodes_1MD_1QM_1ML
FOM_runs/nodes_2MD_2QM_1ML
FOM_runs/nodes_4MD_4QM_1ML
FOM_runs/nodes_8MD_8QM_1ML
```

For larger tests, QM is capped at 64 nodes while ML remains at one node. For example:

```text
FOM_runs/nodes_128MD_64QM_1ML
FOM_runs/nodes_512MD_64QM_1ML
FOM_runs/nodes_1024MD_64QM_1ML
```

For 512 MD nodes, the script prepares 4096 MD configurations, 512 QM configurations per batch, eight QM batches, and seven precomputed HDF5 copies.

Each test directory contains its own `master_FOM.json`, `frontier_FOM.py`, `h5store/`, and log. For example:

```text
FOM_runs/nodes_512MD_64QM_1ML/alf_FOM_nodes_512MD_64QM_1ML.log
FOM_runs/FOM_manifest.tsv
FOM_runs/run_FOM_worker.sh
```

Each log records the start message, ALF output, and final ALF exit code. In sequential mode, a failure prevents later tests from starting; in parallel mode, already-started tests continue independently.

The script also creates `results/` and `figures/` inside `FOM_runs/` for the automatic FOM analysis.

## Automatic FOM Analysis

After all ALF tests have completed successfully, the worker automatically runs `compare_FOM.py` using the MD node counts recorded in `FOM_manifest.tsv`.

The comparison is executed only if every ALF test exits with code 0. In parallel mode, the worker waits for all tests to finish before starting the analysis. If any test fails, the comparison is skipped.

The command is equivalent to:

```bash
python -u compare_FOM.py \
    --alf_path "$OUTPUT_ROOT" \
    --nodes "${NODE_COUNTS[@]}" \
    --results-dir "$OUTPUT_ROOT/results" \
    --figures-dir "$OUTPUT_ROOT/figures"
```

The comparison output is saved to:

```text
FOM_runs/results/FOM_comparison.log
```

The analysis generates a CSV summary, individual FOM reports, and ten scaling and execution-time figures.

The resulting directory structure is:

```text
FOM_runs/
├── FOM_manifest.tsv
├── run_FOM_worker.sh
├── nodes_1MD_1QM_1ML/
├── nodes_2MD_2QM_1ML/
├── nodes_4MD_4QM_1ML/
├── nodes_8MD_8QM_1ML/
├── results/
│   ├── FOM_comparison.log
│   ├── FOM_comparison.csv
│   ├── FOM_results_nodes_1MD_1QM_1ML.txt
│   ├── FOM_results_nodes_2MD_2QM_1ML.txt
│   ├── FOM_results_nodes_4MD_4QM_1ML.txt
│   └── FOM_results_nodes_8MD_8QM_1ML.txt
└── figures/
    ├── FOM_vs_nodes.png
    ├── FOM_scaling_efficiency.png
    ├── MD_time_vs_nodes.png
    ├── QM_time_vs_nodes.png
    ├── ML_time_vs_nodes.png
    ├── MD_time_vs_configs.png
    ├── QM_time_vs_configs.png
    ├── ML_time_vs_configs.png
    ├── Stage_percent_vs_nodes.png
    └── Stage_percent_vs_configs.png
```

The individual `FOM_results_<directory_name>.txt` files preserve the output of `analyze_FOM.py`. All figures are saved in `figures/`, while the CSV summary, comparison log, and individual FOM reports are saved in `results/`.

Both `compare_FOM.py` and `analyze_FOM.py` must be available in the same directory as `run_FOM.sh`.

The automatic comparison uses the default MD timestep, target MD duration, and ML epoch count defined in `compare_FOM.py`, unless explicitly overridden in the worker command.
