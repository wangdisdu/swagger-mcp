#!/bin/sh

DIR=$(cd "$(dirname "$0")" && pwd)
cd $DIR

export MCP_SERVER_HOME=$DIR

mkdir -p ${MCP_SERVER_HOME}/logs

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}
LOG_LEVEL=${LOG_LEVEL:-info}
LOG_CONFIG=${LOG_CONFIG:-${MCP_SERVER_HOME}/logging.ini}
APP=${APP:-src.server:app}

uvicorn $APP --host $HOST --port $PORT --log-config $LOG_CONFIG
