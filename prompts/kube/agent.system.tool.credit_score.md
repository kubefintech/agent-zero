### credit_score:
Calculates user's affordability score by asking questions from a structured questionnaire.

IMPORTANT GUIDELINES:
- Always call this tool directly to process the user's answer and get the next question
- For the initial call, use no arguments to start the assessment
- For subsequent calls, include both the question_id and the user's answer
- For select-type questions, users can respond with either the number or the option text
- Do NOT use input_tool when asking credit score questions
- Do NOT try to calculate the score yourself - the tool handles all calculations

usage:
```json
{
  "thoughts": ["The user wants to calculate their credit score."],
  "tool_name": "credit_score",
  "tool_args": {}
}
```

When responding to a question:
```json
{
  "thoughts": ["The user answered '30' to the age question."],
  "tool_name": "credit_score",
  "tool_args": {
    "question_id": "age",  // Include the ID of the question being answered
    "answer": "30"         // Pass ONLY the user's direct answer
  }
}
```

Process Flow:
1. Call credit_score tool with no arguments to start the assessment
2. The tool presents the first question to the user (e.g., "What is your age?")
3. When user answers, call credit_score again with the question_id and their answer
4. The tool will provide the next question based on previous answers
5. Continue this loop until all questions are answered
6. The tool automatically calculates and displays the final score

Technical Details:
- Questions are fetched from: https://staging.platform.kube.money/api/v1/credit-score/questions
- Results are submitted to: https://staging.platform.kube.money/api/v1/credit-score/submit
- Questions adapt based on previous answers (e.g., different questions for "Businessman" vs "Employee")
- The question_id is included in each question the tool presents (usually matching the subject like "age", "income", etc.) 