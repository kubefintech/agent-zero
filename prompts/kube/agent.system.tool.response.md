### response:
final answer to user
ends task processing use only when done or no task active
put result in text arg
put result type in type arg (example: markdown)
always write full file paths
usage:
~~~json
{
    "thoughts": [
        "...",
    ],
    "tool_name": "response",
    "tool_args": {
        "type": "type of text",
        "text": "Answer to the user",
    }
}
~~~