#!/bin/bash

set -e

PY_PATH=".venv/bin/python3"
OUTPUT_DIR="output"
DEV=false

if [[ ! -x "$PY_PATH" ]]; then
    echo "Error: python not found at $PY_PATH"
    exit 1
fi

help () {

cat << _EOF_

Run deployments.

-h | --help
print help

-d | --dev
run build script and start dev server

_EOF_
}

while [[ -n "$1" ]]; do
        case "$1" in
            -d | --dev)
                DEV=true
                ;;
            -h | --help)
                help
                exit
                ;;
        esac
        shift
done

echo "building site"
"$PY_PATH" ssg.py
echo "build finished"

if [[ "$DEV" == true ]]; then
    echo "starting dev server"
    "$PY_PATH" -m http.server --directory "$OUTPUT_DIR"
fi

