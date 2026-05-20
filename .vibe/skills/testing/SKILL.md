---
name: testing  
description: Automate testing for API calls telemetry systems, including unit tests, integration tests, and edge cases like token exhaustion or rate limits  
license: MIT  
compatibility: Python 3.11+  
user-invocable: true  
allowed-tools:  
  - read_file  
  - grep  
  - ask_user_question
---

# Testing Skill

## Overview

This skill automates testing for API calls telemetry systems, covering unit tests, integration tests, and edge cases (e.g., token exhaustion, API failures).

## Key Features

- **Unit Tests:** Mocks API calls to verify telemetry logging and cost calculations.
- **Integration Tests:** Runs the telemetry wrapper with a test API endpoint to validate end-to-end functionality.
- **Edge Cases:** Tests scenarios like invalid model names, failed API calls (e.g., 429 errors), and token exhaustion.
- **Reporting:** Generates a test report summarizing pass/fail status for each test case.

## Use Cases

- Validating telemetry logging for Mistral API calls.
- Testing cost calculations for different token counts and models.
- Ensuring the wrapper script handles API failures gracefully.

## Example Workflow

1. **Input:** A Python test file or a request to generate test cases.
2. **Output:** A test report with pass/fail status and logs for failures.
3. **User Interaction:** Asks for confirmation before running destructive tests (e.g., rate limit simulation).

## Tools Used

- `read_file`: To inspect test files.
- `grep`: To search for test patterns (e.g., `assert` statements).
- `ask_user_question`: To confirm user intent for critical test cases.
