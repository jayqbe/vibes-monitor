---
name: batch-processing  
description: Automate batch processing for telemetry data, such as aggregating logs, generating reports, or exporting data to CSV/JSON  
license: MIT  
compatibility: Python 3.11+  
user-invocable: true  
allowed-tools:  
  - read_file  
  - grep
---

# Batch Processing Skill

## Overview

This skill automates batch processing for telemetry data, including aggregating logs, generating cost summaries, and exporting data to CSV/JSON.

## Key Features

- **Log Aggregation:** Combines telemetry logs from multiple sources into a single dataset.
- **Report Generation:** Generates text-based summaries of token usage and costs (e.g., "Daily Cost Report").
- **Data Export:** Converts telemetry data into CSV/JSON for external analysis.
- **Performance Optimization:** Identifies and optimizes slow batch operations.

## Use Cases

- Generating weekly/monthly cost reports for Mistral API usage.
- Aggregating logs from multiple API endpoints.
- Exporting telemetry data for analysis in tools like Excel or Tableau.

## Example Workflow

1. **Input:** A request to process telemetry data (e.g., "Generate a cost report for May 2026").
2. **Output:** A CSV/JSON file or a text summary of the processed data.
3. **User Interaction:** None (fully automated).

## Tools Used

- `read_file`: To read telemetry data files.
- `grep`: To filter data by model, date, or user.
