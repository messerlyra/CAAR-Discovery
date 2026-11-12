#!/usr/bin/env bash
# start_timing_server.sh — source this to start the ZMQ timing collector
# and export CAAR_TIMING_SERVER dynamically.
#
# Follows src/timing/test_timing.sh pattern: launch timing_server.py in
# background, log to a CSV, and export CAAR_TIMING_SERVER for workers.
#
# Usage (sourced):
#   source start_timing_server.sh <log_file> [port]
#
# Sets/exports:
#   CAAR_TIMING_SERVER, TIMING_LOG, TIMING_PORT, TIMING_HOST
#
# Starts server in background and records PID to $log_file.pid
# Installs a trap to clean up the server on exit (caller shell).

if [[ -z "${ENVIRONMENT_SCRIPT:-}" ]]; then
    ENVIRONMENT_SCRIPT="/lustre/orion/world-shared/csc728/messerlyra/scripts/load_caar_env.bash"
fi

# If CAAR_TIMING_SERVER already set and server appears alive, reuse it
if [[ -n "${CAAR_TIMING_SERVER:-}" ]]; then
    return 0 2>/dev/null || exit 0
fi

if [[ -z "${TIMING_LOG:-}" ]]; then
    echo "Warning, no timing server started. TIMING_LOG must be defined!"
    return 0 2>/dev/null || exit 0
fi
TIMING_PORT="${TIMING_PORT:-12710}"

if [ ! -d "$BASE_DIR" ]; then
    readonly BASE_DIR=$(dirname $(realpath "${BASH_SOURCE[0]}"))
fi

TIMING_SERVER_SCRIPT="$BASE_DIR/../src/timing/timing_server.py"

if [[ ! -f "$TIMING_SERVER_SCRIPT" ]]; then
    echo "Warning: timing server script not found: $TIMING_SERVER_SCRIPT (timing disabled)" >&2
    return 0 2>/dev/null || exit 0
fi

# Determine HSN address dynamically (matches Frontier login/compute hsn0)
TIMING_HOST=$(ip -4 addr show hsn0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n1)
if [[ -z "$TIMING_HOST" ]]; then
    TIMING_HOST=$(hostname -f 2>/dev/null || hostname)
fi

# Find a free port if the default is in use
if command -v ss >/dev/null 2>&1 && ss -tlnH "sport = :$TIMING_PORT" 2>/dev/null | grep -q "$TIMING_PORT"; then
    for try_port in $(seq 12710 12810); do
        if ! ss -tlnH "sport = :$try_port" 2>/dev/null | grep -q "$try_port"; then
            TIMING_PORT=$try_port
            break
        fi
    done
fi

export CAAR_TIMING_SERVER="tcp://${TIMING_HOST}:${TIMING_PORT}"
echo "Starting timing server on $CAAR_TIMING_SERVER, logging to $TIMING_LOG"

# Launch collector in background after sourcing CAAR env for zmq
# Do not use a subshell for the background job so $! is captured correctly
# shellcheck disable=SC1090
source "$ENVIRONMENT_SCRIPT" 2>/dev/null || true
export PYTHONPATH="$BASE_DIR/../src:$PYTHONPATH"
mkdir -p "$(dirname "$TIMING_LOG")"
python -u "$TIMING_SERVER_SCRIPT" --port "$TIMING_PORT" --log "$TIMING_LOG" &
TIMING_PID=$!
echo $TIMING_PID >"$TIMING_LOG.pid"

sleep 1
if [[ -f "$TIMING_LOG.pid" ]]; then
    echo "Timing server PID $TIMING_PID"
    # Clean up server when caller exits
    trap 'kill $TIMING_PID 2>/dev/null || true; rm -f "$TIMING_LOG.pid"' EXIT
fi
