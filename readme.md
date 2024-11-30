
#### Quantized LLMs for Function Calling: Evaluating Agent-Augmented Qwen and LLama on the BFCL Non Live AST Benchmark

This thesis explores the effectiveness of quantized large language models (LLMs), specifically Qwen \parencite{yang_qwen2_2024} and LLama \parencite{dubey_llama_2024} with 1.5B, 3B, 7B, 8B parameters, in addressing function calling tasks. The models will be evaluated using the BFCL
Non Live AST Benchmark \parencite{fanjia_yan_berkeley_nodate}, both in their base version and with integrated agents \parencite{wu_autogen_2023}. As part of this study, a practical case will be presented to demonstrate the application of these models for the automatic creation of objects based on generic inputs (referred to as 'object calling input'), using a hierarchical structure with agents \parencite{patil_goex_2024}. The objective is to assess whether the integration of agents and inter-agent communication, through In Context Learning (ICL) \parencite{dong_survey_2024}, can enhance the performance of quantized models without the need for training and/or fine-tuning.

#### Get started:

- Add the quantize model in a folder in the same level of the thesis folder called models
- Update the `config.json` file, inside `/thesis/berkeley-function-call-leaderboard`
- Go in the folder `/thesis/berkeley-function-call-leaderboard` create and miniconda env and run `pip install -e .` 
- Then in order to run you have to open the file `bfcl/v002_generator_bfcl.py`

You can uncomment the model you want to run, you need to activate a server or an endpoint if avaible (assign it to the variable `huggingface_endpoint_url`), select if you want to run it with agent or without agent (`with_agent=True`).
In the file config.json you have to specify the path where the model is stored. You can donwload it from the huggingface website. 

After setting up the model in the file `bfcl/v002_generator_bfcl.py` go in your terminal, activate you miniconda env and run:

> the bfcl commands respect the same syntax coming from the BFCL Benchmark repository.

`bfcl generate --model {agent-network, agent-network-gpt} --test-cases {simple, parallel, multiple, parallel_multiple, java, javascript}` 

And it will create a folder data/agent-network/BFCL_v03_simple_result.json.

Remembre to set the .env file in the berkley-function-call-leaderboard folder with the OPENAI api key if you use the `agent-network-gpt` case.

#### Evaluate the results:

In order to evaluate the result just run: `bfcl evaluate` and it will create a folder score with the results of the evaluation.


#### Personalized Handler:
- Update the files `handler_map.py` and `model_metadata.py` with the new model (look at the others template and make sure that the key corresponds), I implemented compatibility with the Qwen model and the LLama model modifying the OpenAI Handler. Like presented below:

```python
api_inference_handler_map = {
    "agent-network-gpt": OpenAIHandler, 
    "agent-network": OpenAIHandler, 
    ...
```

```python
MODEL_METADATA_MAPPING = {
    "agent-network-gpt": [
        "",
        "",
        "",
        "",
    ],
    "agent-network": [
        "",
        "",
        "",
        "",
    ],
    ...
```



#### System Prompt:
The system prompt are inside the folder `/thesis/berkeley-function-call-leaderboard/system_prompt`

- `tester.md` is the system prompt for the tester agents (the one that create the test cases), inside the folder `tester_llama` and `tester_qwen` are the system prompt for the tester agents of the llama and qwen models. Using the corresponding stop tokens for the few shot prompting.
- `caller.md` is the system prompt for the caller agents (the one that generate the function call).
- `caller_feedback.md` is the system prompt for the caller agents (the one that generate the function call) but knowing it will have the feedback coming from the tester caller loop
- `validator.md` is the system prompt for the validator agents (the one that validate the function call).
- `validator_feedback.md` is the caller_feedback but knowing that it will have the feedback coming from the validator in the final loop


#### For local generation:

Use the file generator.py (make sure to specify the model handler and the quantize_models), `python generator.py all` the last argument is the test cases you want o make him complete that are: `[ "simple","parallel", "multiple", "parallel_multiple", "java", "javascript"]`. Note: make sure to be in the env that you have installed the project with `pip install -e .` and inside the folder `/thesis/berkeley-function-call-leaderboard`.


#### Quantize models:

models: Qwen_Qwen2.5-1.5B-Instruct, Qwen_Qwen2.5-3B-Instruct, all..

`data/result-quantize`: their result coming from generator.py
`data/score-quantize`: their score coming from `bfcl evaluate`



