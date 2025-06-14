# **FastAPI Simple Profiler**

A dead simple profiler for FastAPI applications, designed to provide per-request performance metrics and export them to a CSV format easily importable into Google Sheets or other spreadsheet software.
![Image](https://github.com/user-attachments/assets/2bdc4c99-6a6d-44c9-b573-0ec9836896ad)

## **Features**

* **Middleware-based**: Easily integrate into your FastAPI application with a single middleware.  
* **Per-request Metrics**: Capture total request wall clock time (TotalTimeMs) and CPU time (CPUTimeMs) for each API call.  
* **Conditional Activation**: Enable profiling via a URL query parameter (?profile=true) or by setting the FASTAPI\_SIMPLE\_PROFILER\_ENABLED=true environment variable to control overhead.  
* **In-Memory Storage**: Temporarily stores recent profiling data in memory, with a configurable retention policy.  
* **CSV Export Endpoint**: Access a dedicated endpoint (/profiler/metrics.csv) to download collected metrics as a CSV file.  
* **Google Sheets Ready**: CSV format is optimized for direct import into spreadsheet applications.  
* **Lightweight**: Designed for minimal overhead, especially when profiling is not active.

## **Installation**

You can install the package using pip:

```bash
pip install fastapi-simple-profiler
```

This package depends on pyinstrument for detailed CPU time measurement, pandas for CSV generation, and fastapi/starlette for the web framework integration. These dependencies will be automatically installed.

## **Usage**

### **1\. Integrate the Middleware**

Add ProfilerMiddleware to your FastAPI application instance.

```python
from fastapi import FastAPI  
from fastapi.responses import StreamingResponse  
from fastapi_simple_profiler import ProfilerMiddleware, profiler_instance  
import uvicorn  
import time  
import asyncio

app = FastAPI()

# Add the profiler middleware to your FastAPI application.  
# You can configure its behavior:  
# - `enable_by_default`: Set to `True` to profile all requests by default.  
#                        (Default: `False`)  
# - `profile_query_param`: The query parameter name to toggle profiling.  
#                          (Default: "profile")  
# - `max_retained_requests`: The maximum number of requests to keep in memory.  
#                            Older requests are automatically pruned.  
#                            (Default: 1000)  

app.add_middleware(  
    ProfilerMiddleware,  
    enable_by_default=True, # Set to True to enable profiling for all requests by default  
    profile_query_param="profile", # e.g., use `?profile=true` in URL  
    max_retained_requests=500 # Keep data for the last 500 requests in memory  
)

@app.get("/")  
async def read_root():  
    """A simple root endpoint."""  
    await asyncio.sleep(0.01) # Simulate some async I/O work  
    return {"message": "Hello World"}

@app.get("/items/{item_id}")  
async def read_item(item_id: int):  
    """An endpoint that simulates some compute-bound or I/O work."""  
    if item_id % 2 == 0:  
        await asyncio.sleep(0.05) # Simulate longer async work for even IDs  
    else:  
        # Simulate some blocking CPU work (e.g., heavy computation)  
        # This will be reflected in CPUTimeMs by pyinstrument  
        _ = [i*i for i in range(100000)] # CPU-bound loop  
        time.sleep(0.005) # Small blocking sleep to show in TotalTimeMs too  
    return {"item_id": item_id, "message": "Item processed"}

@app.get("/slow-endpoint")  
async def slow_endpoint():  
    """An intentionally slow endpoint."""  
    await asyncio.sleep(0.5) # Simulate significant async delay  
    return {"message": "This was a slow request!"}

@app.get("/profiler/metrics.csv")  
async def get_profiler_metrics_csv():  
    """  
    Dedicated endpoint to download the collected profiling metrics as a CSV file.  
    This uses FastAPI's StreamingResponse for efficient file download.  
    """  
    csv_buffer = profiler_instance.export_to_csv()  
    return StreamingResponse(  
        csv_buffer,  
        media_type="text/csv",  
        headers={"Content-Disposition": "attachment; filename=fastapi_profile_metrics.csv"}  
    )

@app.get("/profiler/clear")  
async def clear_profiler_data():  
    """  
    Endpoint to clear all collected profiling data from memory.  
    Useful for resetting the collected metrics.  
    """  
    profiler_instance.clear_data()  
    return {"message": "Profiler data cleared."}




if __name__ == "__main__":  
    # To run this example:  
    # 1. Save the above code as `main.py` in your project root.  
    # 2. Ensure `fastapi-simple-profiler` is installed (`pip install fastapi-simple-profiler`).  
    # 3. Run from your terminal: `uvicorn main:app --reload --port 8000`  
    #  
    # To enable profiling for ALL requests via environment variable:  
    # FASTAPI_SIMPLE_PROFILER_ENABLED=true uvicorn main:app --reload --port 8000  
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
if you want to preview the results at an endpoint like below add the following code

![Image](https://github.com/user-attachments/assets/2bdc4c99-6a6d-44c9-b573-0ec9836896ad)

```python

import pandas as pd
from fastapi.responses import HTMLResponse


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
```

### **2\. Run your FastAPI Application**

Run your FastAPI application using Uvicorn (recommended ASGI server for FastAPI):
```bash
uvicorn your_app_module:app --reload --port 8000
```
(Replace your\_app\_module with the name of your Python file, e.g., main).

### **3\. Generate Profiled Requests**

Make some requests to your FastAPI application.

* **Profile specific requests**: If enable\_by\_default is False (the default), append ?profile=true to the URL for requests you want to profile:  
  * http://localhost:8000/?profile=true  
  * http://localhost:8000/items/123?profile=true  
  * http://localhost:8000/slow-endpoint?profile=true  
* **Profile all requests**: 
 
  * Set enable\_by\_default=True when adding ProfilerMiddleware to your app.  
  * OR set the environment variable before running your app: FASTAPI\_SIMPLE\_PROFILER\_ENABLED=true uvicorn your\_app\_module:app \--reload \--port 8000

### **4\. Export Metrics to CSV**

Once you have made some requests (with profiling active), open your web browser and navigate to:

http://localhost:8000/profiler/metrics.csv

This will trigger a direct download of a CSV file (e.g., fastapi\_profile\_metrics.csv) containing your collected profiling data.

### **5\. Import into Google Sheets**

1. Go to [Google Sheets](https://docs.google.com/spreadsheets/u/0/create) (or your preferred spreadsheet software).  
2. Go to File \> Import \> Upload.  
3. Choose the downloaded fastapi\_profile\_metrics.csv file.  
4. Ensure "Detect automatically" is selected for the separator type (usually the default).  
5. Click "Import data".

Your profiling metrics will now be available in a clean, tabular format for analysis\!

## **Columns in the CSV Export**

The exported CSV file will include the following columns:

* Timestamp: The exact time the request completed (YYYY-MM-DD HH:MM:SS).  
* RequestPath: The URL path of the API endpoint (e.g., /items/{item\_id}).  
* HTTPMethod: The HTTP method used for the request (e.g., GET, POST).  
* StatusCode: The HTTP response status code (e.g., 200, 404, 500).  
* TotalTimeMs: The total "wall clock" time for the request-response cycle in milliseconds.  
* CPUTimeMs: The actual CPU time spent processing the request in milliseconds, as reported by pyinstrument. This excludes time spent waiting on I/O.

## **Contributing**

Contributions are welcome\! If you find bugs, have feature requests, or want to improve the code, please feel free to open issues or submit pull requests on the [GitHub repository](https://github.com/jithinsankar/fastapi-simple-profiler).

## **License**

This project is licensed under the MIT License \- see the [LICENSE](https://github.com/jithinsankar/fastapi-simple-profiler/blob/main/LICENSE) file for details.

