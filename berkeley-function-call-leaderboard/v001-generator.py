import argparse
from agent.constant import DEFAULT_JOLLY_PROMPT, DEFAULT_EXPERT_PROMPT, DEFAULT_ASSISTANT_PROMPT, DEFAULT_ASSISTANT2_PROMPT
from agent.agent_framework import OpenSourceAgent, Mediator
from utils_v001 import prepare_test_environment, prepare_system_prompts, write, prepare_system_prompt_function_parameter_extraction

# handler 
# QWEN MODEL: 'Qwen/Qwen2.5-1.5B-Instruct'
# LLAMA MODEL: ...

def run_tests(test_category):
    # Crea un'istanza di QwenHandler con i parametri necessari
    handler_bfcl ='Qwen/Qwen2.5-1.5B-Instruct'
    model_name='Qwen/Qwen2.5-3B-Instruct'
    temperature = 0.9  # Sostituisci con il valore desiderato per la temperatura

    offset = 0
    test_cases_total, handler = prepare_test_environment(handler_bfcl, temperature, test_category)
    test_cases_total = test_cases_total[offset:]
    with_agent = True

    # Lista per salvare i risultati
    results = []

    # Itera su tutti i test cases
    for i, test_entry in enumerate(test_cases_total):
        global_index = i + offset
        # Prepara i prompt di sistema per ogni test case
        system_instruction_action, system_jolly, system_expert, system_assistant = prepare_system_prompts(
            test_entry, 
            handler,
            DEFAULT_JOLLY_PROMPT,
            DEFAULT_EXPERT_PROMPT,
            DEFAULT_ASSISTANT_PROMPT)
        
        # Crea gli agenti OpenSourceAgent per ogni test case
        action_caller = OpenSourceAgent(name="action_caller", system_instruction=system_instruction_action, model_name=model_name)
        syntax_expert = OpenSourceAgent(name="syntax_expert", system_instruction=system_expert, model_name=model_name)

        # Crea un Mediator per ogni test case
        mediator = Mediator()
        mediator.add_agent(action_caller)
        mediator.add_agent(syntax_expert)

        res = mediator.send("user", action_caller.id, test_entry["question"][0][1]['content'])
        if not with_agent:
            print(res)

        if with_agent:
            system_assistant = prepare_system_prompt_function_parameter_extraction(test_entry, handler, res, DEFAULT_ASSISTANT2_PROMPT) 
            syntax_assistant = OpenSourceAgent(name="syntax_assistant", system_instruction=system_assistant,model_name=model_name)
            mediator.add_agent(syntax_assistant)
            
            res = mediator.math_problem_solving_architecture(
                assistant_id=action_caller.id, 
                assistant2_id=syntax_assistant.id, 
                expert_id=syntax_expert.id, 
                user_input=test_entry["question"][0][1]['content'], 
                str_condition="ok", 
                max_turns=6
            )
    
        result_entry = {
            "id": f"{test_category}_{global_index}",
            "result": res
        }
        results.append(result_entry)

        write(result_entry, model_name)

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