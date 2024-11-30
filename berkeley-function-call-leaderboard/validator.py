from bfcl.model_handler.constant import (
    UNDERSCORE_TO_DOT,
    JAVA_TYPE_CONVERSION,
    JS_TYPE_CONVERSION,
)
from bfcl.eval_checker.ast_eval.type_convertor.java_type_converter import java_type_converter
from bfcl.eval_checker.ast_eval.type_convertor.js_type_converter import js_type_converter
import re
import json
import ast
from bfcl.model_handler.utils import ast_parse

#### Constants ####
PYTHON_TYPE_MAPPING = {
    "string": str,
    "integer": int,
    "float": float,
    "boolean": bool,
    "array": list,
    "tuple": list,
    "dict": dict,
    "any": str,
}

# This is the list of types that we need to recursively check its values
PYTHON_NESTED_TYPE_CHECK_LIST = ["array", "tuple"]

NESTED_CONVERSION_TYPE_LIST = ["Array", "ArrayList", "array"]


def default_decode_ast_prompting(result, language="Python"):
    result = result.strip("`\n ")
    if not result.startswith("["):
        result = "[" + result
    if not result.endswith("]"):
        result = result + "]"
    decoded_output = ast_parse(result, language)

    return decoded_output

#### Main function ####
def ast_checker(
    func_description, model_output, language, test_category, model_name
):


    try:
        model_output = default_decode_ast_prompting(model_output, language)
    except Exception as e:
        return {
                "valid": False,
                "error": [f"Invalid syntax. Failed to decode AST. {str(e)}"],
                "error_type": "ast_decoder:decoder_failed",
            }
        

    if model_output is None:
        return {
            "valid": False,
            "error": ["No functions has been choose!"],
            "error_type": "no_function_called"
        }

    if "parallel" in test_category or "multiple" in test_category:
        return parallel_function_checker_no_order(
            func_description, model_output, language, model_name
        )
        
    else:
        if len(model_output) != 1:
            return {
                "valid": False,
                "error": ["Wrong number of functions."],
                "error_type": "simple_function_checker:wrong_count",
            }

        return simple_function_checker(
            func_description[0], model_output[0], language, model_name
        )

#### Helper functions for AST ####
def find_description(func_descriptions, name):
    if type(func_descriptions) == list:
        for func_description in func_descriptions:
            if func_description["name"] == name:
                return func_description
        return None
    else:
        # it is a dict, there is only one function
        return func_descriptions

def convert_func_name(function_name, model_name: str):
    model_name_escaped = model_name.replace("_", "/")
    if "." in function_name:
        if model_name_escaped in UNDERSCORE_TO_DOT:
            # OAI does not support "." in the function name so we replace it with "_". ^[a-zA-Z0-9_-]{1,64}$ is the regex for the name.
            # This happens for OpenAI, Mistral, and Google models
            return re.sub(r"\.", "_", function_name)
    return function_name

def type_checker(
    param: str,
    value,
    expected_type_description: str,
    expected_type_converted,
    nested_type_converted=None,
):
    """
    Enhanced type_checker for validating the value against expected types.
    Includes nested type validation without relying on possible_answer.
    """
    result = {
        "valid": True,
        "error": [],
        "error_type": "type_error:simple",
    }

    # Check for direct type match
    if type(value) == expected_type_converted:
        # print("NESTED_TYPE_CONVERTED:", nested_type_converted)
        # If no nested type validation is required, return valid
        if nested_type_converted is None:
            return result
        
        # Validate nested types for lists/arrays
        if isinstance(value, list):
            for item in value:
                nested_check = type_checker(
                    param,
                    item,
                    str(nested_type_converted),
                    nested_type_converted,
                )
                if not nested_check["valid"]:
                    result["valid"] = False
                    result["error"].append(
                        f"Nested type validation failed for parameter {repr(param)}. "
                        f"Expected type {expected_type_description}[{nested_type_converted}], got {type(item).__name__}."
                    )
                    result["error_type"] = "type_error:nested"
                    return result
            return result

    # Handle Python auto conversion from int to float
    if expected_type_converted == float and isinstance(value, int):
        return result

    # For unexpected types, add error message
    result["valid"] = False
    result["error"].append(
        f"Incorrect type for parameter {repr(param)}. Expected type {expected_type_description}, got {type(value).__name__}. Parameter value: {repr(value)}."
    )
    result["error_type"] = "type_error:simple"
    return result

def simple_function_checker(
    func_description: dict,
    model_output: dict,
    language: str,
    model_name: str,
):
    # Extract function name and parameters details
    func_name = func_description["name"]
    param_details = func_description["parameters"]["properties"]
    required_params = func_description["parameters"]["required"]

    # Initialize a result dictionary
    result = {
        "valid": True,
        "error": [],
        "error_type": "simple_function_checker:unclear",
    }

    func_name = convert_func_name(func_name, model_name)

    
    # Check if function name matches
    if func_name not in model_output:
        result["valid"] = False
        result["error"].append(
            f"Function name {repr(func_name)} not found in model output. "
        )
        result["error_type"] = "simple_function_checker:wrong_func_name"
        return result

    model_params = model_output[func_name]

    # print(f'REQUIRED_PARAMS for {model_output}:', required_params)
    # Check for required parameters in model output
    for param in required_params:
        if param not in model_params:
            result["valid"] = False
            result["error"].append(f"Missing required parameter: {repr(param)}.")
            result["error_type"] = "simple_function_checker:missing_required"
            return result

    # Validate types for each parameter in model output
    for param, value in model_params.items():
        if param not in param_details:
            result["valid"] = False
            result["error"].append(f"Unexpected parameter: {repr(param)}.")
            result["error_type"] = "simple_function_checker:unexpected_param"
            return result

        full_param_details = param_details[param]
        expected_type_description = full_param_details["type"]  # This is a string
        nested_type_converted = None

        if language == "Java":
            expected_type_converted = JAVA_TYPE_CONVERSION[expected_type_description]

            if expected_type_description in JAVA_TYPE_CONVERSION:
                if type(value) != str:
                    result["valid"] = False
                    result["error"].append(
                        f"Incorrect type for parameter {repr(param)}. Expected type String, got {type(value).__name__}. Parameter value: {repr(value)}."
                    )
                    result["error_type"] = "type_error:java"
                    return result

                if expected_type_description in NESTED_CONVERSION_TYPE_LIST:
                    nested_type = param_details[param]["items"]["type"]
                    nested_type_converted = JAVA_TYPE_CONVERSION[nested_type]
                    value = java_type_converter(
                        value, expected_type_description, nested_type
                    )
                else:
                    value = java_type_converter(value, expected_type_description)

        elif language == "JavaScript":
            expected_type_converted = JS_TYPE_CONVERSION[expected_type_description]

            if expected_type_description in JS_TYPE_CONVERSION:
                if type(value) != str:
                    result["valid"] = False
                    result["error"].append(
                        f"Incorrect type for parameter {repr(param)}. Expected type String, got {type(value).__name__}. Parameter value: {repr(value)}."
                    )
                    result["error_type"] = "type_error:js"
                    return result
            

                if expected_type_description in NESTED_CONVERSION_TYPE_LIST:
                    nested_type = param_details[param]["items"]["type"]
                    nested_type_converted = JS_TYPE_CONVERSION[nested_type]
                    value = js_type_converter(
                        value, expected_type_description, nested_type
                    )
                else:
                    value = js_type_converter(value, expected_type_description)

        elif language == "Python":
            expected_type_converted = PYTHON_TYPE_MAPPING[expected_type_description]
            # improve the validator for the nested type script beacasue I have an hard time to detect when the nested type is part of a list, we can address this in the system prompt of the validator
            if expected_type_description in PYTHON_NESTED_TYPE_CHECK_LIST:
                nested_type = param_details[param]["items"]["type"]
                nested_type_converted = PYTHON_TYPE_MAPPING[nested_type]

        # We convert all tuple value to list when the expected type is tuple.
        if expected_type_description == "tuple" and type(value) == tuple:
            value = list(value)

        # Allow python auto conversion from int to float
        if (
            language == "Python"
            and expected_type_description == "float"
            and type(value) == int
        ):
            value = float(value)

        # Type checking
        type_check_result = type_checker(
            param,
            value,
            expected_type_description,
            expected_type_converted,
            nested_type_converted,
        )
        if not type_check_result["valid"]:
            return type_check_result

    return result

def parallel_function_checker_no_order(
    func_descriptions: list,
    model_output: list,
    language: str,
    model_name: str,
):

    matched_indices = []

    # We go through the function descriptions and try to match them with model outputs
    for i in range(len(func_descriptions)):
        func_description = func_descriptions[i]

        all_errors = []


        for index in range(len(model_output)):
            if index in matched_indices:
                continue

            result = simple_function_checker(
                func_description,
                model_output[index],
                language,
                model_name,
            )



            if result["valid"]:
                matched_indices.append(index)
                break
            else:
                all_errors.append(
                    {
                        f"Model Result Index {index}": {
                            "sub_error": result["error"],
                            "sub_error_type": result["error_type"],
                            "model_output_item": model_output[index],
                        }
                    }
                )

        if not result["valid"]:
            considered_indices = [
                i for i in range(len(model_output)) if i not in matched_indices
            ]
            all_errors.insert(
                0,
                f"Could not find a matching function among index {considered_indices} of model output for index {i} of function descriptions.",
            )
            result = {
                "valid": False,  # Invalid only if no matches
                "error": all_errors,
                "error_type": "parallel_function_checker_no_order:cannot_find_match"
            }
    if len(matched_indices) > 0 :
        return {
            "valid": True,  # Valid if at least one match
            "error": all_errors,  # Keep errors for reference
            "error_type": "parallel_function_checker_no_order:partial_match"
        }

    return {"valid": True, "error": []}

# def multiple_function_checker(
#     func_descriptions: list,
#     model_output: list,
#     language: str,
#     model_name: str,
# ):

#     func_description = func_descriptions[0]
#     return simple_function_checker(
#         func_description,
#         model_output[0],
#         language,
#         model_name,
#     )