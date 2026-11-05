import zmq
import json
import socket
import os
import datetime
import functools
import threading
import queue

class TimingClient:
    def __init__(self, server_addr=None):
        # server_addr or environment variable or default
        self.server_url = server_addr or os.environ.get("CAAR_TIMING_SERVER", "tcp://localhost:5555")

        # Queue for outgoing messages
        self.msg_queue = queue.Queue()

        # Start background sender thread
        self.sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self.sender_thread.start()

    def _sender_loop(self):
        """
        Background thread that handles the synchronous ZMQ REQ/REP communication.
        """
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        # Set a timeout so we don't hang forever if the server is down
        socket.setsockopt(zmq.RCVTIMEO, 2000)
        socket.connect(self.server_url)

        while True:
            try:
                # Get message from queue
                message = self.msg_queue.get()

                # Send to server
                socket.send_json(message)

                # Wait for reply (required by REQ socket)
                try:
                    socket.recv_json()
                except zmq.Again:
                    # Server didn't respond in time.
                    # We must reset the socket or handle the state because
                    # a REQ socket is stuck in 'waiting for reply' state.
                    # The simplest way to recover a REQ socket is to recreate it.
                    socket.close()
                    socket = context.socket(zmq.REQ)
                    socket.setsockopt(zmq.RCVTIMEO, 2000)
                    socket.connect(self.server_url)

                self.msg_queue.task_done()
            except Exception as e:
                # Log error to stderr but keep the thread alive
                import sys
                print(f"TimingClient background sender error: {e}", file=sys.stderr)

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

def time_task(task_name: str):
    """
    Decorator to report task start and end.
    task_name is a string that prefixes the task.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if len(args) > 0:
                task_id = f"{task_name}.{str(args[0])}"
            else:
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
