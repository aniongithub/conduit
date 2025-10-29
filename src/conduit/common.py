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
    """Colored console formatter with customizable format string"""
    
    lightgray = "\x1b[1;30m"
    gray = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    def __init__(self, format_string=None, use_colors=True):
        super().__init__()
        self.use_colors = use_colors
        self.format_string = format_string or "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
        
        if self.use_colors:
            self.FORMATS = {
                logging.DEBUG: self.lightgray + self.format_string + self.reset,
                logging.INFO: self.gray + self.format_string + self.reset,
                logging.WARNING: self.yellow + self.format_string + self.reset,
                logging.ERROR: self.red + self.format_string + self.reset,
                logging.CRITICAL: self.bold_red + self.format_string + self.reset
            }
        else:
            self.FORMATS = {
                level: self.format_string for level in [
                    logging.DEBUG, logging.INFO, logging.WARNING, 
                    logging.ERROR, logging.CRITICAL
                ]
            }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class SimpleFormatter(logging.Formatter):
    """Simple formatter for clean output"""
    
    def __init__(self, format_string=None):
        super().__init__()
        self.format_string = format_string or "%(levelname)s: %(message)s"
    
    def format(self, record):
        formatter = logging.Formatter(self.format_string)
        return formatter.format(record)


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for machine-readable logs"""
    
    def format(self, record):
        import json
        log_record = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)
    
_logger = None
_logger_config = None

def logger(
    level: str = None,
    format_type: str = None,
    format_string: str = None,
    output: str = None,
    filename: str = None,
    use_indentation: bool = None,
    use_colors: bool = None,
    reset: bool = False
) -> logging.Logger:
    """
    Get or create a configurable logger instance.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) - None uses configured default
        format_type: Formatter type ('color', 'simple', 'structured') - None uses configured default
        format_string: Custom format string (overrides format_type)
        output: Output destination ('console', 'file', 'both') - None uses configured default
        filename: Log file path (required if output includes 'file')
        use_indentation: Whether to use IndentedLoggerAdapter - None uses configured default
        use_colors: Force color usage on/off (auto-detect if None)
        reset: Force recreation of logger
    
    Returns:
        Configured logger instance
    """
    global _logger, _logger_config
    
    # Apply defaults from _logger_config if parameters are None
    if _logger_config is not None:
        level = level if level is not None else _logger_config.get('level', 'INFO')
        format_type = format_type if format_type is not None else _logger_config.get('format_type', 'color')
        format_string = format_string if format_string is not None else _logger_config.get('format_string', None)
        output = output if output is not None else _logger_config.get('output', 'console')
        filename = filename if filename is not None else _logger_config.get('filename', None)
        use_indentation = use_indentation if use_indentation is not None else _logger_config.get('use_indentation', True)
        use_colors = use_colors if use_colors is not None else _logger_config.get('use_colors', None)
    else:
        # Fallback to hardcoded defaults if no config exists
        level = level if level is not None else 'INFO'
        format_type = format_type if format_type is not None else 'color'
        output = output if output is not None else 'console'
        use_indentation = use_indentation if use_indentation is not None else True
    
    # Create config dict for comparison
    current_config = {
        'level': level,
        'format_type': format_type,
        'format_string': format_string,
        'output': output,
        'filename': filename,
        'use_indentation': use_indentation,
        'use_colors': use_colors
    }
    
    # Return existing logger if config hasn't changed and reset not requested
    if not reset and _logger is not None and _logger_config == current_config:
        return _logger
    
    # Auto-detect color support if not specified
    if use_colors is None:
        use_colors = hasattr(os.sys.stdout, 'isatty') and os.sys.stdout.isatty()
    
    # Create new logger
    log = logging.getLogger("conduit-log")
    
    # Clear existing handlers if resetting
    if reset or _logger is not None:
        log.handlers.clear()
    
    # Set log level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    log.setLevel(numeric_level)
    
    # Create formatter
    if format_string:
        formatter = logging.Formatter(format_string)
    elif format_type == "color":
        formatter = ColorFormatter(use_colors=use_colors)
    elif format_type == "simple":
        formatter = SimpleFormatter()
    elif format_type == "structured":
        formatter = StructuredFormatter()
    else:
        formatter = ColorFormatter(use_colors=use_colors)
    
    # Add handlers based on output configuration
    if output in ("console", "both"):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        log.addHandler(console_handler)
    
    if output in ("file", "both"):
        if not filename:
            raise ValueError("filename must be provided when output includes 'file'")
        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(numeric_level)
        # Use structured format for file output unless custom format specified
        if not format_string and format_type == "color":
            file_formatter = StructuredFormatter()
        else:
            file_formatter = formatter
        file_handler.setFormatter(file_formatter)
        log.addHandler(file_handler)
    
    # Wrap with IndentedLoggerAdapter if requested
    if use_indentation:
        _logger = IndentedLoggerAdapter(log)
        _logger.setLevel(numeric_level)
    else:
        _logger = log
    
    # Store config for future comparisons
    _logger_config = current_config
    
    return _logger

def set_log_level(level: str):
    """Set the global log level for the conduit logger"""
    global _logger, _logger_config
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    # Update existing logger if it exists
    if _logger is not None:
        # Update config
        if _logger_config:
            _logger_config['level'] = level.upper()
        
        # Set level on both the underlying logger and its handlers
        underlying_logger = _logger.logger if hasattr(_logger, 'logger') else _logger
        underlying_logger.setLevel(numeric_level)
        
        # Update handler levels
        for handler in underlying_logger.handlers:
            handler.setLevel(numeric_level)
        
        # Update adapter level if using IndentedLoggerAdapter
        if hasattr(_logger, 'setLevel'):
            _logger.setLevel(numeric_level)
    else:
        # Create new logger with specified level
        logger(level=level.upper())

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