# Gunicorn settings (Render picks this file up automatically)
workers = 1
threads = 4      # handle a few requests at once on the free plan
timeout = 120    # allow slower PDF and image processing
