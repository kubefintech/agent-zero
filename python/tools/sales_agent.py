import requests
import json
from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle


class SalesAgent(Tool):
    """Tool for handling sales agent requests and status checks."""

    def __init__(self, agent, name, args, message):
        super().__init__(agent, name, args, message)
        self.request_api_url = "https://staging.platform.kube.money/api/v1/sales-agent/request"
        self.profile_api_url = "https://staging.platform.kube.money/api/v1/sales-agent/profile"
        
        # Extract user_context from the agent's last_user_message if available
        self.user_context = None
        if hasattr(agent, 'last_user_message') and agent.last_user_message:
            message_content = agent.last_user_message.content
            if isinstance(message_content, dict) and 'user_context' in message_content:
                user_context_data = message_content['user_context']
                # Handle case where user_context might be a string
                if isinstance(user_context_data, str):
                    try:
                        self.user_context = json.loads(user_context_data)
                        PrintStyle.hint(f"Parsed user_context string into dictionary")
                    except json.JSONDecodeError:
                        PrintStyle.error(f"Failed to parse user_context as JSON")
                        self.user_context = {"raw_string": user_context_data}
                else:
                    # It's already a dictionary
                    self.user_context = user_context_data
                    
                if isinstance(self.user_context, dict):
                    PrintStyle.hint(f"Retrieved user_context with keys: {', '.join(self.user_context.keys())}")
        
    async def execute(self, action="", bank_name="", position="", **kwargs):
        """
        Handle sales agent requests and status checks.
        
        Args:
            action (str): Either "request" to submit a new request or "status" to check status
            bank_name (str): Name of the bank (required for request action)
            position (str): Position being applied for (required for request action)
        """
        # Check if user context and access token are available
        if not self.user_context:
            PrintStyle.error("No user context found. User needs to log in first.")
            error_msg = "You need to log in first before making a sales agent request. Please log in to your account and try again."
            await self.agent.hist_add_warning(error_msg)
            return Response(message="", break_loop=False)
            
        if not isinstance(self.user_context, dict) or not self.user_context.get('access_token'):
            PrintStyle.error("No access token found in user context. User needs to log in again.")
            error_msg = "Your session appears to be invalid. Please log in again to make a sales agent request."
            await self.agent.hist_add_warning(error_msg)
            return Response(message="", break_loop=False)

        try:
            # Set up headers with bearer token
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.user_context['access_token']}"
            }
            PrintStyle.hint("Using access_token from user_context for authorization")

            if action == "request":
                # If bank_name is not provided, ask for it
                if not bank_name:
                    return Response(
                        message="Please provide the name of the bank you work.",
                        break_loop=False
                    )
                
                # If position is not provided but bank_name is, ask for position
                if bank_name and not position:
                    return Response(
                        message="Please specify the position at " + bank_name + ".",
                        break_loop=False
                    )
                
                # If we have both bank_name and position, submit the request
                response = requests.post(
                    self.request_api_url,
                    json={
                        "bank_name": bank_name,
                        "position": position
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    return Response(
                        message="Your sales agent request has been submitted successfully.",
                        break_loop=True
                    )
                else:
                    return Response(
                        message=f"Failed to submit request. Status code: {response.status_code}",
                        break_loop=True
                    )
                    
            elif action == "status":
                # Check request status
                response = requests.get(self.profile_api_url, headers=headers)
                
                if response.status_code == 200:
                    status_data = response.json()
                    return Response(
                        message=f"Current status of your sales agent request: {status_data}",
                        break_loop=True
                    )
                else:
                    return Response(
                        message=f"Failed to fetch status. Status code: {response.status_code}",
                        break_loop=True
                    )
            else:
                # If no action is specified, start the request process
                return Response(
                    message="Please provide the name of the bank you want to be a sales agent for.",
                    break_loop=False
                )
                
        except Exception as e:
            PrintStyle.error(f"Error in sales agent tool: {str(e)}")
            return Response(
                message=f"An error occurred: {str(e)}",
                break_loop=True
            ) 