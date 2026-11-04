import socket
import json
import datetime
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="CAAR Timing Server")
    parser.add_argument("--port", type=int, default=5555, help="Port to listen on")
    parser.add_argument("--log", type=str, default="task_timings.csv", help="Log file path")
    args = parser.parse_args()

    # Initialize log file with header
    if not os.path.exists(args.log):
        with open(args.log, "w") as f:
            f.write("timestamp,task_id,status,node\n")

    # Create raw TCP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('', args.port))
        server_sock.listen(5)
        print(f"Timing server started on port {args.port}. Logging to {args.log}")

        while True:
            try:
                conn, addr = server_sock.accept()
                with conn:
                    # Read until newline
                    data = b""
                    while True:
                        chunk = conn.recv(1024)
                        if not chunk:
                            break
                        data += chunk
                        if b"\n" in data:
                            break

                    if not data:
                        continue

                    # Process only the first line
                    line = data.split(b"\n")[0].decode('utf-8')
                    if not line:
                        continue

                    message = json.loads(line)

                    task_id = message.get("task_id", "unknown")
                    status = message.get("status", "unknown")
                    node = message.get("node", "unknown")

                    timestamp = datetime.datetime.now().isoformat()

                    log_entry = f"{timestamp},{task_id},{status},{node}\n"
                    with open(args.log, "a") as f:
                        f.write(log_entry)

            except Exception as e:
                print(f"Error processing connection: {e}")

if __name__ == "__main__":
    main()
