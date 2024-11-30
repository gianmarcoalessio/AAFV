from agent.agent_architecture import agent_architecture
from agent.agent_framework import Mediator
from utils_v001 import prepare_test_environment, write
import argparse
import os

BASE_PATH = "/home/ago/giammy/TESI-MAGISTRALE/thesis/berkeley-function-call-leaderboard"

def run_tests(test_category):
    MODEL_NAME_BFCL = 'Qwen/Qwen2.5-1.5B-Instruct'
    TEMPERATURE = 0.9
    MAX_TURNS = 4
    N_TESTS = 2

    local_endpoint = "http://localhost:8080/v1/chat/completions"
    qwen_1_5b_endpoint = "https://qczw73rk6noiiz27.us-east-1.aws.endpoints.huggingface.cloud/v1/chat/completions" 
    qwen_3b_endpoint = ""
    qwen_7b_endpoint = ""
    llama_3b_endpoint =""
    llama_8b_endpoint ="https://l41j2vkrxy8txnck.us-east-1.aws.endpoints.huggingface.cloud/v1/chat/completions"
    huggingface_endpoint_url = local_endpoint 

    offset = 0
    test_cases_total, _ = prepare_test_environment(MODEL_NAME_BFCL, TEMPERATURE, test_category)
    test_cases_total = test_cases_total[offset:]

    # Lista per salvare i risultati
    results = []
    mediator = Mediator()

    # Itera su tutti i test cases
    for i, test_entry in enumerate(test_cases_total):
        global_index = i + offset

        result = agent_architecture(
            model_name = MODEL_NAME_BFCL,
            temperature=TEMPERATURE,
            url_endpoint= huggingface_endpoint_url,
            test_entry=test_entry,
            bfcl=False,
            n_tests=N_TESTS,
            MAX_TURNS=MAX_TURNS,
            VALIDATION_CONDITION="Valid: The function call respects the parameter types and requirements."
        )

        result_entry = {
            "id": f"{test_category}_{global_index}",
            "result": result
        }
        results.append(result_entry)

        write(result_entry, MODEL_NAME_BFCL)

def main(test_category):
    if test_category == "all":
        categories = [ "simple","parallel", "multiple", "parallel_multiple", "java", "javascript"]
        for category in categories:
            run_tests(category)
    else:
        run_tests(test_category)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some arguments.")
    parser.add_argument("test_category", type=str, help="Test category (simple, parallel, multiple, parallel_multiple, java, javascript, all)")

    args = parser.parse_args()
    main(args.test_category)