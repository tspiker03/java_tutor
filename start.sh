#!/bin/bash
PORT="${PORT:-5000}"
exec gunicorn app:app --bind "0.0.0.0:$PORT"
