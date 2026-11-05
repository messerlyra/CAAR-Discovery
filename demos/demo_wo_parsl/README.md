# demo

The `demo/demo_wo_parsl/run_*.py` scripts execute the three parts of
the FOM individually on test structures and hippynn parameters from:

- `FOM_measurement/h5store_precomputed/data-128configs.h5`
- `demo/demo_w_parsl/ensembles/ensemble-0000/model-*/best_model.pt`

The run-scripts work around parsl using `tools.run_parsl`, a helper
which executes `parsl.python_app`-decorated functions directly.
Note that this direct-run method will have different overhead costs
than running within parsl, since parsl starts up each worker once
and passes input/output pairs via network messages.

It is thus suitable for measuring and testing components only.
The full, initial FOM measurement requires using parsl, since that
is ALF's workflow engine.

## Running Locally

This script can be run if the ALF-CAAR and hippynn-CAAR projects are installed
in its environment. This configuration is suitable for local development,
without rootstock, if the `run_teachar.py` program is modified to specify
the hippynn calculator.

## Running on Frontier

Activate the CAAR environment:

    source /lustre/orion/world-shared/csc728/messerlyra/scripts/load_caar_env.bash

Grab an interactive node:

    salloc -N1 -q debug -A csc728 -t 60

Run the steps:

    python run_sampling.py
    python run_teacher.py
    python run_training.py
