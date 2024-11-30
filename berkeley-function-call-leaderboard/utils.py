
#### -------------------------------------------------- ####

#### COSE NUOVE

#### -------------------------------------------------- ####

import json
import re
from typing import List, Dict, Any
from pydantic import create_model, Field, ValidationError
from agent.agent_framework import OpenSourceAgent, Mediator
import ast

# Helper Functions
def create_agent(name, system_instruction, model_name,temperature,huggingface_endpoint_url):
    """Creates an OpenSourceAgent with the given parameters."""
    return OpenSourceAgent(name=name, system_instruction=system_instruction,temperature=temperature, model_name=model_name, huggingface_endpoint_url= huggingface_endpoint_url)

def add_agents_to_mediator(mediator, *agents):
    """Adds multiple agents to the mediator."""
    for agent in agents:
        mediator.add_agent(agent)

def colored_label(label, color_code):
    """Returns the label wrapped in ANSI escape codes for coloring."""
    return f"\033[{color_code}m{label}\033[0m"

def send_and_print(mediator, sender_id, recipient_id, content, label):
    """Sends content using the mediator and prints the response."""
    response = mediator.send(sender_id, recipient_id, content)
    if label:
        colored = colored_label(label, "34")  # Blue color for label
        print(f'{colored:<30} Response: {response}')
    return response

def validate_and_print(content, function, label):
    """Validates a function call and prints the validation result."""
    validation_result = validate_function_call(content, function)
    if label:
        colored = colored_label(label, "32")  # Green color for label
        print(f'{colored:<30} Validation NOMODEL: {validation_result}')
    return validation_result

def extract_function_definitions(model_output: str, function_definitions: List[Dict[str, Any]]):
    result = {"model_output": model_output, "validation_result": ""}
    function_match = re.match(r"\[([\w.]+)\((.*)\)\]", model_output.strip())  # Adjusted regex to allow dots in function names
    function_name = function_match.group(1)
    # Step 2: Extract the function call and parameters
    function_def = next((f for f in function_definitions if f['name'] == function_name), None)
    if not function_def:
        result["validation_result"] = f"Invalid: No matching function definition found for '{function_name}'."
        return result 

def leggi_file_markdown(percorso_file,functions=None):
    with open(percorso_file, 'r', encoding='utf-8') as file:
        contenuto = file.read()
    if(functions):
        contenuto = contenuto.format(functions=functions)
    return contenuto


def validate_function_call(model_output: str, function_definitions: List[Dict[str, Any]]):
    result = {
        "model_output": model_output,
        "validation_result": "",
        "individual_results": []
    }

    # Step 1: Check if the model output is enclosed in square brackets
    if not model_output.strip().startswith("[") or not model_output.strip().endswith("]"):
        result["validation_result"] = "Invalid: The model output is not enclosed in square brackets."
        return result

    # Remove the outer brackets
    inner_output = model_output.strip()[1:-1].strip()

    # Split the model output into individual function calls
    # This regex splits on commas not within parentheses
    function_calls = re.findall(r'[\w\.]+\([^\)]*\)', inner_output)

    if not function_calls:
        result["validation_result"] = "Invalid: No valid function calls found."
        return result

    all_valid = True

    for func_call in function_calls:
        func_result = validate_single_function_call(func_call, function_definitions)
        result["individual_results"].append(func_result)
        if not func_result["validation_result"].startswith("Valid"):
            all_valid = False

    if all_valid:
        result["validation_result"] = "Valid: All function calls respect the parameter types and requirements."
    else:
        result["validation_result"] = "Invalid: One or more function calls failed validation."

    return result
def validate_function_call(model_output: str, function_definitions: List[Dict[str, Any]]) -> Dict[str, Any]:
    result = {
        "model_output": model_output,
        "validation_result": "",
    }

    # Step 1: Check if the model output is enclosed in square brackets
    if not model_output.strip().startswith("[") or not model_output.strip().endswith("]"):
        result["validation_result"] = "Invalid: The model output is not enclosed in square brackets."
        return result

    # Remove the outer brackets and strip whitespace
    inner_output = model_output.strip()[1:-1].strip()

    # Split the model output into individual function calls
    # This regex matches function calls, even if they contain nested parentheses
    function_calls = re.findall(r'[\w\.]+\([^()]*?(?:\([^()]*?\)[^()]*?)*\)', inner_output)

    if not function_calls:
        result["validation_result"] = "Invalid: No valid function calls found."
        return result

    invalid_messages = []
    all_valid = True

    for index, func_call in enumerate(function_calls, start=1):
        func_result = validate_single_function_call(func_call, function_definitions)
        if not func_result["validation_result"].startswith("Valid"):
            all_valid = False
            function_name = func_result["function_name"]
            invalid_messages.append(
                f"Invalid: Function call at index {index} ({function_name}) is not correct because {func_result['validation_result']}"
            )

    # Determine the overall validation result
    if all_valid:
        result["validation_result"] = "Valid: All function calls respect the parameter types and requirements."
    else:
        result["validation_result"] = ' | '.join(invalid_messages)

    return result

def validate_single_function_call(func_call: str, function_definitions: List[Dict[str, Any]]) -> Dict[str, Any]:
    func_result = {"function_call": func_call, "function_name": "", "validation_result": ""}

    # Step 2: Extract the function name and parameters
    function_match = re.match(r"([\w\.]+)\((.*)\)", func_call.strip())
    if not function_match:
        func_result["validation_result"] = "The function call is not in the correct format."
        return func_result

    function_name = function_match.group(1)
    func_result["function_name"] = function_name
    params_string = function_match.group(2)

    # Step 3: Transform params_string into valid Python dictionary syntax
    try:
        # Replace equals signs with colons and wrap keys in quotes
        params_string_prepared = re.sub(r'(\w+)\s*=', r'"\1":', params_string)

        # Replace single quotes with double quotes
        params_string_prepared = params_string_prepared.replace("'", '"')

        # Enclose the params_string in curly braces to make it a dict
        params_string_prepared = f"{{{params_string_prepared}}}"

        # Use ast.literal_eval to safely evaluate the params
        params = ast.literal_eval(params_string_prepared)
    except (ValueError, SyntaxError) as e:
        func_result["validation_result"] = f"The parameters are not valid Python literals. Error: {str(e)}"
        return func_result

    # Step 4: Find the matching function definition
    function_def = next(
        (f for f in function_definitions if f["name"] == function_name), None
    )
    if not function_def:
        func_result["validation_result"] = f"No matching function definition found for '{function_name}'."
        return func_result

    # Step 5: Dynamically create a validation model based on the function definition
    try:
        # Build fields for the Pydantic model dynamically
        fields = {}
        for param_name, param_details in function_def["parameters"]["properties"].items():
            param_type = param_details["type"]
            if param_type == "integer":
                field_type = int
            elif param_type == "string":
                field_type = str
            elif param_type == "array":
                field_type = list
            elif param_type == "number":
                field_type = float
            elif param_type == "boolean":
                field_type = bool
            else:
                field_type = Any  # Default to Any if type not recognized
            fields[param_name] = (
                field_type,
                Field(default=None)
                if param_name not in function_def["parameters"].get("required", [])
                else ...,
            )

        # Dynamically create a Pydantic model for validation
        FunctionModel = create_model(function_name, **fields)

        # Step 6: Validate the parameters using the created model
        FunctionModel(**params)

        # If validation succeeds
        func_result["validation_result"] = "Valid: The function call respects the parameter types and requirements."
        return func_result

    except ValidationError as e:
        # If validation fails due to type or required field issues
        error_messages = []
        for err in e.errors():
            loc = ' -> '.join(map(str, err['loc']))
            msg = err['msg']
            error_messages.append(f"{loc}: {msg}")
        func_result["validation_result"] = '; '.join(error_messages)
        return func_result
    except Exception as e:
        # Catch-all for any unexpected errors
        func_result["validation_result"] = f"{str(e)}"
        return func_result
    

