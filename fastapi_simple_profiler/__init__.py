# fastapi_simple_profiler/__init__.py
# This file marks the directory as a Python package.
# It also allows for easier imports like 'from fastapi_simple_profiler import ProfilerMiddleware'

from .middleware import ProfilerMiddleware
from .profiler_data import FastAPIProfiler

# Create a global instance of the profiler for easy access
profiler_instance = FastAPIProfiler()

# fastapi_simple_profiler/profiler_data.py
import pandas as pd
from typing import List, Dict, Any
import io
import threading
import time # Import time for timestamp formatting

class FastAPIProfiler:
    """
    Manages in-memory storage of profiled request data and handles CSV export.
    Implemented as a singleton to ensure a single source of truth for profiling data.
    """
    _instance = None
    _lock = threading.Lock() # Lock for thread-safe data access

    def __new__(cls):
        """
        Ensures only one instance of FastAPIProfiler exists (singleton pattern).
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check lock to prevent race conditions during initialization
                if cls._instance is None:
                    cls._instance = super(FastAPIProfiler, cls).__new__(cls)
                    # Initialize attributes for the new instance
                    cls._instance.profiled_requests_data: List[Dict[str, Any]] = []
                    cls._instance.max_retained_requests = 1000 # Default max requests to keep in memory
        return cls._instance

    def configure(self, max_retained_requests: int = 1000):
        """
        Configures the profiler's data retention policy.

        Args:
            max_retained_requests (int): Maximum number of requests to retain in memory.
                                         Defaults to 1000.
        Raises:
            ValueError: If max_retained_requests is less than 1.
        """
        if max_retained_requests < 1:
            raise ValueError("max_retained_requests must be at least 1.")
        self.max_retained_requests = max_retained_requests
        # Prune immediately if the new configuration is smaller than current data size
        self._prune_old_data()

    def add_profile_data(self, data: Dict[str, Any]):
        """
        Adds a single profiled request's data to the in-memory store.
        Ensures thread-safe appending and pruning.

        Args:
            data (Dict[str, Any]): A dictionary containing profiled metrics for a request.
                                   Expected keys: Timestamp, RequestPath, HTTPMethod,
                                   StatusCode, TotalTimeMs, CPUTimeMs.
        """
        with self._lock:
            self.profiled_requests_data.append(data)
            self._prune_old_data()

    def _prune_old_data(self):
        """
        Internal method to prune old data to adhere to the max_retained_requests policy.
        This keeps only the most recent N requests.
        """
        if len(self.profiled_requests_data) > self.max_retained_requests:
            # Efficiently slice the list to keep only the latest N entries
            self.profiled_requests_data = self.profiled_requests_data[-self.max_retained_requests:]

    def get_profile_data(self) -> List[Dict[str, Any]]:
        """
        Retrieves all currently stored profiled request data.
        Returns a copy to prevent external modification issues.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a profiled request.
        """
        with self._lock:
            return list(self.profiled_requests_data) # Return a copy

    def clear_data(self):
        """
        Clears all stored profiling data from memory.
        Ensures thread-safe clearing.
        """
        with self._lock:
            self.profiled_requests_data = []

    def export_to_csv(self) -> io.StringIO:
        """
        Exports the stored profiling data to a CSV formatted StringIO object.
        This StringIO object can be used directly with FastAPI's StreamingResponse.

        Returns:
            io.StringIO: A StringIO object containing the CSV data.
        """
        data_to_export = self.get_profile_data()

        # Define the desired order and default columns for the CSV
        desired_columns = [
            "Timestamp", "RequestPath", "HTTPMethod", "StatusCode",
            "TotalTimeMs", "CPUTimeMs"
        ]

        if not data_to_export:
            # If no data, create an empty DataFrame with the desired headers
            df = pd.DataFrame(columns=desired_columns)
        else:
            df = pd.DataFrame(data_to_export)

            # Ensure all desired columns are present, filling missing with NaN if necessary
            # and reorder columns as per desired_columns list
            for col in desired_columns:
                if col not in df.columns:
                    df[col] = pd.NA # Use pandas Not Available for missing data

            # Reorder columns to the desired sequence
            df = df[desired_columns]

        csv_buffer = io.StringIO()
        # Export DataFrame to CSV string. index=False prevents writing the DataFrame index.
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0) # Rewind the buffer to the beginning for reading
        return csv_buffer


# fastapi_simple_profiler/middleware.py
import time
import os
import json
from typing import Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

try:
    # Attempt to import Profiler from pyinstrument.
    # This is a core dependency for detailed CPU profiling.
    from pyinstrument import Profiler
except ImportError:
    # If pyinstrument is not installed, set Profiler to None.
    # The middleware will still function but will not capture CPUTimeMs.
    print("Warning: pyinstrument not found. CPUTimeMs will not be available.")
    Profiler = None

# Import the global profiler instance from the __init__.py which ensures
# the singleton instance is used across the application.
from . import profiler_instance

class ProfilerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to profile FastAPI requests and store performance metrics.

    This middleware integrates with pyinstrument (if available) to capture
    detailed profiling data per request. It then processes this data to extract
    key metrics (wall time, CPU time) and stores them in an in-memory profiler instance.

    Profiling can be activated conditionally based on:
    - `enable_by_default`: If True, profiling is active for all requests.
    - `FASTAPI_SIMPLE_PROFILER_ENABLED` environment variable: If "true" (case-insensitive),
      profiling is active for all requests.
    - `profile_query_param`: A specific query parameter (e.g., `?profile=true`)
      can explicitly enable/disable profiling for an individual request.
    """

    def __init__(self, app: ASGIApp,
                 enable_by_default: bool = False,
                 profile_query_param: str = "profile",
                 max_retained_requests: int = 1000):
        """
        Initializes the ProfilerMiddleware.

        Args:
            app (ASGIApp): The ASGI application (FastAPI instance) to wrap.
            enable_by_default (bool): If True, profiling is enabled for all requests
                                      unless explicitly disabled by the query parameter.
                                      Defaults to False.
            profile_query_param (str): The query parameter key (e.g., "profile")
                                       to toggle profiling for individual requests.
                                       Defaults to "profile".
            max_retained_requests (int): Maximum number of requests to retain in memory.
                                         Passed to the profiler_instance's configure method.
                                         Defaults to 1000.
        """
        super().__init__(app)
        self.enable_by_default = enable_by_default
        self.profile_query_param = profile_query_param
        # Configure the global profiler instance with the specified retention policy
        profiler_instance.configure(max_retained_requests=max_retained_requests)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        Dispatches the request through the middleware.
        If profiling is active, it wraps the request processing with pyinstrument.
        Collects request metrics and adds them to the global profiler instance.
        """
        # Get environment variable status (case-insensitive)
        is_enabled_by_env = os.getenv("FASTAPI_SIMPLE_PROFILER_ENABLED", "false").lower() == "true"
        # Get query parameter status (case-insensitive)
        query_param_value = request.query_params.get(self.profile_query_param, "").lower()
        is_enabled_by_query = query_param_value == "true"
        is_disabled_by_query = query_param_value == "false"

        # Determine if profiling should be active for this specific request
        # Logic:
        # 1. If enable_by_default is True:
        #    - Profiling is ON unless query param explicitly sets it to "false".
        # 2. If enable_by_default is False:
        #    - Profiling is OFF unless query param explicitly sets it to "true" OR
        #      the environment variable `FASTAPI_SIMPLE_PROFILER_ENABLED` is "true".
        profile_active = (self.enable_by_default and not is_disabled_by_query) or \
                         (not self.enable_by_default and (is_enabled_by_query or is_enabled_by_env))

        start_time = time.perf_counter() # Wall clock start time
        profiler = None
        response = None
        cpu_time_ms = 0.0 # Initialize CPU time

        # Only create and start profiler if it's active and pyinstrument is available
        if profile_active and Profiler:
            profiler = Profiler()
            profiler.start()

        try:
            # Process the request through the rest of the application
            response = await call_next(request)
        except Exception as e:
            # Ensure response is handled even if an exception occurs before a response is generated
            if response is None:
                response = Response("Internal Server Error", status_code=500)
            raise e # Re-raise the original exception after ensuring response handling
        finally:
            end_time = time.perf_counter() # Wall clock end time
            total_time_ms = (end_time - start_time) * 1000 # Convert to milliseconds

            if profiler:
                # Stop pyinstrument profiler if it was started
                profiler.stop()
                try:
                    # Parse pyinstrument's JSON output to get CPU time
                    profile_json = json.loads(profiler.output("json"))
                    # pyinstrument's cpu_time is in seconds, convert to milliseconds
                    cpu_time_ms = round(profile_json.get("cpu_time", 0) * 1000, 3)
                except Exception as e:
                    print(f"Error processing pyinstrument profile JSON: {e}")
                    # If an error occurs, CPUTimeMs will remain 0.0

            # Collect and store the aggregated profile data
            profile_data = {
                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "RequestPath": request.url.path,
                "HTTPMethod": request.method,
                "StatusCode": response.status_code,
                "TotalTimeMs": round(total_time_ms, 3),
                "CPUTimeMs": cpu_time_ms
            }
            profiler_instance.add_profile_data(profile_data)

            # Ensure a response is always returned by the middleware
            return response

