import json
import os
import subprocess
import ast
import sys

from bfcl.model_handler.base_handler import BaseHandler
from bfcl.model_handler.constant import GORILLA_TO_OPENAPI
from bfcl.model_handler.model_style import ModelStyle
from bfcl.model_handler.utils import (
    convert_to_function_call,
    convert_to_tool,
    default_decode_ast_prompting,
    default_decode_execute_prompting,
    format_execution_results_prompting,
    func_doc_language_specific_pre_processing,
    system_prompt_pre_processing_chat_model,
    convert_system_prompt_into_user_prompt,
    combine_consecutive_user_prompts,
)
from openai import OpenAI

from bfcl.v002_generator_bfcl import v002_generator_bfcl


def extract_question_and_functions(inference_data):
    """
    Extracts the question from the 'user' role and functions from the 'system' role in the provided inference data.

    Args:
        inference_data (dict): The input dictionary containing 'message'.

    Returns:
        dict: A dictionary containing the 'question' and 'functions'.
    """
    result = {"question": None, "functions": None}
    
    try:
        # Access the 'message' field
        messages = inference_data.get("message", [])
        
        for message in messages:
            # Extract the question from the 'user' role
            if message.get("role") == "user":
                result["question"] = message.get("content", "").strip()
            
            # Extract functions from the 'system' role
            if message.get("role") == "system":
                content = message.get("content", "")
                phrase = "Here is a list of functions in JSON format that you can invoke.\n"
                start_index = content.find(phrase)
                if start_index != -1:
                    # Locate the JSON part starting after the phrase
                    json_start = content.find("[{", start_index)
                    json_end = content.find("}]", json_start) + 2  # Include closing brackets

                    if json_start != -1 and json_end != -1:
                        functions_string = content[json_start:json_end]
                        result["functions"] = ast.literal_eval(functions_string)  # Convert to Python object
        
    except (ValueError, SyntaxError) as e:
        print(f"Error processing data: {e}")
    
    return result


class OpenAIHandler(BaseHandler):
    def __init__(self, model_name, temperature) -> None:
        super().__init__(model_name, temperature)
        self.model_style = ModelStyle.OpenAI
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.GLOBAL_INDEXES = {
            "java": 0,
            "simple": 0,
            "javascript": 0,
            "parallel": 0,
            "multiple": 0,
            "parallel_multiple": 0,
        }

    def decode_ast(self, result, language="Python"):
        if "FC" not in self.model_name:
            return default_decode_ast_prompting(result, language)
        else:
            decoded_output = []
            for invoked_function in result:
                name = list(invoked_function.keys())[0]
                params = json.loads(invoked_function[name])
                decoded_output.append({name: params})
        return decoded_output

    def decode_execute(self, result):
        if "FC" not in self.model_name:
            return default_decode_execute_prompting(result)
        else:
            function_call = convert_to_function_call(result)
            return function_call

    #### FC methods ####

    def _query_FC(self, inference_data: dict):
        message: list[dict] = inference_data["message"]
        tools = inference_data["tools"]
        inference_data["inference_input_log"] = {"message": repr(message), "tools": tools}

        if len(tools) > 0:
            api_response = self.client.chat.completions.create(
                messages=message,
                model=self.model_name.replace("-FC", ""),
                temperature=self.temperature,
                tools=tools,
            )
        else:
            api_response = self.client.chat.completions.create(
                messages=message,
                model=self.model_name.replace("-FC", ""),
                temperature=self.temperature,
            )
        return api_response

    def _pre_query_processing_FC(self, inference_data: dict, test_entry: dict) -> dict:
        inference_data["message"] = []
        return inference_data

    def _compile_tools(self, inference_data: dict, test_entry: dict) -> dict:
        functions: list = test_entry["function"]
        test_category: str = test_entry["id"].rsplit("_", 1)[0]

        functions = func_doc_language_specific_pre_processing(functions, test_category)
        tools = convert_to_tool(functions, GORILLA_TO_OPENAPI, self.model_style)

        inference_data["tools"] = tools

        return inference_data

    def _parse_query_response_FC(self, api_response: any) -> dict:
        try:
            model_responses = [
                {func_call.function.name: func_call.function.arguments}
                for func_call in api_response.choices[0].message.tool_calls
            ]
            tool_call_ids = [
                func_call.id for func_call in api_response.choices[0].message.tool_calls
            ]
        except:
            model_responses = api_response.choices[0].message.content
            tool_call_ids = []

        model_responses_message_for_chat_history = api_response.choices[0].message

        return {
            "model_responses": model_responses,
            "model_responses_message_for_chat_history": model_responses_message_for_chat_history,
            "tool_call_ids": tool_call_ids,
            "input_token": api_response.usage.prompt_tokens,
            "output_token": api_response.usage.completion_tokens,
        }

    def add_first_turn_message_FC(
        self, inference_data: dict, first_turn_message: list[dict]
    ) -> dict:
        inference_data["message"].extend(first_turn_message)
        return inference_data

    def _add_next_turn_user_message_FC(
        self, inference_data: dict, user_message: list[dict]
    ) -> dict:
        inference_data["message"].extend(user_message)
        return inference_data

    def _add_assistant_message_FC(
        self, inference_data: dict, model_response_data: dict
    ) -> dict:
        inference_data["message"].append(
            model_response_data["model_responses_message_for_chat_history"]
        )
        return inference_data

    def _add_execution_results_FC(
        self,
        inference_data: dict,
        execution_results: list[str],
        model_response_data: dict,
    ) -> dict:
        # Add the execution results to the current round result, one at a time
        for execution_result, tool_call_id in zip(
            execution_results, model_response_data["tool_call_ids"]
        ):
            tool_message = {
                "role": "tool",
                "content": execution_result,
                "tool_call_id": tool_call_id,
            }
            inference_data["message"].append(tool_message)

        return inference_data

    #### Prompting methods ####

    def _query_prompting(self, inference_data: dict):
        inference_data["inference_input_log"] = {"message": repr(inference_data["message"])}

        # These two models have temperature fixed to 1
        # Beta limitation: https://platform.openai.com/docs/guides/reasoning/beta-limitations
        if "o1-preview" in self.model_name or "o1-mini" in self.model_name:
            api_response = self.client.chat.completions.create(
                messages=inference_data["message"],
                model=self.model_name,
                temperature=1,
            )
        elif (self.model_name  == 'agent-network'):
            # script_path = "/home/ago/giammy/TESI-MAGISTRALE/thesis/berkeley-function-call-leaderboard/v002-generator-bfcl.py"
            # try:
                # print(f"******************** INFERENCE DATA: {json.dumps(extract_question_and_functions(inference_data))}")
                # result = subprocess.run(
                #     ["python", script_path, json.dumps(extract_question_and_functions(inference_data))],
                #     capture_output=True, text=True, check=True
                # )
                # api_response = result.stdout.strip()
                # print(f"API response: {api_response}")

            # except subprocess.CalledProcessError as e:
            #     print(f"Errore durante l'esecuzione di v002-generator-bfcl: {e}")
            #     print(f"Output di errore: {e.stderr}")
            #     api_response = {"error": str(e)}


            test_entry = extract_question_and_functions(inference_data)
            api_response = v002_generator_bfcl(test_entry,self.model_name)

        elif (self.model_name  == 'agent-network-gpt'):
            test_entry = extract_question_and_functions(inference_data)
            api_response = v002_generator_bfcl(test_entry,self.model_name)

        else:
            api_response = self.client.chat.completions.create(
                messages=inference_data["message"],
                model=self.model_name,
                temperature=self.temperature,
            )

        return api_response

    def _pre_query_processing_prompting(self, test_entry: dict) -> dict:
        functions: list = test_entry["function"]
        test_category: str = test_entry["id"].rsplit("_", 1)[0]

        functions = func_doc_language_specific_pre_processing(functions, test_category)
            # Mapping of test categories to their total test limits
        total_tests = {
            "java": 100,
            "simple": 400,
            "javascript": 50,
            "parallel": 200,
            "multiple": 200,
            "parallel_multiple": 200,
        }

        # Initialize GLOBAL_INDEX for each category if not already done
        if not hasattr(self, "GLOBAL_INDEXES"):
            self.GLOBAL_INDEXES = {category: 0 for category in total_tests.keys()}

        # Perform language-specific preprocessing
        functions = func_doc_language_specific_pre_processing(functions, test_category)
        percentage = 1 # 30% of tests allowed

        # Check if the test category exists and process
        if test_category in total_tests:
            total_test = total_tests[test_category]
            number_test = total_test * percentage

            # Increment the index for the specific test category
            self.GLOBAL_INDEXES[test_category] += 1

            # Interrupt processing if the limit is reached
            if self.GLOBAL_INDEXES[test_category] > number_test:
                raise Exception(
                    f"{test_category}: Reached the limit of tests {int(number_test)}/{total_test}, "
                    f"completed {self.GLOBAL_INDEXES[test_category]} tests"
                )
        else:
            raise ValueError(f"Unknown test category: {test_category}")


        test_entry["question"][0] = system_prompt_pre_processing_chat_model(
            test_entry["question"][0], functions, test_category
        )
        # Special handling for o1-preview and o1-mini as they don't support system prompts yet
        if "o1-preview" in self.model_name or "o1-mini" in self.model_name:
            for round_idx in range(len(test_entry["question"])):
                test_entry["question"][round_idx] = convert_system_prompt_into_user_prompt(
                    test_entry["question"][round_idx]
                )
                test_entry["question"][round_idx] = combine_consecutive_user_prompts(
                    test_entry["question"][round_idx]
                )

        return {"message": []}

    def _parse_query_response_prompting(self, api_response: any) -> dict:

        if self.model_name == "agent-network" or self.model_name == "agent-network-gpt":
            query_response = {
                "model_responses": api_response,
                "model_responses_message_for_chat_history": None,
                "input_token": 0,
                "output_token": 0,
            }
        else:
            query_response = {
                "model_responses": api_response.choices[0].message.content,
                "model_responses_message_for_chat_history": api_response.choices[0].message,
                "input_token": api_response.usage.prompt_tokens,
                "output_token": api_response.usage.completion_tokens,
            }
        return query_response

    def add_first_turn_message_prompting(
        self, inference_data: dict, first_turn_message: list[dict]
    ) -> dict:
        inference_data["message"].extend(first_turn_message)
        return inference_data

    def _add_next_turn_user_message_prompting(
        self, inference_data: dict, user_message: list[dict]
    ) -> dict:
        inference_data["message"].extend(user_message)
        return inference_data

    def _add_assistant_message_prompting(
        self, inference_data: dict, model_response_data: dict
    ) -> dict:
        inference_data["message"].append(
            model_response_data["model_responses_message_for_chat_history"]
        )
        return inference_data

    def _add_execution_results_prompting(
        self, inference_data: dict, execution_results: list[str], model_response_data: dict
    ) -> dict:
        formatted_results_message = format_execution_results_prompting(
            inference_data, execution_results, model_response_data
        )

        inference_data["message"].append(
            {"role": "user", "content": formatted_results_message}
        )

        return inference_data
