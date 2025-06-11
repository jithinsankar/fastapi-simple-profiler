# fastapi_simple_profiler/__init__.py
# This file marks the directory as a Python package.

from .middleware import ProfilerMiddleware
# Import profiler_instance from profiler_data to avoid circular dependency
from .profiler_data import profiler_instance
