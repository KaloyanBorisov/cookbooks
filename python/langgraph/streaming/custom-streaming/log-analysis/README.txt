# Custom Streaming Log Analysis

This directory contains a streaming log analyzer that performs contextual error analysis on log files. The analyzer processes log data in chunks, scans for errors or warnings, and, if issues are detected, expands the analysis window to include surrounding context for deeper investigation.

## Features
- Processes log files in streaming fashion, chunk by chunk
- Scans each chunk for errors, warnings, or critical issues
- Automatically expands the context window for deeper analysis when issues are detected
- Provides detailed error analysis, root cause assessment, and recommended actions
- Outputs progress and analysis results to the console

## Usage

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the analyzer on a log file:
   ```bash
   python custom_streaming_log_analysis.py <log_file_path>
   ```
   Replace `<log_file_path>` with the path to your log file (e.g., `advanced_log.log`).

## Files
- `custom_streaming_log_analysis.py`: Main script for streaming log analysis
- `advanced_log.log`: Example log file for testing

## Requirements
See `requirements.txt` for the list of required Python packages.
