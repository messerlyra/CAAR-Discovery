import zmq
import json
import datetime
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="CAAR Timing Server")
    parser.add_argument("--port", type=int, default=5555, help="Port to listen on")
    parser.add_argument("--log", type=str, default="task_timings.csv", help="Log file path")
    args = parser.parse_args()

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{args.port}")

    print(f"Timing server started on port {args.port}. Logging to {args.log}")
    
    # Initialize log file with header
    if not os.path.exists(args.log):
        with open(args.log, "w") as f:
            f.write("timestamp,task_id,status,node\n")

    while True:
        try:
            # Wait for next request from a client
            message = socket.recv_json()
            
            task_id = message.get("task_id", "unknown")
            status = message.get("status", "unknown")
            node = message.get("node", "unknown")
            
            timestamp = datetime.datetime.now().isoformat()
            
            log_entry = f"{timestamp},{task_id},{status},{node}\n"
            with open(args.log, "a") as f:
                f.write(log_entry)
            
            # Send reply to client
            socket.send_json({"status": "ok"})
            
        except Exception as e:
            print(f"Error processing message: {e}")
            # Still send a reply to avoid blocking the client
            try:
                socket.send_json({"status": "error", "message": str(e)})
            except:
                pass

if __name__ == "__main__":
    main()
