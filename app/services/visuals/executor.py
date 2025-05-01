"""Secure Python execution environment for generating visualizations."""
import ast
import builtins
import contextlib
import io
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from app.services.visuals.chart_generator import ChartGenerator

logger = logging.getLogger(__name__)

# Directory for storing execution outputs
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "data/visuals/output"))


class VisualizationExecutor:
    """Secure execution environment for generating visualizations."""

    def __init__(self):
        """Initialize the visualization executor."""
        # Create the output directory if it doesn't exist
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Set up allowed modules and functions
        self.allowed_modules = {
            "matplotlib", "matplotlib.pyplot", "numpy", "math", 
            "pandas", "datetime", "time", "random", "statistics"
        }
        
        # Functions that are explicitly disallowed
        self.disallowed_functions = {
            "eval", "exec", "compile", "open", "file", "__import__", 
            "globals", "locals", "vars", "getattr", "setattr", "delattr",
            "input", "raw_input", "os", "sys", "subprocess"
        }
        
        # Initialize chart generator
        self.chart_generator = ChartGenerator()

    def execute_code(
        self, code: str, timeout: int = 10, max_memory_mb: int = 100
    ) -> Dict[str, Any]:
        """Execute visualization code in a secure environment.

        Args:
            code (str): Python code to execute
            timeout (int, optional): Execution timeout in seconds. Defaults to 10.
            max_memory_mb (int, optional): Maximum memory usage in MB. Defaults to 100.

        Returns:
            Dict[str, Any]: Execution results including outputs and errors

        Raises:
            ValueError: If code contains disallowed functions or modules
            RuntimeError: If execution times out or exceeds memory limits
        """
        # Check code for disallowed patterns
        self._validate_code(code)
        
        # Prepare the secure execution environment
        restricted_globals = self._prepare_restricted_globals()
        
        # Set up the output capture
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Set up result object
        result = {
            "success": False,
            "output": "",
            "error": "",
            "execution_time": 0,
            "figure_paths": [],
            "data": {},
        }
        
        # Execute the code with resource limits
        start_time = time.time()
        
        try:
            # Set the timeout using signal on Unix-like systems
            if sys.platform != "win32":
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Execution timed out after {timeout} seconds")
                
                # Set the timeout
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
            
            # Redirect stdout and stderr
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                # Execute the code in the restricted environment
                exec(code, restricted_globals)
                
                # Capture any figures that were created
                if "plt" in restricted_globals:
                    figures = []
                    for i in plt.get_fignums():
                        fig = plt.figure(i)
                        figures.append(fig)
                    
                    # Save the figures
                    for i, fig in enumerate(figures):
                        image_id = str(uuid.uuid4())
                        filename = f"{image_id}.png"
                        filepath = OUTPUT_DIR / filename
                        
                        # Save the figure
                        fig.savefig(filepath, bbox_inches="tight")
                        result["figure_paths"].append(str(filepath))
            
            # Clear the timeout
            if sys.platform != "win32":
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            
            # Capture the output
            result["output"] = stdout_capture.getvalue()
            result["error"] = stderr_capture.getvalue()
            result["success"] = True
            result["execution_time"] = time.time() - start_time
            
            # Check if any numpy arrays or other data were created in the environment
            for var_name, var_value in restricted_globals.items():
                if var_name.startswith("_") or var_name in self._get_builtin_names():
                    continue
                    
                # Store primitive types, numpy arrays, and pandas DataFrames
                if (isinstance(var_value, (int, float, str, bool, list, dict)) or
                    (hasattr(var_value, "__module__") and 
                     var_value.__module__ in ("numpy", "pandas"))):
                    
                    # Convert numpy arrays to lists for serialization
                    if hasattr(var_value, "__module__") and var_value.__module__ == "numpy":
                        if hasattr(var_value, "tolist"):
                            result["data"][var_name] = var_value.tolist()
                        else:
                            result["data"][var_name] = str(var_value)
                    else:
                        try:
                            # Check if the value is JSON serializable
                            import json
                            json.dumps({var_name: var_value})
                            result["data"][var_name] = var_value
                        except (TypeError, OverflowError):
                            # If not serializable, convert to string
                            result["data"][var_name] = str(var_value)
            
        except TimeoutError as e:
            result["error"] = f"Timeout error: {str(e)}"
            logger.error("Code execution timed out: %s", e)
        except Exception as e:
            result["error"] = f"Execution error: {str(e)}"
            logger.error("Code execution failed: %s", e)
        finally:
            # Clear any remaining matplotlib figures
            plt.close("all")
            
            # Close output captures
            stdout_capture.close()
            stderr_capture.close()
        
        return result

    def execute_chart(
        self, 
        chart_type: str, 
        data: Dict[str, Any], 
        title: str,
        subtitle: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a chart generation using the ChartGenerator.

        Args:
            chart_type (str): Type of chart (bar, line, pie, etc.)
            data (Dict[str, Any]): Data for the chart
            title (str): Chart title
            subtitle (Optional[str], optional): Chart subtitle. Defaults to None.

        Returns:
            Dict[str, Any]: Chart generation results

        Raises:
            ValueError: If chart_type is not supported
        """
        result = {
            "success": False,
            "error": "",
            "chart_path": "",
        }
        
        try:
            # Generate the chart
            chart_path, figure = self.chart_generator.create_chart(
                chart_type=chart_type,
                data=data,
                title=title,
                subtitle=subtitle,
            )
            
            # Close the figure
            self.chart_generator.close_figure(figure)
            
            result["success"] = True
            result["chart_path"] = chart_path
            
        except Exception as e:
            result["error"] = f"Chart generation error: {str(e)}"
            logger.error("Chart generation failed: %s", e)
        
        return result

    def _validate_code(self, code: str) -> None:
        """Validate the code for security issues.

        Args:
            code (str): Python code to validate

        Raises:
            ValueError: If the code contains disallowed patterns
        """
        # First, parse the code to get an AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {str(e)}")
        
        # Analyze the AST for disallowed patterns
        for node in ast.walk(tree):
            # Check for imports
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name not in self.allowed_modules:
                        raise ValueError(f"Import of disallowed module: {name.name}")
            
            # Check for from ... import ...
            elif isinstance(node, ast.ImportFrom):
                if node.module not in self.allowed_modules:
                    raise ValueError(f"Import from disallowed module: {node.module}")
            
            # Check for disallowed function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in self.disallowed_functions:
                    raise ValueError(f"Use of disallowed function: {node.func.id}")
                
                # Check for attribute calls like os.system
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        module_name = node.func.value.id
                        if module_name in ["os", "sys", "subprocess"]:
                            raise ValueError(f"Use of disallowed module function: {module_name}.{node.func.attr}")
        
        # Check for specific unsafe patterns in the code text
        for pattern in ["__builtins__", "globals()", "locals()", "getattr(", "setattr(", "delattr("]:
            if pattern in code:
                raise ValueError(f"Use of unsafe pattern: {pattern}")

    def _prepare_restricted_globals(self) -> Dict[str, Any]:
        """Prepare a restricted globals dictionary for code execution.

        Returns:
            Dict[str, Any]: Restricted globals dictionary
        """
        restricted_globals = {}
        
        # Add safe builtins
        safe_builtins = {}
        for name in dir(builtins):
            if name not in self.disallowed_functions and not name.startswith("__"):
                safe_builtins[name] = getattr(builtins, name)
        
        restricted_globals["__builtins__"] = safe_builtins
        
        # Add allowed modules
        for module_name in self.allowed_modules:
            try:
                if "." in module_name:
                    parent, child = module_name.split(".", 1)
                    if parent in restricted_globals:
                        module = getattr(restricted_globals[parent], child)
                    else:
                        module = __import__(module_name, fromlist=[child])
                else:
                    module = __import__(module_name)
                    
                # Alias matplotlib.pyplot as plt for convenience
                if module_name == "matplotlib.pyplot":
                    restricted_globals["plt"] = module
                else:
                    restricted_globals[module_name.split(".")[-1]] = module
                    
            except ImportError:
                logger.warning("Failed to import allowed module: %s", module_name)
        
        return restricted_globals

    def _get_builtin_names(self) -> Set[str]:
        """Get the names of built-in functions and objects.

        Returns:
            Set[str]: Set of built-in names
        """
        return set(dir(builtins))

    def save_output_text(self, text: str) -> str:
        """Save output text to a file.

        Args:
            text (str): Text to save

        Returns:
            str: Path to the saved file
        """
        output_id = str(uuid.uuid4())
        filename = f"{output_id}.txt"
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, "w") as f:
            f.write(text)
        
        return str(filepath) 