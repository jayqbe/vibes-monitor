---
name: code-review
description: Perform automated code reviews for token telemetry systems, ensuring adherence to logging, error handling, and data integrity standards  
license: MIT  
compatibility: Python 3.11+  
user-invocable: true  
allowed-tools:  
  - read_file  
  - grep  
  - ask_user_question
---

# Code Review Skill

## Overview

This skill automates code reviews, focusing on best practices for logging, error handling, and data integrity.

## Key Features

- **Logging Validation:** Ensures logs are correctly structured and free of sensitive data.
- **Error Handling:** Checks for proper error handling in API call wrappers and proxy scripts.
- **Data Integrity:** Validates that token usage and cost calculations are accurate and consistent.
- **Performance Optimization:** Identifies inefficient logging or batch processing methods.

## Use Cases

- Reviewing wrapper scripts for API call interception.
- Validating telemetry data storage (e.g., SQLite, JSON, CSV).
- Ensuring compliance with Mistral’s pricing models for cost calculations.

## Example Workflow

1. **Input:** A Python file containing the telemetry wrapper script.
2. **Output:** A list of issues (e.g., missing error handling, inefficient logging) and suggestions for fixes.
3. **User Interaction:** Asks for confirmation before applying automated fixes (if allowed).

## Tools Used

- `read_file`: To inspect telemetry-related code.
- `grep`: To search for patterns like `log_telemetry` or `calculate_cost`.
- `ask_user_question`: To confirm user intent for critical changes.
