### sales_agent:
Handles sales agent requests and status checks. Allows users to submit requests to become a sales agent and check their request status. triggers when the user wants to submit a sales agent request or check their request status.

IMPORTANT GUIDELINES:
- Use this tool to submit new sales agent requests or check status of existing requests
- For submitting requests, both bank_name and position are required
- For checking status, no additional parameters are needed
- The tool handles all API communication and error handling

Usage for submitting a request:
```json
{
  "thoughts": ["The user wants to submit a sales agent request."],
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
   - Provide bank_name and position
   - Tool submits request to API
   - Returns success/failure message

2. For status checks:
   - Call sales_agent tool with action="status"
   - Tool fetches current status from API
   - Returns current status information

Technical Details:
- Request submission endpoint: https://staging.platform.kube.money/api/v1/sales-agent/request
- Status check endpoint: https://staging.platform.kube.money/api/v1/sales-agent/profile 