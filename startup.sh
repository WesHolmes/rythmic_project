#!/bin/bash
gunicorn --bind=0.0.0.0:8000 --workers=4 --timeout=600 --keep-alive=2 --max-requests=1000 app:app
