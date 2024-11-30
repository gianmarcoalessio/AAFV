#### -------------------------------------------------- ####

#### COSE VECCHIE

#### -------------------------------------------------- ####


from bfcl.model_handler.oss_model.base_oss_handler import OSSHandler
from bfcl._llm_response_generation import collect_test_cases, parse_test_category_argument
from bfcl.model_handler.utils import system_prompt_pre_processing_chat_model
import json
from bfcl.model_handler.utils import system_prompt_pre_processing_assistant_model
from pathlib import Path

RESULT_PATH = Path("./result")
VERSION_PREFIX = "BFCL_v3"

def prepare_test_environment(model_name_bfcl, temperature, test_category):

    # Initialize the handler with the given type_handler
    handler = OSSHandler(model_name=model_name_bfcl, temperature=temperature)
    # Ensure model_name_bfcl and test_category are lists
    if not isinstance(model_name_bfcl, list):
        model_name_bfcl = [model_name_bfcl]
    if not isinstance(test_category, list):
        test_category = [test_category]

    # Parse test categories
    test_name_total, test_filename_total = parse_test_category_argument(test_category)
    # Adjust model name (e.g., add '-optimized' suffix)
    model_name_optimized = model_name_bfcl[0] + "-optimized"
    # Collect test cases
    test_cases_total = collect_test_cases(
        test_name_total, test_filename_total, model_name_optimized
    )
    
    return test_cases_total, handler

def prepare_system_prompts(test_entry, handler, default_jolly_prompt, default_expert_prompt, default_assistant_prompt):

    inference_data = handler._pre_query_processing_prompting(test_entry)

    # Extract the system functions list from inference_data
    system_functions_list = inference_data["function"]
    
    # Add the first turn message prompting
    inference_data = handler.add_first_turn_message_prompting(
        inference_data, test_entry["question"][0]
    )
    system_instruction_action = inference_data["message"][0]['content']
    
    # Prepare the system controller and expert prompts
    system_jolly_data = system_prompt_pre_processing_chat_model(
        [test_entry["question"][0][1]], default_jolly_prompt, system_functions_list
    )
    system_expert_data = system_prompt_pre_processing_chat_model(
        [test_entry["question"][0][1]], default_expert_prompt, system_functions_list
    )
    system_assistant_data = system_prompt_pre_processing_assistant_model(
        [test_entry["question"][0][1]], default_assistant_prompt, system_functions_list
    )
    
    system_jolly = system_jolly_data[0]['content']
    system_expert = system_expert_data[0]['content']
    system_assistant = system_assistant_data[0]['content']
    
    return system_instruction_action, system_jolly, system_expert, system_assistant

def prepare_system_prompt_function_parameter_extraction(test_entry, handler,response, default_assistant_prompt):
    inference_data = handler._pre_query_processing_prompting(test_entry)

    # Extract the system functions list from inference_data
    system_functions_list = inference_data["function"]

        # Usa una regex per estrarre il nome della funzione
    match = re.match(r'\[([\w_]+)\s*\(', response)
    if not match or match==None: 
        single_function_information='The function name is not provided in the response, ask the expert to provide it for you. Explaining the function'
    else:
        function_name = match.group(1)

        single_function_information = []
        # Trova la funzione corrispondente nella function_list
        for func in system_functions_list:
            if func.get('name') == function_name:
                # Estrai i parametri della funzione
                params = func.get('parameters', {}).get('properties', {})
                required_params = func.get('parameters', {}).get('required', [])
                param_list = []
                for param_name, param_info in params.items():
                    param_entry = {
                        'name': param_name,
                        'type': param_info.get('type'),
                        'description': param_info.get('description'),
                        'required': param_name in required_params
                    }
                    param_list.append(param_entry)
                single_function_information.append({
                    'function_name': function_name,
                    'parameters': param_list
                })
    
    system_prompt = default_assistant_prompt.format(single_function_information=single_function_information)
    return system_prompt
    

def write(result, model_name):
    model_name_dir = model_name.replace("/", "_")
    model_result_dir = RESULT_PATH / model_name_dir
    model_result_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(result, dict):
        result = [result]

    for entry in result:
        test_category = entry["id"].rsplit("_", 1)[0]
        file_to_write = f"{VERSION_PREFIX}_{test_category}_result.json"
        file_to_write = model_result_dir / file_to_write
        with open(file_to_write, "a+") as f:
            try:
                f.write(json.dumps(entry) + "\n")
            except Exception as e:
                print(f"❗️Failed to write result: {e}")
                f.write(
                    json.dumps(
                        {
                            "id": entry["id"],
                            "result": repr(entry),
                        }
                    )
                    + "\n"
                )