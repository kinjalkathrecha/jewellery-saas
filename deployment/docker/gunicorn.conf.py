import os

bind = f"0.0.0.0:{os.environ.get('PORT', 8000)}"

# Number of Gunicorn workers
workers = int(os.environ.get("GUNICORN_WORKERS", 4))

# Thread count per worker
threads = int(os.environ.get("GUNICORN_THREADS", 2))

# Maximum request timeout
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))

# Logging configuration
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Preload application to share memory between workers
preload_app = True
