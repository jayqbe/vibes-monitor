# Functional Specification: Token Telemetry for Vibe CLI

## 1. Purpose and Scope

### 1.1 Objective

Develop a **standalone token telemetry system** that runs as a proxy wrapper around Vibe CLI to:

- Measure **model API traffic** (requests, tokens, latency, errors).
- Compute **cost** based on Mistral AI’s pricing model.
- Output **text-based summaries** with category breakdowns.

### 1.2 Scope

- **In-Scope**:
  - Real-time tracking of API calls made by Vibe CLI.
  - Token usage per request/response.
  - Cost calculation (input/output tokens, per model).
  - Basic reporting (CLI output, local storage).
- **Out-of-Scope**:
  - Long-term data storage (beyond local logs).
  - Advanced analytics/dashboarding.
  - Integration with external billing systems.

---

## 2. Functional Requirements

### 2.1 Core Functions


| Function             | Description                                                | Input                         | Output               | Notes                                                              |
| -------------------- | ---------------------------------------------------------- | ----------------------------- | -------------------- | ------------------------------------------------------------------ |
| **Track API Calls**  | Log every API call made by Vibe CLI.                       | API request/response payloads | Structured log entry | Include timestamp, endpoint, request/response tokens, status code. |
| **Measure Tokens**   | Count input/output tokens per API call.                    | API response                  | Token count          | Support for Mistral models.                                        |
| **Compute Cost**     | Calculate cost based on token usage and Mistral’s pricing. | Token counts, model name      | Cost in USD          | Dynamic mapping for input/output costs per model.                  |
| **Generate Reports** | Produce summaries of usage and cost.                       | Telemetry data                | CLI output           | Text-based summary with category breakdowns.                       |


### 2.2 Telemetry Metadata


| Metric              | Description                        | Example                                      |
| ------------------- | ---------------------------------- | -------------------------------------------- |
| **Model**           | Name of the model used.            | `mistral-tiny`                               |
| **API Endpoint**    | URL/path of the API call.          | `https://api.mistral.ai/v1/chat/completions` |
| **Origin**          | Who initiated the call?            | `user`, `agent`, `sub-agent`                 |
| **Request Tokens**  | Number of tokens in the request.   | `256`                                        |
| **Response Tokens** | Number of tokens in the response.  | `512`                                        |
| **Total Tokens**    | Request + Response tokens.         | `768`                                        |
| **Processing Time** | Time taken to process the request. | `125ms`                                      |
| **Status Code**     | HTTP status code of the response.  | `200`, `429`                                 |
| **Cost**            | Calculated cost for the call.      | `$0.000576`                                  |


### 2.3 Cost Model

- **Provider**: Mistral AI.
- **Pricing**:
  - **Input tokens**: (example) $0.25 per 1M tokens.
  - **Output tokens**: (example) $0.75 per 1M tokens.
- **Dynamic Mapping**:
  - `mistral-tiny`, `mistral-medium`, `mistral-large` all use the same pricing.
  - Configurable for custom models.

### 2.4 Reporting

- **Format**: Text-based summary with category breakdowns (e.g., by model, origin, or time period).
- **Example**:
  ```
  ## Token Telemetry Summary (2026-05-19)
  - **Total API Calls**: 42
  - **Total Tokens**: 32,450 (Input: 12,000, Output: 20,450)
  - **Total Cost**: $0.0243

  ### Breakdown by Model
  - mistral-medium: 20 calls, 15,000 tokens (Input: 5,000, Output: 10,000), $0.01125
  - mistral-large: 22 calls, 17,450 tokens (Input: 7,000, Output: 10,450), $0.01308

  ### Breakdown by Origin
  - user: 30 calls, 25,000 tokens (Input: 10,000, Output: 15,000), $0.01875
  - agent: 12 calls, 7,450 tokens (Input: 2,000, Output: 5,450), $0.00562
  ```

---

## 3. Non-Functional Requirements


| Requirement       | Description                                        |
| ----------------- | -------------------------------------------------- |
| **Security**      | No sensitive data logged (only metadata).          |
| **Portability**   | Works in a local Vibe CLI environment.             |
| **Extensibility** | Support for future providers/models.               |
| **Performance**   | Minimal overhead; non-blocking on failure.         |


---

## 4. Assumptions and Constraints

- **Assumption**: Vibe CLI uses Mistral’s API for model calls.
- **Constraint**: No modifications to Vibe CLI or HTTP client required.
