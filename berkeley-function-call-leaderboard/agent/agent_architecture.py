from utils import send_and_print,validate_and_print,add_agents_to_mediator,leggi_file_markdown,create_agent
from agent.agent_framework import Mediator
import os
BASE_PATH = "/home/ago/giammy/TESI-MAGISTRALE/thesis/berkeley-function-call-leaderboard"

def print_final_response(response):
    """Prints the final response in red and surrounded by two lines."""
    colored_text = f"\033[31mFINAL RESPONSE: {response}\033[0m"  # Red color
    print("=" * 50)  # Top line
    print(colored_text)
    print("=" * 50)  # Bottom line

def agent_architecture(model_name,temperature,url_endpoint, test_entry,bfcl=False, n_tests=2, MAX_TURNS=2, VALIDATION_CONDITION='Valid: The function call respects the parameter types and requirements.'):
    """
    Simulates the agent architecture workflow and returns the final output (res_recipient).
    
    Parameters:
        mediator: Mediator object for communication between agents.
        tester: Tester agent object.
        caller: Caller agent object.
        caller_feedback: Caller feedback agent object.
        validator: Validator agent object.
        validator_feedback: Validator feedback agent object.
        test_entry: Dictionary containing test information (e.g., function to validate).
        user_question: The initial user question.
        previous_tests: List to store results from previous tests.
        MAX_TURNS: Maximum number of iterations for validator feedback.
        VALIDATION_CONDITION: Condition to determine when validation ends.
    
    Returns:
        res_recipient: Final response after iterative validation.
    """
    if bfcl:
        user_question = test_entry["question"]
        functions = test_entry["functions"]
    else:
        user_question = test_entry["question"][0][0]['content']
        functions = test_entry["function"]
    # Costruisci percorsi assoluti
    system_prompt_tester = leggi_file_markdown(os.path.join(BASE_PATH, f'system_prompt/tester_qwen/javascript.md'))
    system_prompt_caller = leggi_file_markdown(os.path.join(BASE_PATH, 'system_prompt/caller.md'), functions)
    system_prompt_caller_feedback = leggi_file_markdown(os.path.join(BASE_PATH, 'system_prompt/caller_feedback.md'), functions)
    system_prompt_validator = leggi_file_markdown(os.path.join(BASE_PATH, 'system_prompt/validator.md'))
    system_prompt_validator_feedback = leggi_file_markdown(os.path.join(BASE_PATH, 'system_prompt/validator_feedback.md'), functions)


    mediator = Mediator()
    # Create Agents
    tester = create_agent("assistant", system_prompt_tester, model_name,temperature=1,huggingface_endpoint_url=url_endpoint)
    caller = create_agent("assistant", system_prompt_caller, model_name,temperature, url_endpoint)
    caller_feedback = create_agent("assistant", system_prompt_caller_feedback, model_name,temperature,url_endpoint)
    validator = create_agent("assistant", system_prompt_validator, model_name,temperature,url_endpoint)
    validator_feedback = create_agent("assistant", system_prompt_validator_feedback, model_name,temperature,url_endpoint)

    add_agents_to_mediator(mediator, tester, caller,caller_feedback,validator,validator_feedback)

    previous_tests=[]

    print("[QUESTION] ", user_question)
    for idx in range(n_tests):
        res_tester = send_and_print(mediator, "user", tester.id, user_question, "[TESTER]")
        res_caller = send_and_print(mediator, tester.id, caller.id, res_tester, "[CALLER]")
        
        # Step 2: Validation
        validator_result = validate_and_print(res_caller, functions, "VALIDATION:        ")
        
        # Collect results in a dictionary
        test_result = {
            "user_question": user_question,
            "res_tester": res_tester,
            "res_caller": res_caller,
            "validator_result": validator_result["validation_result"]
        }
        
        # Append the test result to the previous_tests list
        previous_tests.append(test_result)

    # Prepare feedback content
    content_feedback = f"The Question that you have to reply is: {user_question} \n\n Below you can find the feedback for the previous tests: \n\n"
    for idx, test in enumerate(previous_tests):
        content_feedback += f"""
**Test {idx+1}:**
**Tester Question**: {test['res_tester']}
**Function Calling Response**: {test['res_caller']}
**Validation Feedback Response**: {test['validator_result']}
"""
        
    print("CONTENT FEEDBACK: ", content_feedback)

    res_caller_feedback = send_and_print(mediator, "user", caller_feedback.id, content_feedback, "[CALLER FEEDBACK]")
    validator_result = validate_and_print(res_caller_feedback, functions, "VALIDATION:        ")

    caller_feedback_content = f"""
    **Question**: {user_question}
    **Function Calling Response**: {res_caller_feedback}
    **Validation Feedback**: {validator_result["validation_result"]}
    **Content Feedback**: {content_feedback}
    """

    counter = 0
    res_sender = caller_feedback_content

    while counter < MAX_TURNS:
        res_recipient = send_and_print(mediator, validator.id, validator_feedback.id, res_sender, "[VALIDATOR FEEDBACK]")

        validator_result = validate_and_print(res_recipient, functions, "VALIDATION LOOP:        ")
        
        caller_feedback_content = f"""
    **Question**: {user_question}
    **Function Calling Response**: {res_recipient}
    **Validation Feedback**: {validator_result["validation_result"]}
    **Content Feedback**: {content_feedback}
    """
        res_sender = send_and_print(mediator, validator_feedback.id, validator.id, caller_feedback_content, "[VALIDATOR]")

        res_sender = f"""
    **Question**: {user_question}
    **Function Calling Response**: {res_recipient}
    **Validation Feedback**: {res_sender}
    **Content Feedback**: {content_feedback}
    """
        
        if VALIDATION_CONDITION in res_sender:
            break

        counter += 1

    print_final_response(res_recipient)

    return res_recipient