---
name: documentation  
description: Automate the generation and maintenance of documentation for code base, including API schemas, data models, and deployment guides  
license: MIT  
compatibility: Python 3.11+  
user-invocable: true  
allowed-tools:  
  - read_file  
  - grep
---

# Documentation Skill

## Overview

This skill automates the generation and maintenance of code base documentation, including API schemas, data models, and deployment guides.

## Key Features

- **API Documentation:** Generates OpenAPI/Swagger-style docs.
- **Data Model Documentation:** Documents the data schema (e.g., SQLite tables, JSON structures).
- **Deployment Guides:** Creates step-by-step guides for setting up the system locally or in production.
- **Markdown/HTML Output:** Exports documentation in Markdown or HTML format for easy sharing.

## Use Cases

- Documenting the wrapper script’s API endpoints.
- Generating a README for the project.
- Updating API schemas when new models are added.

## Example Workflow

1. **Input:** A request to generate or update documentation (e.g., "Generate API docs for the system").
2. **Output:** A Markdown or HTML file with structured documentation.
3. **User Interaction:** None (fully automated).

## Tools Used

- `read_file`: To inspect existing documentation or code comments.
- `grep`: To extract API endpoints or data model details.
