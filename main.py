# main.py
# This file serves as a mock FastAPI application to demonstrate and test
# the fastapi-simple-profiler middleware.

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
import time
import asyncio
import io # Import io for handling CSV buffer
import pandas as pd # Import pandas to help with HTML table generation

# Import the ProfilerMiddleware and the global profiler_instance from your package
from fastapi_simple_profiler import ProfilerMiddleware, profiler_instance

# Initialize the FastAPI application
app = FastAPI(
    title="FastAPI Simple Profiler Demo",
    description="A demonstration of the fastapi-simple-profiler middleware.",
    version="0.1.0"
)

# Add the profiler middleware to your FastAPI application.
# It's crucial to set enable_by_default=False if you want manual control
# via query parameters or environment variables.
app.add_middleware(
    ProfilerMiddleware,
    enable_by_default=False, # Set to False for manual control
    profile_query_param="profile",
    max_retained_requests=500
)

# Use FastAPI's startup event to clear profiler data
# This ensures it runs within the application's context after startup.
@app.on_event("startup")
async def startup_event():
    """
    Clears profiler data when the FastAPI application starts up.
    This ensures a clean slate for profiling on each run/reload.
    """
    print("INFO: Clearing profiler data on application startup.")
    profiler_instance.clear_data()


@app.get("/", summary="Root Endpoint", response_model=dict)
async def read_root():
    """
    A simple root endpoint that simulates a small asynchronous I/O delay.
    """
    await asyncio.sleep(0.01) # Simulate some async I/O work (e.g., database call)
    return {"message": "Hello World"}

@app.get("/items/{item_id}", summary="Item Endpoint", response_model=dict)
async def read_item(item_id: int):
    """
    An endpoint that simulates different types of work based on item_id:
    - Even IDs: Simulate longer asynchronous I/O.
    - Odd IDs: Simulate CPU-bound work (blocking operation).
    """
    if item_id % 2 == 0:
        await asyncio.sleep(0.05) # Simulate longer async work for even IDs
    else:
        # Significantly increase CPU-bound work here
        # This loop will consume noticeable CPU time
        result = 0
        for _ in range(5_000_000): # Increased from 1,000,000 to 5,000,000 for more CPU time
            result += sum(x * x for x in range(20)) # More complex calculation per iteration
        # No time.sleep here, so it's purely CPU-bound within Python
    return {"item_id": item_id, "message": "Item processed"}

@app.get("/cpu-intensive", summary="Dedicated CPU-Intensive Endpoint", response_model=dict)
async def cpu_intensive_endpoint():
    """
    A dedicated endpoint to demonstrate high CPUTimeMs by performing
    a significant amount of synchronous, CPU-bound calculation.
    """
    print("INFO: /cpu-intensive endpoint activated - performing heavy computation.")
    result = 0
    # Perform a very heavy synchronous CPU-bound task
    for _ in range(20_000_000): # Even larger loop: Increased from 5,000,000 to 20,000,000
        result += sum(x * x for x in range(50)) # More complex calculation
    print("INFO: /cpu-intensive endpoint computation finished.")
    return {"message": "CPU intensive task completed", "result_dummy": result % 100}


@app.get("/slow-endpoint", summary="Slow Endpoint", response_model=dict)
async def slow_endpoint():
    """
    An intentionally slow endpoint to clearly demonstrate profiling of long requests.
    """
    await asyncio.sleep(0.5) # Simulate significant async delay
    return {"message": "This was a slow request!"}

@app.get("/profiler/dashboard", summary="Profiler Dashboard", response_class=HTMLResponse)
async def get_profiler_dashboard():
    """
    Dedicated endpoint to display the collected profiling metrics as an HTML table in the browser.
    """
    profile_data = profiler_instance.get_profile_data()

    if not profile_data:
        # If no data, display a message
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>FastAPI Profiler Dashboard</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; color: #374151; }
                .container { max-width: 90%; margin: 2rem auto; padding: 1.5rem; background-color: #ffffff; border-radius: 0.75rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
                h1 { color: #1f2937; }
                .clear-button { background-color: #dc2626; color: white; padding: 0.5rem 1rem; border-radius: 0.5rem; text-decoration: none; display: inline-block; margin-top: 1rem; }
                .clear-button:hover { background-color: #ef4444; }
                .export-csv-button { background-color: #10b981; color: white; padding: 0.5rem 1rem; border-radius: 0.5rem; text-decoration: none; display: inline-block; margin-top: 1rem; margin-left: 0.5rem; }
                .export-csv-button:hover { background-color: #059669; }
                .message { text-align: center; font-size: 1.125rem; color: #6b7280; }
            </style>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        </head>
        <body>
            <div class="container">
                <h1 class="text-3xl font-bold mb-4">FastAPI Profiler Dashboard</h1>
                <p class="message">No profiling data collected yet. Make some requests with `?profile=true` or set `FASTAPI_SIMPLE_PROFILER_ENABLED=true`.</p>
                <div class="flex justify-start space-x-2">
                    <a href="/profiler/clear" class="clear-button">Clear Data</a>
                    <a href="/profiler/metrics.csv" class="export-csv-button">Export to CSV</a>
                </div>
            </div>
        </body>
        </html>
        """
    else:
        # Create a DataFrame from the profile data
        df = pd.DataFrame(profile_data)

        # Define the desired column order for display
        desired_columns = [
            "Timestamp", "RequestPath", "HTTPMethod", "StatusCode",
            "TotalTimeMs", "CPUTimeMs"
        ]
        # Ensure all desired columns are present, filling missing with NaN if necessary
        for col in desired_columns:
            if col not in df.columns:
                df[col] = pd.NA

        # Reorder columns to the desired sequence
        df = df[desired_columns]

        # Convert DataFrame to an HTML table string
        html_table = df.to_html(index=False, classes="min-w-full divide-y divide-gray-200 shadow-sm sm:rounded-lg")

        # Basic HTML structure with Tailwind CSS for modern look
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>FastAPI Profiler Dashboard</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                /* Custom styles for the table */
                body {{ font-family: 'Inter', sans-serif; background-color: #f3f4f6; color: #374151; }}
                .container {{ max-width: 90%; margin: 2rem auto; padding: 1.5rem; background-color: #ffffff; border-radius: 0.75rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
                h1 {{ color: #1f2937; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
                th, td {{ padding: 0.75rem; border: 1px solid #e5e7eb; text-align: left; }}
                th {{ background-color: #f9fafb; font-weight: 600; color: #4b5563; }}
                tr:nth-child(even) {{ background-color: #f3f4f6; }}
                tr:hover {{ background-color: #e0f2fe; }} /* Light blue hover */
                .clear-button {{ background-color: #dc2626; color: white; padding: 0.5rem 1rem; border-radius: 0.5rem; text-decoration: none; display: inline-block; margin-top: 1rem; }}
                .clear-button:hover {{ background-color: #ef4444; }}
                .export-csv-button {{ background-color: #10b981; color: white; padding: 0.5rem 1rem; border-radius: 0.5rem; text-decoration: none; display: inline-block; margin-top: 1rem; margin-left: 0.5rem; }}
                .export-csv-button:hover {{ background-color: #059669; }}
            </style>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        </head>
        <body>
            <div class="container">
                <h1 class="text-3xl font-bold mb-4">FastAPI Profiler Dashboard</h1>
                {html_table}
                <div class="flex justify-start space-x-2">
                    <a href="/profiler/clear" class="clear-button">Clear Data</a>
                    <a href="/profiler/metrics.csv" class="export-csv-button">Export to CSV</a>
                </div>
            </div>
        </body>
        </html>
        """

    return HTMLResponse(content=html_content, status_code=200)

@app.get("/profiler/metrics.csv", summary="Download Profiler Metrics CSV", response_class=StreamingResponse)
async def get_profiler_metrics_csv():
    """
    Dedicated endpoint to download the collected profiling metrics as a CSV file.
    This still exists for users who prefer direct download.
    """
    csv_buffer = profiler_instance.export_to_csv()
    return StreamingResponse(
        csv_buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fastapi_profile_metrics.csv"}
    )

@app.get("/profiler/clear", summary="Clear Profiler Data", response_model=dict)
async def clear_profiler_data():
    """
    Endpoint to clear all collected profiling data from memory.
    Useful for resetting the collected metrics.
    """
    profiler_instance.clear_data()
    return {"message": "Profiler data cleared."}

# Entry point for running the application using Uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
