# **FastAPI Simple Profiler**

A dead simple profiler for FastAPI applications, designed to provide per-request performance metrics and export them to a CSV format easily importable into Google Sheets or other spreadsheet software.

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

pip install fastapi-simple-profiler

This package depends on pyinstrument for detailed CPU time measurement, pandas for CSV generation, and fastapi/starlette for the web framework integration. These dependencies will be automatically installed.

## **Usage**

### **1\. Integrate the Middleware**

Add ProfilerMiddleware to your FastAPI application instance.

from fastapi import FastAPI  
from fastapi.responses import StreamingResponse  
from fastapi\_simple\_profiler import ProfilerMiddleware, profiler\_instance  
import uvicorn  
import time  
import asyncio

app \= FastAPI()

\# Add the profiler middleware to your FastAPI application.  
\# You can configure its behavior:  
\# \- \`enable\_by\_default\`: Set to \`True\` to profile all requests by default.  
\#                        (Default: \`False\`)  
\# \- \`profile\_query\_param\`: The query parameter name to toggle profiling.  
\#                          (Default: "profile")  
\# \- \`max\_retained\_requests\`: The maximum number of requests to keep in memory.  
\#                            Older requests are automatically pruned.  
\#                            (Default: 1000\)  
app.add\_middleware(  
    ProfilerMiddleware,  
    enable\_by\_default=False, \# Set to True to enable profiling for all requests by default  
    profile\_query\_param="profile", \# e.g., use \`?profile=true\` in URL  
    max\_retained\_requests=500 \# Keep data for the last 500 requests in memory  
)

@app.get("/")  
async def read\_root():  
    """A simple root endpoint."""  
    await asyncio.sleep(0.01) \# Simulate some async I/O work  
    return {"message": "Hello World"}

@app.get("/items/{item\_id}")  
async def read\_item(item\_id: int):  
    """An endpoint that simulates some compute-bound or I/O work."""  
    if item\_id % 2 \== 0:  
        await asyncio.sleep(0.05) \# Simulate longer async work for even IDs  
    else:  
        \# Simulate some blocking CPU work (e.g., heavy computation)  
        \# This will be reflected in CPUTimeMs by pyinstrument  
        \_ \= \[i\*i for i in range(100000)\] \# CPU-bound loop  
        time.sleep(0.005) \# Small blocking sleep to show in TotalTimeMs too  
    return {"item\_id": item\_id, "message": "Item processed"}

@app.get("/slow-endpoint")  
async def slow\_endpoint():  
    """An intentionally slow endpoint."""  
    await asyncio.sleep(0.5) \# Simulate significant async delay  
    return {"message": "This was a slow request\!"}

@app.get("/profiler/metrics.csv")  
async def get\_profiler\_metrics\_csv():  
    """  
    Dedicated endpoint to download the collected profiling metrics as a CSV file.  
    This uses FastAPI's StreamingResponse for efficient file download.  
    """  
    csv\_buffer \= profiler\_instance.export\_to\_csv()  
    return StreamingResponse(  
        csv\_buffer,  
        media\_type="text/csv",  
        headers={"Content-Disposition": "attachment; filename=fastapi\_profile\_metrics.csv"}  
    )

@app.get("/profiler/clear")  
async def clear\_profiler\_data():  
    """  
    Endpoint to clear all collected profiling data from memory.  
    Useful for resetting the collected metrics.  
    """  
    profiler\_instance.clear\_data()  
    return {"message": "Profiler data cleared."}

if \_\_name\_\_ \== "\_\_main\_\_":  
    \# To run this example:  
    \# 1\. Save the above code as \`main.py\` in your project root.  
    \# 2\. Ensure \`fastapi-simple-profiler\` is installed (\`pip install fastapi-simple-profiler\`).  
    \# 3\. Run from your terminal: \`uvicorn main:app \--reload \--port 8000\`  
    \#  
    \# To enable profiling for ALL requests via environment variable:  
    \# FASTAPI\_SIMPLE\_PROFILER\_ENABLED=true uvicorn main:app \--reload \--port 8000  
    uvicorn.run(app, host="0.0.0.0", port=8000)

### **2\. Run your FastAPI Application**

Run your FastAPI application using Uvicorn (recommended ASGI server for FastAPI):

uvicorn your\_app\_module:app \--reload \--port 8000

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

Contributions are welcome\! If you find bugs, have feature requests, or want to improve the code, please feel free to open issues or submit pull requests on the [GitHub repository](https://github.com/your-org/fastapi-simple-profiler).

## **License**

This project is licensed under the MIT License \- see the [LICENSE](http://docs.google.com/LICENSE) file for details.

