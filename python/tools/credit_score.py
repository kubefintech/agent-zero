import requests
import json
import os
from typing import Dict, List, Any, Optional
import re
from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle


class CreditScore(Tool):
    """Tool for calculating a user's affordability score based on their responses to questions."""

    def __init__(self, agent, name, args, message):
        super().__init__(agent, name, args, message)
        self.questions = []
        self.responses = {}
        self.score = 0
        self.question_api_url = "https://staging.platform.kube.money/api/v1/credit-score/questions"
        self.submit_api_url = "https://staging.platform.kube.money/api/v1/credit-score/submit"
        self.state = {}
        
        # Log initialization for debugging
        PrintStyle.hint(f"Credit Score Tool initialized. API URL: {self.question_api_url}")
        
        # Check for existing state
        existing_state = agent.get_data("credit_score_state")
        if existing_state:
            active_count = len(existing_state.get("active_questions", []))
            response_count = len(existing_state.get("responses", {}))
            PrintStyle.hint(f"Found existing credit score state with {response_count} responses and {active_count} active questions")

    async def execute(self, **kwargs):
        """Execute the credit score tool based on the current state."""
        # Get conversation state
        conversation_state = self.agent.get_data("credit_score_state") or {}
        
        # First invocation or reset
        if not conversation_state or kwargs.get("reset", False):
            # Start the process and ask the first question
            intro_message = "I'll help you calculate your affordability score. I'll ask you a series of questions one by one."
            questions = await self.fetch_questions()
            
            if not questions:
                return Response(
                    message="I'm unable to fetch or load the credit score questions. Please ensure that the example/credit_score_questions.json file exists and is properly formatted.",
                    break_loop=False
                )
            
            # Initialize with the questions that have no dependencies
            initial_questions = [q for q in questions if not q.get("dependency")]
            
            conversation_state = {
                "current_question_index": 0,
                "all_questions": questions,  # Store all questions for reference
                "active_questions": initial_questions,  # Only questions currently in the queue
                "responses": {},
                "current_question_id": initial_questions[0]["id"] if initial_questions else None  # Track current question ID
            }
            
            # Save all questions for later use in submit_score
            self.questions = questions
            
            # Save state
            self.agent.set_data("credit_score_state", conversation_state)
            
            # Format first question
            first_question = initial_questions[0]
            question_text = self.format_question(first_question)
            
            return Response(
                message=f"{intro_message}\n\n{question_text}\n\nQuestion ID: {first_question['id']}",
                break_loop=False
            )
        
        # Handle user's response
        elif "current_question_index" in conversation_state:
            # Get the answer from tool_args
            question_id = self.args.get("question_id", "")
            user_answer = self.args.get("answer", "")
            
            # If question_id is provided, use it to directly answer that question
            if question_id:
                # Clean the answer
                user_answer = user_answer.strip() if isinstance(user_answer, str) else user_answer
                
                # Save the answer for this question
                conversation_state["responses"][question_id] = user_answer
                PrintStyle.hint(f"Recorded response '{user_answer}' for question '{question_id}'")
            else:
                # Fall back to old method if question_id not provided (for backward compatibility)
                current_index = conversation_state["current_question_index"]
                
                # Make sure we have active questions
                if not conversation_state["active_questions"]:
                    return Response(
                        message="There are no more questions to answer. Let's restart the credit score assessment.",
                        break_loop=False
                    )
                
                # Get the current question
                current_question = conversation_state["active_questions"][current_index]
                current_question_id = current_question["id"]
                
                # Get user's response from the message or text field
                if "text" in self.args:
                    user_answer = self.args.get("text", "").strip()
                else:
                    user_answer = self.message.strip()
                
                # For JSON or complex responses, try to extract just the text content
                if isinstance(user_answer, str) and user_answer.startswith("{") and user_answer.endswith("}"):
                    try:
                        # This might be a JSON object, let's extract just the plain text
                        json_data = json.loads(user_answer)
                        if "text" in json_data:
                            user_answer = json_data["text"].strip()
                    except:
                        # If parsing fails, keep the original response
                        pass
                
                # Save the user's response
                conversation_state["responses"][current_question_id] = user_answer
                PrintStyle.hint(f"Recorded response '{user_answer}' for question '{current_question_id}'")
            
            # Update active questions based on responses
            self.update_active_questions(conversation_state)
            
            # Advance to next question
            conversation_state["current_question_index"] += 1
            
            # Check if we've reached the end of the active questions
            if conversation_state["current_question_index"] >= len(conversation_state["active_questions"]):
                # Check again for any new dependent questions that might have been activated
                old_active_length = len(conversation_state["active_questions"])
                self.update_active_questions(conversation_state)
                
                # If new questions were added or there are still active questions, adjust the index and continue
                if len(conversation_state["active_questions"]) > 0:
                    # Make sure we don't go beyond the bounds of the active questions array
                    conversation_state["current_question_index"] = min(
                        old_active_length, 
                        len(conversation_state["active_questions"]) - 1
                    )
                    
                    # Ask the next question
                    next_question = conversation_state["active_questions"][conversation_state["current_question_index"]]
                    question_text = self.format_question(next_question)
                    
                    # Update current question ID
                    conversation_state["current_question_id"] = next_question["id"]
                    
                    # Save state
                    self.agent.set_data("credit_score_state", conversation_state)
                    
                    return Response(
                        message=f"Thank you. {question_text}\n\nQuestion ID: {next_question['id']}",
                        break_loop=False
                    )
                
                # Only proceed to calculate score if there are no more active questions
                if len(conversation_state["active_questions"]) == 0:
                    # Save the responses for score calculation and submission
                    self.responses = conversation_state["responses"]
                    score_result = await self.calculate_score()
                    self.score = score_result["score"]
                    
                    # Submit the score
                    submission_result = await self.submit_score()
                    
                    # Display what questions were answered (for debugging)
                    answered_questions = ', '.join(conversation_state["responses"].keys())
                    PrintStyle.hint(f"Answered questions: {answered_questions}")
                    
                    # Clear the state
                    self.agent.set_data("credit_score_state", None)
                    
                    # Return the final response with reasoning
                    return Response(
                        message=f"Thank you for answering all the questions. Based on your responses, your affordability score is {self.score} out of 100.\n\nReasoning: {score_result['reasoning']}\n\nThis score indicates your current financial standing and ability to afford credit. Higher scores indicate better affordability.",
                        break_loop=False
                    )
            else:
                # Ask the next question
                next_question = conversation_state["active_questions"][conversation_state["current_question_index"]]
                question_text = self.format_question(next_question)
                
                # Update current question ID
                conversation_state["current_question_id"] = next_question["id"]
                
                # Save state
                self.agent.set_data("credit_score_state", conversation_state)
                
                return Response(
                    message=f"Thank you. {question_text}\n\nQuestion ID: {next_question['id']}",
                    break_loop=False
                )
        
        # Fallback for unexpected state
        return Response(
            message="I'm having trouble with the credit score calculation. Let's try again. Please tell me when you're ready to start the credit score assessment.",
            break_loop=False
        )
    
    def update_active_questions(self, conversation_state):
        """Update active questions based on dependencies and responses."""
        all_questions = conversation_state["all_questions"]
        responses = conversation_state["responses"]
        
        # Clean and process all responses for easier dependency checking
        processed_responses = {}
        for question_id, response in responses.items():
            # Clean the response - ensure it's a simple string value
            clean_response = response
            if isinstance(response, str):
                clean_response = response.strip()
            
            # Find the question
            question = next((q for q in all_questions if q["id"] == question_id), None)
            if question:
                # For select-type questions, convert numeric responses to the actual option
                if question.get("type") == "select" and question.get("options") and isinstance(clean_response, str) and clean_response.isdigit():
                    option_index = int(clean_response) - 1
                    if 0 <= option_index < len(question["options"]):
                        processed_responses[question_id] = question["options"][option_index]
                    else:
                        processed_responses[question_id] = clean_response
                else:
                    processed_responses[question_id] = clean_response
            else:
                processed_responses[question_id] = clean_response
        
        # Store the processed responses for debugging
        PrintStyle.hint(f"Processed responses: {processed_responses}")
        
        # Find which questions should be active - start with a clean slate
        candidate_questions = []
        
        # First add questions with no dependencies that haven't been answered yet
        for question in all_questions:
            if not question.get("dependency") and question["id"] not in responses:
                candidate_questions.append(question)
        
        # Then check for dependent questions that should be active
        added_dependent = True
        # Keep iterating until no more dependent questions are added
        while added_dependent:
            added_dependent = False
            for question in all_questions:
                # Skip if already in candidate questions or already answered
                if question in candidate_questions or question["id"] in responses:
                    continue
                    
                dependency = question.get("dependency")
                if dependency:
                    question_id = dependency.get("question_id")
                    required_value = dependency.get("value")
                    
                    # Check if the dependency has been answered
                    if question_id in processed_responses:
                        user_response = processed_responses[question_id]
                        
                        # Case-insensitive comparison for string values
                        if isinstance(user_response, str) and isinstance(required_value, str):
                            # Handle both direct text match and numeric option selection
                            matches = user_response.lower() == required_value.lower()
                        else:
                            # Direct comparison for other types
                            matches = user_response == required_value
                        
                        # Add the question if dependency is satisfied
                        if matches:
                            candidate_questions.append(question)
                            added_dependent = True
                            PrintStyle.hint(f"Activated dependent question '{question['id']}' based on response '{user_response}' to '{question_id}'")
        
        # Create the new active questions list
        # Start with an empty list to rebuild from scratch
        new_active_questions = []
        
        # First, add any questions that were already in the active list to maintain order
        for question in conversation_state["active_questions"]:
            if question["id"] not in responses and question not in new_active_questions:
                new_active_questions.append(question)
        
        # Then add any new questions that were activated but aren't already in the list
        for question in candidate_questions:
            if question["id"] not in responses and question not in new_active_questions:
                new_active_questions.append(question)
        
        # Log the active questions for debugging
        active_ids = [q["id"] for q in new_active_questions]
        PrintStyle.hint(f"Active questions: {active_ids}")
        
        # Replace the active questions in the conversation state
        conversation_state["active_questions"] = new_active_questions

    def format_question(self, question: Dict[str, Any]) -> str:
        """Format a question with options if applicable."""
        question_text = question["text"]
        
        if question.get("options"):
            # Format options with numbers for selection
            options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(question["options"])])
            return f"{question_text}\n{options_text}"
        
        # Add additional instruction for number-type questions
        if question.get("type") == "number":
            return f"{question_text} (Please enter a number)"
        
        return question_text

    async def fetch_questions(self) -> List[Dict[str, Any]]:
        """Fetch questions from the API."""
        try:
            PrintStyle.hint(f"Fetching questions from {self.question_api_url}")
            response = requests.get(self.question_api_url, timeout=10)
            response.raise_for_status()
            
            # Parse the response
            response_data = response.json()
            
            # Extract questions from the data field
            if "data" in response_data and isinstance(response_data["data"], list):
                self.questions = response_data["data"]
                PrintStyle.hint(f"Successfully fetched {len(self.questions)} questions")
                return self.questions
            else:
                PrintStyle.error(f"Unexpected API response format: {response_data}")
                # Use questions from JSON file
                return self._get_default_questions()
                
        except requests.RequestException as e:
            PrintStyle.error(f"Error fetching questions from API: {e}")
            # Use questions from JSON file
            PrintStyle.hint("Attempting to use questions from JSON file")
            return self._get_default_questions()
    
    def _get_default_questions(self) -> List[Dict[str, Any]]:
        """Return default questions from a file or terminate if file cannot be loaded."""
        # Path to questions file
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                               "example", "credit_score_questions.json")
        
        try:
            # Try to load questions from file
            if os.path.exists(file_path):
                PrintStyle.hint(f"Loading questions from {file_path}")
                with open(file_path, 'r') as file:
                    data = json.load(file)
                    if "data" in data and isinstance(data["data"], list):
                        PrintStyle.hint(f"Successfully loaded {len(data['data'])} questions from file")
                        return data["data"]
                    else:
                        PrintStyle.error(f"Unexpected format in questions file: missing 'data' field or not a list")
            else:
                PrintStyle.error(f"Questions file not found at {file_path}")
        except Exception as e:
            PrintStyle.error(f"Error loading questions from file: {e}")
            
        # Return empty list instead of hardcoded questions
        return []
    
    async def calculate_score(self) -> Dict[str, Any]:
        """Calculate the affordability score using only the LLM, returning both score and reasoning."""
        # Create a detailed prompt with scoring guidelines and factors to consider
        system_prompt = """
        You are a financial expert specializing in credit scoring and affordability assessment.
        
        Your task is to analyze the user's responses and calculate an affordability score on a scale of 0-100.
        
        SCORING GUIDELINES:
        - 0-20: Very Poor Affordability - High financial risk, very limited ability to afford credit
        - 21-40: Poor Affordability - Significant financial constraints, limited ability to take on debt
        - 41-60: Moderate Affordability - Some financial stability, moderate ability to handle credit
        - 61-80: Good Affordability - Financially stable, good ability to manage debt obligations
        - 81-100: Excellent Affordability - Very financially secure, excellent ability to handle credit
        
        FACTORS TO CONSIDER:
        - Income Level: Higher income improves affordability
        - Debt-to-Income Ratio: Lower ratio improves affordability
        - Education Level: Higher education often correlates with better financial stability
        - Employment Status: Stable employment improves affordability
        - Business Metrics (if applicable): Profitable businesses with stable operations rate higher
        
        RESPONSE FORMAT:
        Provide your analysis as a JSON object with:
        1. A numeric score between 0-100
        2. A brief explanation of the reasoning
        
        Example:
        {
          "score": 75,
          "reasoning": "Good income level, moderate debt, stable employment"
        }
        """
        
        # Import json here to avoid linter error
        import json
        
        # Format user responses for the model with cleaned data
        # Extract the actual values, not the JSON objects
        cleaned_responses = {}
        for q_id, answer in self.responses.items():
            # Find the question to determine its type
            question = next((q for q in self.questions if q["id"] == q_id), None)
            
            # Process select-type responses to get the actual option text
            if question and question.get("type") == "select" and question.get("options") and isinstance(answer, str) and answer.isdigit():
                option_index = int(answer) - 1
                if 0 <= option_index < len(question["options"]):
                    cleaned_responses[q_id] = question["options"][option_index]
                else:
                    cleaned_responses[q_id] = answer
            else:
                cleaned_responses[q_id] = answer
        
        # Format the responses with question text for better context
        formatted_responses = []
        for q_id, answer in cleaned_responses.items():
            question = next((q for q in self.questions if q["id"] == q_id), None)
            if question:
                formatted_responses.append(f"Question: {question['text']}\nAnswer: {answer}")
            else:
                formatted_responses.append(f"{q_id}: {answer}")
        
        user_responses = "\n\n".join(formatted_responses)
        
        try:
            # Call the model to calculate the score
            PrintStyle.hint("Calculating score with LLM")
            score_result = await self.agent.call_utility_model(
                system=system_prompt,
                message=f"Please calculate an affordability score based on these responses:\n\n{user_responses}"
            )

            PrintStyle.hint(f"Score result: {score_result}")
            
            # Initialize result with default values
            result = {
                "score": 0,
                "reasoning": "Default moderate score due to incomplete information."
            }
            
            # Try to parse JSON first
            try:
                result_json = json.loads(score_result)
                if "score" in result_json and isinstance(result_json["score"], (int, float)):
                    score = int(result_json["score"])
                    PrintStyle.hint(f"Extracted score {score} from JSON response")
                    
                    # Ensure score is within 0-100 range
                    score = max(0, min(100, score))
                    result["score"] = score
                    
                    if "reasoning" in result_json:
                        reasoning = result_json["reasoning"]
                        PrintStyle.hint(f"Reasoning: {reasoning}")
                        result["reasoning"] = reasoning
                    
                    return result
            except json.JSONDecodeError:
                PrintStyle.hint("Could not parse response as JSON, trying regex")
            
            # Fall back to regex extraction
            score_match = re.search(r'(\d+)', score_result)
            if score_match:
                score = int(score_match.group(1))
                PrintStyle.hint(f"Extracted score {score} using regex")
                # Ensure score is within 0-100 range
                result["score"] = max(0, min(100, score))
                
                # Try to extract some reasoning text
                # Take everything after the score number as reasoning
                reasoning_text = score_result.split(str(score), 1)
                if len(reasoning_text) > 1:
                    result["reasoning"] = reasoning_text[1].strip().strip('.,:"\'')
                else:
                    result["reasoning"] = "Score extracted from model response."
                
                return result
            else:
                PrintStyle.error(f"Could not extract numeric score from LLM response: {score_result}")
                result["reasoning"] = "No score found in model response. Using default moderate score."
                return result
        except Exception as e:
            PrintStyle.error(f"Error calculating score with LLM: {e}")
            return {
                "score": 0,
                "reasoning": f"Error during score calculation: {str(e)}"
            }
    
    async def submit_score(self) -> Dict[str, Any]:
        """Submit the final score to the API."""
        # Format responses to be in the format {question_id: answer}
        formatted_responses = {}
        
        # Process responses to convert numeric select answers to actual text values
        # and ensure answers are clean, simple values
        for question_id, answer in self.responses.items():
            # Clean the answer - remove any JSON structure, quotes, or unwanted formatting
            clean_answer = answer
            
            # Strip quotes if present
            if isinstance(clean_answer, str):
                clean_answer = clean_answer.strip('"\'')
            
            # Find the corresponding question
            question = next((q for q in self.questions if q["id"] == question_id), None)
            
            if question and question.get("type") == "select" and question.get("options"):
                # For select-type questions, always convert numeric responses to text options
                if isinstance(clean_answer, str) and clean_answer.isdigit():
                    option_index = int(clean_answer) - 1
                    if 0 <= option_index < len(question["options"]):
                        PrintStyle.hint(f"Converting response for {question_id}: {clean_answer} -> {question['options'][option_index]}")
                        formatted_responses[question_id] = question["options"][option_index]
                    else:
                        formatted_responses[question_id] = clean_answer
                else:
                    # For non-numeric select responses, still ensure they match an option if possible
                    found_match = False
                    if isinstance(clean_answer, str):
                        for option in question["options"]:
                            if clean_answer.lower() == option.lower():
                                formatted_responses[question_id] = option
                                found_match = True
                                break
                    
                    if not found_match:
                        formatted_responses[question_id] = clean_answer
            else:
                formatted_responses[question_id] = clean_answer
        
        # Log the formatted responses for debugging
        PrintStyle.hint(f"Formatted responses for submission: {formatted_responses}")
        
        # Calculate score and get reasoning
        score_result = await self.calculate_score()
        self.score = score_result["score"]
        score_reasoning = score_result["reasoning"]
        
        payload = {
            "responses": formatted_responses,
            "score": self.score,
            "reasoning": score_reasoning
        }
        
        try:
            PrintStyle.hint(f"Submitting score to {self.submit_api_url}")
            PrintStyle.hint(f"Payload: {json.dumps(payload, indent=2)}")
            response = requests.post(
                self.submit_api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            try:
                response.raise_for_status()
                PrintStyle.hint("Successfully submitted score")
                return response.json()
            except requests.RequestException as e:
                PrintStyle.error(f"Error submitting score: {e}")
                return {"error": str(e)}
        except Exception as e:
            PrintStyle.error(f"Exception during score submission: {e}")
            return {"error": str(e)}
    
    def get_log_object(self):
        """Get the log object for the tool."""
        return self.agent.context.log.log(
            type="info", 
            heading=f"{self.agent.agent_name}: Credit Score Tool", 
            content="",
            kvps=self.args
        )
    
    async def after_execution(self, response, **kwargs):
        """Actions to take after execution."""
        await self.agent.hist_add_tool_result(self.name, response.message) 