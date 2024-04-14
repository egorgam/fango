import inspect
import logging
from functools import wraps

from django.conf import settings

logger = logging.Logger("uvicorn.access")
handler = logging.StreamHandler()

__all__ = ["logger", "log_params"]


class ColoredFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset,
        }

    def format(self, record):
        record.levelname = f"{record.levelname}:".ljust(10)
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


handler.setFormatter(ColoredFormatter("%(levelname)s%(message)s"))
logger.setLevel(logging.INFO)
logger.addHandler(handler)

arg_prefix = "\t\t--> "


def log_params(prefix):
    """
    Decorator for logging function call with args.

    """

    def log(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if settings.ENABLE_CALL_LOG:
                bound_arguments = inspect.signature(func).bind(*args, **kwargs)
                bound_arguments.apply_defaults()
                args_reprs = [arg_prefix + f"{name}={value!r}" for name, value in bound_arguments.arguments.items()]
                signature = "\n".join(args_reprs)
                logger.info(f"[{prefix}] call: {func.__name__} with params:\n{signature}\n")
            return func(*args, **kwargs)

        return wrapper

    return log
