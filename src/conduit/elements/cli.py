from typing import Generator, Iterator, List, Optional
import subprocess
from dataclasses import dataclass, field, MISSING

from conduit.pipelineElement import PipelineElement

@dataclass
class CliElementInput:
    """Input specification for CliElement
    
    All fields are optional - if not provided, will use the defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    command: Optional[str] = None
    arguments: Optional[List[str]] = None
    working_directory: Optional[str] = None
    timeout: Optional[int] = None
    capture_output: Optional[bool] = None
    check: Optional[bool] = None
    text: Optional[bool] = None
    encoding: Optional[str] = None

class CliElement(PipelineElement):
    """Execute shell commands with global defaults and per-datum overrides
    
    Constructor parameters set global defaults for all executions.
    Per-datum input can override any of these defaults for specific commands.
    """
    
    def __init__(self, command: str, arguments: List[str], working_directory: Optional[str] = ".", timeout: Optional[int] = -1, capture_output: Optional[bool] = False, check: Optional[bool] = False, text: Optional[bool] = None, encoding: Optional[str] = "utf-8"):
        super().__init__()  # Automatically captures all constructor parameters

    def process(self, input: Iterator[CliElementInput]) -> Generator[str | int, None, None]:
        for cli_input in input:
            # Apply constructor defaults to None fields
            cli_input = self.apply_defaults(cli_input)
            
            # Format arguments if they contain format strings
            formatted_args = [arg.format(input=cli_input) for arg in cli_input.arguments]
            
            result = subprocess.run(
                [cli_input.command] + formatted_args,
                cwd=cli_input.working_directory,
                timeout=cli_input.timeout if cli_input.timeout > 0 else None,
                capture_output=cli_input.capture_output,
                check=cli_input.check,
                text=cli_input.text,
                encoding=cli_input.encoding
            )
            
            if cli_input.capture_output:
                yield result.stdout
            else:
                yield result.returncode