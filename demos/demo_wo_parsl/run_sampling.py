# Run this script as:
# python run_sampling.py
#
# This script performs a simple MLMD sampling task using the CAAR-Discovery framework.
# It uses the configuration from mlmd_config.json and a demo molecule.

import json
import os
import numpy as np
from ase import Atoms
from alframework.tools.molecules_class import MoleculesObject
from custom_sampling import simple_mlmd_sampling_task
from tools import run_parsl, build_molecule

def main():
    with open('master_config.json', 'r') as f:
        master_config = json.load(f)

    # Load configs
    with open('mlmd_config.json', 'r') as f:
        sampler_config = json.load(f)
    
    with open('builder_config.json', 'r') as f:
        builder_config = json.load(f)

    # Build a real molecule using the builder
    molecule_object = build_molecule('demo_mol_1', builder_config)

    # Parameters
    # Use the ensemble models found in the demo directory
    model_path = os.path.abspath( master_config['model_path'] )
    current_model_id = 0
    gpus_per_node = 1

    # Set environment variable to avoid TypeError in simple_mlmd_sampling_task
    os.environ['PARSL_WORKER_RANK'] = '0'

    # Run the task using .func
    print(f"Running sampling task with model {current_model_id}...")
    try:
        result = run_parsl(
            simple_mlmd_sampling_task,
            molecule_object=molecule_object,
            sampler_config=sampler_config,
            model_path=model_path,
            current_model_id=current_model_id,
            gpus_per_node=gpus_per_node
        )
        print("Sampling task completed.")
        print(f"Result type: {type(result)}")
        print(f"Result: {repr(result)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Sampling task failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
