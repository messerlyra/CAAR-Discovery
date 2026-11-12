import json
import socket
import os
import datetime
import functools
import threading
import queue
import atexit
from urllib.parse import urlparse

class TimingClient:
    def __init__(self, server_addr=None):
        # server_addr or environment variable or default
        url = server_addr or os.environ.get("CAAR_TIMING_SERVER", "tcp://localhost:5555")

        # Parse tcp://host:port
        parsed = urlparse(url)
        self.server_host = parsed.hostname or "localhost"
        self.server_port = parsed.port or 5555

        # Queue for outgoing messages
        self.msg_queue = queue.Queue()

        # Start background sender thread
        self.sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self.sender_thread.start()

    def _sender_loop(self):
        """
        Background thread that handles the raw socket communication.
        """
        while True:
            message = None
            try:
                # Get message from queue
                message = self.msg_queue.get()
                if message is None:
                    break

                # Create a fresh socket for the request
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    s.connect((self.server_host, self.server_port))

                    # Send JSON with a newline delimiter
                    payload = (json.dumps(message) + "\n").encode('utf-8')
                    s.sendall(payload)

            except Exception as e:
                import sys
                print(f"TimingClient raw socket error: {e}", file=sys.stderr)
            finally:
                if message is not None:
                    self.msg_queue.task_done()

    def send_status(self, task_id, status):
        """
        Queues a status update (start/end) for a task.
        """
        try:
            node = socket.gethostname()
            message = {
                "task_id": task_id,
                "status": status,
                "node": node,
                "timestamp": datetime.datetime.now().isoformat()
            }
            self.msg_queue.put(message)
        except Exception as e:
            print(f"TimingClient queue error: {e}")

    def flush(self, timeout=2.0):
        """
        Wait for all queued messages to be sent, with a timeout.
        """
        # Use a daemon thread to call join so we can apply a timeout
        join_thread = threading.Thread(target=self.msg_queue.join, daemon=True)
        join_thread.start()
        join_thread.join(timeout=timeout)

# Singleton instance for easy use
_client = None

def get_timing_client():
    global _client
    if _client is None:
        _client = TimingClient()
    return _client

def report_task_status(task_id: str, status: str):
    client = get_timing_client()
    client.send_status(task_id, status)

def flush_timing():
    global _client
    if _client is not None:
        _client.flush()

atexit.register(flush_timing)

def time_task(task_name: str):
    """
    Decorator to report task start and end.
    task_name is a string that prefixes the task.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
              if len(args) > 0:
                task_id = f"{task_name}.{str(args[0])}"
              else:
                task_id = task_name
              # attempt to get a molid label from the kwargs
              if "moleculeid" in kwargs:
                molid = kwargs["moleculeid"]
                task_id = f"{task_name}.{molid}"
              elif "molecule_object" in kwargs:
                molid = kwargs["molecule_object"].get_moleculeid()
                task_id = f"{task_name}.{molid}"
            except Exception:
              task_id = task_name

            report_task_status(task_id, "start")
            try:
                result = func(*args, **kwargs)
                report_task_status(task_id, "end")
                return result
            except Exception as e:
                report_task_status(task_id, f"error: {str(e)}")
                raise e
        return wrapper
    return decorator
