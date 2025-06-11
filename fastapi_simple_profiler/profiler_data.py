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

# Create a global instance of the profiler here, where its class is defined.
# This ensures it exists before any module tries to import it.
profiler_instance = FastAPIProfiler()
