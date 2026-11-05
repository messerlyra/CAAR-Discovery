import time
import random
import sys
import os

# Add the project root to sys.path so we can import timing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from timing.timing_client import time_task

@time_task("test")
def simple_task():
    # Sleep for a random time between 0 and 1 second
    time.sleep(random.random())

if __name__ == "__main__":
    simple_task()
