import os

# Bind to the port Render provides (or 5000 locally)
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Number of worker processes
# Rule of thumb: 2-4 x number of CPU cores
workers = 2

# Worker class
worker_class = "sync"

# Timeout (seconds) — increase for heavy ML predictions
timeout = 120

# Log level
loglevel = "info"
accesslog = "-"   # Log to stdout
errorlog  = "-"   # Log to stdout

# Restart workers after this many requests (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 100
