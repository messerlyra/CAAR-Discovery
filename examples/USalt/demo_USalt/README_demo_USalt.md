# Testing the USalt Demo

The demo is in the [`demos/demo_w_parsl`](https://github.com/messerlyra/CAAR-Discovery/tree/USalt_prep/demos/demo_w_parsl) directory of the `USalt_prep` branch.

## Setup

Starting a `tmux` session is optional but recommended:

```bash
tmux new
```

Activate the CAAR environment:

```bash
source /lustre/orion/world-shared/csc728/messerlyra/scripts/load_caar_env.bash
```

Change to the demo system directory:

```bash
cd CAAR-Discovery/demos/demo_w_parsl/system_000001_n14_c-Li-Na-K-Rb-Cs-Be-Mg-Ca-Sr-Ba-Zn-Zr_a-F-Cl
```

## Run debug tests - single task on single node on single GPU with debug QOS

Run the builder test:

```bash
python -m alframework --master master_config.json --test_builder
```

Run the molecular-dynamics (MD) sampler test:

```bash
python -m alframework --master master_config.json --test_sampler
```

Run the quantum-mechanics (QM) teacher/labeling test:

```bash
python -m alframework --master master_config.json --test_qm
```

Run the machine-learning (ML) training test:

```bash
python -m alframework --master master_config.json --test_ml
```

## Run production-level tests for MD, QM and ML - multiple tasks across a specified number of nodes (see master\_X.json files)

```bash
python -m alframework --master master_md.json
```

```bash
python -m alframework --master master_qm.json
```

```bash
python -m alframework --master master_ml.json
```

