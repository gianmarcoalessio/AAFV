import uuid
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import json
from bfcl.model_handler.oss_model.qwen import QwenHandler
from bfcl.model_handler.oss_model.llama import LlamaHandler
from llama_cpp import Llama
import requests
from openai import OpenAI


# Load environment variables from .env file
load_dotenv()
client = OpenAI()

config_path = os.path.join(os.path.dirname(__file__), "../config.json")
with open(config_path, "r") as file:
    config = json.load(file)

class Agent:
    def __init__(self, name: str, system_instruction: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.system_instruction = system_instruction
        self.memory: List[Dict[str, Any]] = []  # Memory should be overridden in the subclass

    # TO BE OVERRIDDEN
    def process_message(self, message: str) -> str:
        raise NotImplementedError("process_message method must be implemented in the subclass")

    def send_message(self, recipient: 'Agent', content: str):
        return recipient.process_message(content)

class OpenSourceAgent(Agent):
    def __init__(self, name: str, system_instruction: str,temperature: float, model_name: str = "", end_condition=False, tools=[], huggingface_endpoint_url=""):
        super().__init__(name, system_instruction)
        self.model_name = model_name
        self.huggingface_endpoint_url = huggingface_endpoint_url
        self.temperature = temperature  
        self.memory = []  # Initialize memory
        self.end_condition = end_condition

        if ('gpt' not in self.model_name):
            self.model_handler = self.create_model_handler(system_instruction)
            # Get the model configuration based on the provided model_name
            model_config = config["models"].get(model_name)
            if not model_config:
                raise ValueError(f"Model '{model_name}' not found in configuration")
        
        if not huggingface_endpoint_url and ('gpt' not in self.model_name):
            # Load local model
            self.my_model = Llama(
                model_path=model_config["path"],
                n_ctx=4096,
                temperature=self.temperature,
                # n_threads=8,
                # n_gpu_layers=35,
                verbose=False
            )
            self.stop_token_ids = ["<|EOT|>"]
    
    def create_model_handler(self, system_instruction: str = ""):
        if  "Qwen" in self.model_name:
            handler = QwenHandler(model_name=self.model_name, temperature=self.temperature)
        elif "Llama" in self.model_name:
            handler = LlamaHandler(model_name=self.model_name, temperature=self.temperature)

        self.memory.append({
             "role": "system",
             "content": system_instruction
         })

        # Additional configurations can be set here
        return handler

    def process_message(self, message: str) -> str:
        self.memory.append(message)
        messages = [
            {"role": "system", "content": self.system_instruction},
            message
        ]

        if self.huggingface_endpoint_url:
            # Send POST request to the Hugging Face endpoint
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer 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",  # Adjust if needed
            }
            data = {
            "messages": messages
            }

            response = requests.post(self.huggingface_endpoint_url, headers=headers, json=data)

            if response.status_code == 200:
                response_data = response.json()
                response_text = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                response_text = ''
        elif 'gpt' in self.model_name:
            api_response = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature = self.temperature,

                )
            response_text = api_response.choices[0].message.content

        else:
            formatted_prompt = self.model_handler._format_prompt(messages, function=None)
            # Use local model inference
            api_response = self.my_model(
                formatted_prompt,
                max_tokens=4096,
                stop=self.stop_token_ids,
                top_p=0.5,
                temperature=self.temperature,
                echo=False,
            )

            # Parse the model's response
            model_response_data = self.model_handler._parse_query_response_prompting_llmcpp(api_response)
            response_text = model_response_data["model_responses"]

        # Append the model's response to memory
        self.memory.append({
            "role": self.name,
            "content": response_text
        })

        return response_text

class UserAgent(Agent):
    def __init__(self, name: str, system_instruction: str):
        super().__init__(name, system_instruction)
        self.memory = []

    def process_message(self, message: str) -> str:
        # For the UserAgent, this method can be left empty or handle user-specific logic
        return

    def send_message(self, recipient: 'Agent', content: str):
        input_content = content
        message = input_content
        self.memory.append({
            "role": recipient,
            "content": input_content
        })
        return recipient.process_message(message)

class Mediator:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.agents["user"] = UserAgent("user", "")  # Add a user agent as a default agent

    def add_agent(self, agent: Agent):
        self.agents[agent.id] = agent

    def get_agent(self, agent_id: str) -> Agent:
        return self.agents.get(agent_id)

    def send(self, sender_id: str, recipient_id: str, content: str):
        sender = self.get_agent(sender_id)
        recipient = self.get_agent(recipient_id)

        content = {
            "role": sender.name,
            "content": content
        }

        if sender and recipient:
            return sender.send_message(recipient, content)
        else:
            raise ValueError("Invalid sender or recipient ID")

    def chat(self, sender_id: str, recipient_id: str, content: str, str_condition: str = "", max_turns: int = 4):
        sender = self.get_agent(sender_id)
        recipient = self.get_agent(recipient_id)
        res_recipient = content
        res_sender = " "
        counter = 0
        end = False
        last_response = res_recipient

        if max_turns == -1:
            res_recipient = self.send(sender_id, recipient_id, res_recipient)
            print(f'[{recipient.name}]', res_recipient)
            return res_recipient

        while counter < max_turns and not end:
            res_recipient = self.send(sender_id, recipient_id, res_recipient if counter == 0 else res_sender)
            print(f'[{recipient.name}]', res_recipient)
            if str_condition and str_condition in res_recipient:
                break

            if callable(getattr(recipient, 'end_condition', False)):
                end = recipient.end_condition()

            if end:
                break
            last_response = res_recipient

            res_sender = self.send(recipient_id, sender_id, res_recipient)
            print(f'[{sender.name}]', res_sender)
            if str_condition and str_condition in res_sender:
                break

            if callable(getattr(sender, 'end_condition', False)):
                end = sender.end_condition()

            counter += 1

        return last_response

    def math_problem_solving_architecture(self, assistant_id: str, assistant2_id: str, expert_id: str, user_input: str = "Write your message", str_condition: str = "", max_turns: int = -1):
        res_sender = self.send("user", assistant_id, user_input)
        print(f'[user]', user_input)
        print(f'[{self.get_agent(assistant_id).name}]', res_sender)
        res_sender2 = self.send(assistant_id, assistant2_id, res_sender)
        print(f'[{self.get_agent(assistant2_id).name}]', res_sender2)
        res = self.chat(assistant2_id, expert_id, content=res_sender2, str_condition=str_condition, max_turns=max_turns)
        return res