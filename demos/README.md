# demo

The `demo/demo_wo_parsl/run_*.py` scripts execute the three parts of
the FOM individually on test structures and hippynn parameters from:

- h5store: molecule structures to input to teacher computation
- ensembles: pre-computed hippynn model for running sampler
- dataset: molecular structures to input to hippynn MLIP training

Both of the above input datasets, as well as the `*.json` config
files in this directory need to correspond to the ones used in
the `FOM_measurement` in order to get accurate component-wise timings.
Please check this before comparing timings gathered from this directory
with those of the FOM.

The run-scripts work around parsl using `tools.run_parsl`, a helper
which executes `parsl.python_app`-decorated functions directly.
Note that this direct-run method will have different overhead costs
than running within parsl, since parsl starts up each worker once
and passes input/output pairs via network messages.

It is thus suitable for measuring and testing components only.
The full, initial FOM measurement requires using parsl, since that
is ALF's workflow engine. See `../FOM_measurement` for that.

## Running Locally

    . ./venv/bin/activate
    export "PYTHONPATH=path/to/CAAR-Discovery/src:$PYTHONPATH"

This script can be run if the ALF-CAAR and hippynn-CAAR projects are installed
in its environment. This configuration is suitable for local development,
without rootstock, if the `run_teacher.py` program is modified to specify
the hippynn calculator.

## Running on Frontier

Activate the CAAR environment:

    source /lustre/orion/world-shared/csc728/messerlyra/scripts/load_caar_env.bash
    export "PYTHONPATH=path/to/CAAR-Discovery/src:$PYTHONPATH"

Grab an interactive node:

    salloc -N1 -q debug -A csc728 -t 60

Run the steps:

    python run_sampler.py
    python run_teacher.py
    python run_training.py

## Timing server

Each parsl function is wrapped with a function that emits timing logs.
If there is no log server, this prints harmless connection errors.
You can get rid of these by running a timing server in the background during
your runs,

    python ../src/timing/timing_server.py --log timings.csv &
    SERVER_PID=$!
    trap 'kill $SERVER_PID' EXIT

This has the nice side-effect of collecting per-step timings.
