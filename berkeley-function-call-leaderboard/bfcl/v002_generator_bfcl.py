import sys
import os

# Add the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agent.agent_architecture import agent_architecture
from agent.noagent_architecture import noagent_architecture



def v002_generator_bfcl(test_entry, agent_network):
    """
    In order to run it 
    bfcl generate --model agent-network --test-category python-ast --num-threads 4
    """
    if agent_network == "agent-network-gpt":
      MODEL_NAME_BFCL = 'gpt-3.5-turbo-0125' # only if i'm using local endpoint
      huggingface_endpoint_url= ""
    elif agent_network == "agent-network":
      # MODEL_NAME_BFCL = 'Qwen/Qwen2.5-1.5B-Instruct'
      # MODEL_NAME_BFCL ="meta-llama/Llama-3.2-3B-Instruct"
      # MODEL_NAME_BFCL ="meta-llama/Llama-3.1-8B-Instruct"
      MODEL_NAME_BFCL = "Qwen/Qwen2.5-7B-Instruct"
      # MODEL_NAME_BFCL = "Qwen/Qwen2.5-3B-Instruct"
      local_endpoint = "http://localhost:8080/v1/chat/completions"
      qwen_1_5b_endpoint = "https://qczw73rk6noiiz27.us-east-1.aws.endpoints.huggingface.cloud/v1/chat/completions" 
      qwen_3b_endpoint = "https://ffsur9kuz8bomzwn.us-east-1.aws.endpoints.huggingface.cloud/v1/chat/completions"
      qwen_7b_endpoint = "https://hkkt5ay0stiz2sxy.us-east-1.aws.endpoints.huggingface.cloud/v1/chat/completions"
      llama_3b_endpoint ="https://e36nbky8k2b92hp5.us-east-1.aws.endpoints.huggingface.cloud/v1/chat/completions"
      llama_8b_endpoint ="https://l41j2vkrxy8txnck.us-east-1.aws.endpoints.huggingface.cloud/v1/chat/completions"
      huggingface_endpoint_url = qwen_7b_endpoint
      
    TEMPERATURE = 0.1
    MAX_TURNS = 4
    N_TESTS = 2
    with_agent =True

    if with_agent:

      result = agent_architecture(
          model_name = MODEL_NAME_BFCL,
          temperature=TEMPERATURE,
          url_endpoint= huggingface_endpoint_url,
          test_entry=test_entry,
          bfcl=True,
          n_tests=N_TESTS,
          MAX_TURNS=MAX_TURNS,
          VALIDATION_CONDITION="Valid: The function call respects the parameter types and requirements."
      )

    else:
       
       result = noagent_architecture(
          model_name = MODEL_NAME_BFCL,
          temperature=TEMPERATURE,
          url_endpoint= huggingface_endpoint_url,
          test_entry=test_entry,
          bfcl=True
          )
        
       

    return result