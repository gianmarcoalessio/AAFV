from utils import send_and_print,validate_and_print,add_agents_to_mediator,leggi_file_markdown,create_agent
from agent.agent_framework import Mediator
import os
BASE_PATH = "/home/ago/giammy/TESI-MAGISTRALE/thesis/berkeley-function-call-leaderboard"


def noagent_architecture(model_name,temperature,url_endpoint, test_entry,bfcl=False):

    if bfcl:
        user_question = test_entry["question"]
        functions = test_entry["functions"]
    else:
        user_question = test_entry["question"][0][0]['content']
        functions = test_entry["function"]

    system_prompt_caller = leggi_file_markdown(os.path.join(BASE_PATH, 'system_prompt/caller.md'), functions)
    mediator = Mediator()
    caller = create_agent("assistant", system_prompt_caller, model_name,temperature, url_endpoint)
    add_agents_to_mediator(mediator, caller)
    res = send_and_print(mediator, "user", caller.id, user_question, "")

    return res  

