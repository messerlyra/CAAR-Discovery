# ALF FOM Measurement Setup for CAAR

There is a separate README in FOM\_measurement for run\_FOM.sh.

This one has general instructions and debugging ideas.

# demos

# demo with parsl

Separate README provided in the `demos/demo_w_parsl`  

# demo without parsl

Separate README provided in the `demos/demo_wo_parsl`  

## Installation

This workflow depends on the following python packages:

- https://github.com/bnebgen-LANL/ase.git
- https://github.com/messerlyra/ALF-CAAR.git
- https://github.com/messerlyra/hippynn-CAAR.git
- rootstock

The `build_scripts` directory documents a working environment setup on Frontier.

## Tests

The tests/ directory records simple tests of the helper
functions in `demos/demo_wo_parsl/tools.py`.

## Diagnostics

Here are a few diagnostic questions you can use in case a run
is stuck with partial output.

1. Is there a new `.h5` in h5store?
2. Are there 4x8 = 32 folders in QM?
3. Are there 4x8 = 32 `.p` files in sampling?
4. What do the `.stderr` files show for MD and QM in `runinfo/000/submit_scripts`? 
5. Was a QM `.bash` script created in runinfo / 000/ `submit_scripts`?
6. What does `status_FOM.txt` show?
7. In `alf_FOM.txt` check how many QM tasks were queued, successful.

