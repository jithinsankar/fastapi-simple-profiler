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
