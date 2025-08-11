import logging
import sys

def configure_logging(debug: bool = True):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root.handlers = [handler]
