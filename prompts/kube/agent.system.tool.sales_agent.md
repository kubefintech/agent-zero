### sales_agent:
Handles sales agent requests and status checks. Allows users to submit requests to become a sales agent and check their request status.

IMPORTANT GUIDELINES:
- Use this tool to submit new sales agent requests or check status of existing requests
- For new requests, the tool will ask for information in sequence:
  1. First asks for the bank name
  2. Then asks for the position
- For checking status, no additional parameters are needed
- The tool handles all API communication and error handling

Usage for starting a new request:
```json
{
  "thoughts": ["The user wants to submit a sales agent request. I'll start by asking for the bank name."],
  "tool_name": "sales_agent",
  "tool_args": {
    "action": "request"
  }
}
```

When user provides bank name:
```json
{
  "thoughts": ["User provided the bank name, now asking for position."],
  "tool_name": "sales_agent",
  "tool_args": {
    "action": "request",
    "bank_name": "Example Bank"
  }
}
```

When user provides position:
```json
{
  "thoughts": ["User provided both bank name and position, submitting the request."],
  "tool_name": "sales_agent",
  "tool_args": {
    "action": "request",
    "bank_name": "Example Bank",
    "position": "Senior Sales Agent"
  }
}
```

Usage for checking status:
```json
{
  "thoughts": ["The user wants to check their sales agent request status."],
  "tool_name": "sales_agent",
  "tool_args": {
    "action": "status"
  }
}
```

Process Flow:
1. For new requests:
   - Call sales_agent tool with action="request"
   - Tool asks for bank name
   - User provides bank name
   - Tool asks for position
   - User provides position
   - Tool submits complete request to API
   - Returns success/failure message

2. For status checks:
   - Call sales_agent tool with action="status"
   - Tool fetches current status from API
   - Returns current status information

Technical Details:
- Request submission endpoint: https://staging.platform.kube.money/api/v1/sales-agent/request
- Status check endpoint: https://staging.platform.kube.money/api/v1/sales-agent/profile 