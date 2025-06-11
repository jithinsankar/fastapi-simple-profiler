from setuptools import setup, find_packages
import os

# Get the directory where setup.py is located
current_directory = os.path.dirname(os.path.abspath(__file__))

# Read the contents of the README.md file
readme_path = os.path.join(current_directory, "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = "A dead simple FastAPI profiler with CSV export for Google Sheets."

setup(
    name="fastapi-simple-profiler",
    version="0.1.0", # Initial version
    author="Jithin Sankar", 
    description="A dead simple FastAPI profiler with CSV export for Google Sheets.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jithinsankar/fastapi-simple-profiler", # Replace with your project's GitHub URL
    packages=find_packages(), # Automatically finds all packages in the directory
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License", # Standard open-source license
        "Operating System :: OS Independent",
        "Framework :: FastAPI",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
        "Intended Audience :: Developers",
        "Development Status :: 3 - Alpha", # Indicate development status
    ],
    python_requires='>=3.7', # Minimum Python version requirement
    install_requires=[
        "fastapi>=0.68.0", # Dependency for FastAPI applications
        "starlette>=0.14.2", # FastAPI is built on Starlette
        "pyinstrument>=4.0.0", # Essential for detailed CPU time profiling
        "pandas>=1.0.0", # Used for efficient CSV generation
    ],
    keywords="fastapi profiler performance metrics csv google-sheets monitoring profiling",
    project_urls={
        "Bug Tracker": "https://github.com/jithinsankar/fastapi-simple-profiler/issues", # Replace with your issues URL
        "Source Code": "https://github.com/jithinsankar/fastapi-simple-profiler", # Replace with your source code URL
    },
)

