import time
import random
import sys
import os

# Add the project root to sys.path so we can import demo.timing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from demo.timing.timing_client import time_task

def get_test_task_id(*args, **kwargs):
    return f"test_task_{random.randint(1000, 9999)}"

@time_task(get_test_task_id)
def simple_task():
    # Sleep for a random time between 0 and 1 second
    time.sleep(random.random())

if __name__ == "__main__":
    simple_task()
