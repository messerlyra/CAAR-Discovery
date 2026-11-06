# Run this script as:
import os, sys; sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# python run_training.py
#
# This script performs a simple training task for a HIPPYNN ensemble using the CAAR-Discovery framework.
# It uses the configuration from hippynn_config.json and demo data from `dataset/*.h5`.

import json
import os
import sys
from custom_training import train_HIPPYNN_ensemble_task
from tools import run_parsl
from pathlib import Path

def main():
    # Load config
    with open('training_config.json', 'r') as f:
        ml_config = json.load(f)

    # Parameters
    h5_dir = Path('dataset').resolve()
    # this is the trainer's output directory
    model_path = 'models/ensemble-{:04d}'
    current_training_id = 1 # arg for above, (models/ensemble-0001)
    gpus_per_node = 1 # this will train just 1 model

    # Ensure models directory exists
    if not os.path.exists('models'):
        os.makedirs('models')

    # Run the task using .func
    print(f"Running training task for ID {current_training_id}...")
    try:
        result = run_parsl(
            train_HIPPYNN_ensemble_task,
            ML_config=ml_config,
            h5_dir=h5_dir,
            model_path=model_path,
            current_training_id=current_training_id,
            gpus_per_node=gpus_per_node
        )
        print("Training task completed.")
        print(f"Result type: {type(result)}")
        print(f"Result: {repr(result)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Training task failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
