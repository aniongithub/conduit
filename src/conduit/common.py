import functools
import inspect
import logging
from pydoc import locate
from importlib import import_module
import commentjson
import yaml
from typing import NamedTuple
from urllib.parse import urlparse
from urllib.request import urlopen, Request
import os
from python_log_indenter import IndentedLoggerAdapter

class ColorFormatter(logging.Formatter):
    lightgray = "\x1b[1;30m"
    gray = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: lightgray + format + reset,
        logging.INFO: gray + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
    
_logger = None

def logger() -> logging.Logger:
    global _logger
    if _logger is None:
        log = logging.getLogger(f"conduit-log")
        log.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(log.getEffectiveLevel())
        ch.setFormatter(ColorFormatter())
        log.addHandler(ch)
        _logger = IndentedLoggerAdapter(log)
        _logger.setLevel(log.getEffectiveLevel())

    return _logger

def set_log_level(level: str):
    """Set the global log level for the conduit logger"""
    global _logger
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    # Get or create logger
    log_instance = logger()
    
    # Set level on both the underlying logger and its handler
    underlying_logger = log_instance.logger if hasattr(log_instance, 'logger') else log_instance
    underlying_logger.setLevel(numeric_level)
    
    # Update handler level
    for handler in underlying_logger.handlers:
        handler.setLevel(numeric_level)
    
    # Update adapter level
    log_instance.setLevel(numeric_level)

class MalformedPipelineElement(Exception):
    pass

def instantiate(class_str: str, **kwargs):
    if class_str is None:
        return None
    try:
        module_path, class_name = class_str.rsplit('.', 1)
        module = import_module(module_path)
        klass = getattr(module, class_name)

        if klass == type(()):
            signature = inspect.signature(klass.__init__)
            instance = klass(kwargs.values())
        else:
            signature = inspect.signature(klass.__init__)
            constructor_args = {}

            for name, param in signature.parameters.items():
                if name == "self" or name == "args" or name == "kwargs":
                    continue
                if name in kwargs:
                    constructor_args[name] = kwargs[name]
                    kwargs.pop(name)
                else:
                    if param.default == param.empty:
                        raise ValueError(f"Missing required argument: {name}")
            
            instance = klass(**constructor_args)        
            for k, v in kwargs.items():
                setattr(instance, k, v)
        
        return instance
    except (ImportError, AttributeError) as ex:
        raise ex

def json2obj(filename): 
    f = None
    try:
        f = open(filename)
        data = f.read()
        return commentjson.loads(data, object_hook=lambda d: NamedTuple('X', d.keys())(*d.values()))
    except Exception as e:
        print(e)
        return None
    finally:
        if f is not None:
            f.close()

def loadjson(filename, expand_env: bool = False): 
    f = None
    try:
        f = open(filename)
        data = f.read()
        if expand_env:
            data = expand_env_vars(data)
        return commentjson.loads(data)
    except Exception as e:
        print(e)
        return None
    finally:
        if f is not None:
            f.close()

def loads(data, expand_env: bool = False):
    try:
        if expand_env:
            data = expand_env_vars(data)
        return commentjson.loads(data)
    except Exception as e:
        print(e)
        return None

def expand_env_vars(text: str) -> str:
    """Expand environment variables with support for ${VAR:-default} syntax."""
    import re
    
    def replacer(match):
        var_expr = match.group(1)
        if ':-' in var_expr:
            var_name, default_value = var_expr.split(':-', 1)
            # Remove quotes from default value if present
            default_value = default_value.strip('\'"')
            return os.environ.get(var_name, default_value)
        else:
            return os.environ.get(var_expr, match.group(0))
    
    # Handle ${VAR:-default} and ${VAR} patterns
    text = re.sub(r'\$\{([^}]+)\}', replacer, text)
    # Handle $VAR patterns
    text = os.path.expandvars(text)
    return text

def loadyaml(filename, expand_env: bool = False):
    f = None
    try:
        f = open(filename)
        data = f.read()
        if expand_env:
            data = expand_env_vars(data)
        return yaml.load(data, Loader = yaml.FullLoader)
    except Exception as e:
        print(e)
        return None
    finally:
        if f is not None:
            f.close()

def is_url(resource):
    result = urlparse(resource)
    return all([result.scheme, result.netloc])

def url_data(url):
    try:
        return urlopen(Request(url))
    except:
        return None

def is_local(resource):
    return os.path.exists(resource)

def local_data(path):
    with open(path, "rb") as f:
        return f.read()

def get_data(resource):
    if is_url(resource):
        return url_data(resource)
    elif is_local(resource):
        return local_data(resource)
    else:
        return None
    
from typing import Union

def get_default_logger():
    return logger()

def log(_func=None, *, my_logger: Union[logging.Logger] = None):
    def decorator_log(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if my_logger is None:
                logger = get_default_logger()
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            logger.debug(f"function {func.__name__} called with args {signature}")
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                logger.exception(f"Exception raised in {func.__name__}. exception: {str(e)}")
                raise e
        return wrapper

    if _func is None:
        return decorator_log
    else:
        return decorator_log(_func)