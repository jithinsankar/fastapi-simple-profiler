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
    from pyinstrument import Profiler
except ImportError:
    print("Warning: pyinstrument not found. CPUTimeMs will not be available.")
    Profiler = None

from .profiler_data import profiler_instance

class ProfilerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to profile FastAPI requests and store performance metrics.
    """

    def __init__(self, app: ASGIApp,
                 enable_by_default: bool = False,
                 profile_query_param: str = "profile",
                 max_retained_requests: int = 1000):
        super().__init__(app)
        self.enable_by_default = enable_by_default
        self.profile_query_param = profile_query_param
        profiler_instance.configure(max_retained_requests=max_retained_requests)
        # Added a print to confirm middleware initialization and its default setting
        print(f"INFO: ProfilerMiddleware initialized. enable_by_default={self.enable_by_default}")

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        Dispatches the request through the middleware, conditionally profiling it.
        """
        is_enabled_by_env = os.getenv("FASTAPI_SIMPLE_PROFILER_ENABLED", "false").lower() == "true"
        query_param_value = request.query_params.get(self.profile_query_param, "").lower()
        is_enabled_by_query = query_param_value == "true"
        is_disabled_by_query = query_param_value == "false"

        # --- DEBUG PRINTS START ---
        print(f"\nDEBUG: Processing Request to {request.url.path}")
        print(f"DEBUG: Middleware setting: enable_by_default={self.enable_by_default}")
        print(f"DEBUG: Environment variable 'FASTAPI_SIMPLE_PROFILER_ENABLED' is '{os.getenv('FASTAPI_SIMPLE_PROFILER_ENABLED')}'. Interpreted as is_enabled_by_env={is_enabled_by_env}")
        print(f"DEBUG: Query parameter '{self.profile_query_param}' is '{query_param_value}'. Interpreted as is_enabled_by_query={is_enabled_by_query}, is_disabled_by_query={is_disabled_by_query}")
        # --- DEBUG PRINTS END ---

        # Determine if profiling should be active for this specific request
        profile_active = (self.enable_by_default and not is_disabled_by_query) or \
                         (not self.enable_by_default and (is_enabled_by_query or is_enabled_by_env))

        # --- DEBUG PRINTS START ---
        print(f"DEBUG: Final decision: profile_active={profile_active}")
        # --- DEBUG PRINTS END ---

        start_time = time.perf_counter()
        profiler = None
        response = None
        cpu_time_ms = 0.0

        if profile_active and Profiler:
            print(f"DEBUG: Pyinstrument profiler STARTING for request to {request.url.path}.")
            profiler = Profiler()
            profiler.start()

        try:
            response = await call_next(request)
        except Exception as e:
            if response is None:
                response = Response("Internal Server Error", status_code=500)
            raise e
        finally:
            end_time = time.perf_counter()
            total_time_ms = (end_time - start_time) * 1000

            if profiler: # Only stop profiler if it was started
                print(f"DEBUG: Pyinstrument profiler STOPPING for request to {request.url.path}.")
                profiler.stop()
                try:
                    profile_json = json.loads(profiler.output("json"))
                    cpu_time_ms = round(profile_json.get("cpu_time", 0) * 1000, 3)
                except Exception as e:
                    print(f"Error processing pyinstrument profile JSON for {request.url.path}: {e}")

            if profile_active: # Only add data to the profiler instance if profiling was active
                profile_data = {
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "RequestPath": request.url.path,
                    "HTTPMethod": request.method,
                    "StatusCode": response.status_code,
                    "TotalTimeMs": round(total_time_ms, 3),
                    "CPUTimeMs": cpu_time_ms
                }
                profiler_instance.add_profile_data(profile_data)
                print(f"DEBUG: Added profile data for {request.url.path} (status: {response.status_code}, total_time: {total_time_ms:.3f}ms).")
            else:
                print(f"DEBUG: Profiling NOT active for {request.url.path}. Data not added.")

            return response
