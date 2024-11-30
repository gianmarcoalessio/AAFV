
import difflib
import re
from typing import List, Dict, Any, Optional
import json


def check_type(value: Any, expected_type: str) -> bool:
    """
    Checks if the value matches the expected type.

    Args:
        value (Any): The value to check.
        expected_type (str): The expected type as a string.

    Returns:
        bool: True if type matches, False otherwise.
    """
    type_mapping = {
        'string': str,
        'integer': int,
        'float': float,
        'boolean': bool,
        'dict': dict,
        'list': list
        # Add more mappings as needed
    }

    python_type = type_mapping.get(expected_type.lower())
    if not python_type:
        # Unknown type, consider as valid
        return True

    # Attempt to cast the value to the expected type
    try:
        if python_type == bool:
            # Special handling for boolean
            if isinstance(value, bool):
                return True
            if isinstance(value, str) and value.lower() in ['true', 'false']:
                return True
            return False
        elif python_type == int:
            int(value)
        elif python_type == float:
            float(value)
        elif python_type == str:
            str(value)
        elif python_type == dict:
            if isinstance(value, dict):
                return True
            return False
        elif python_type == list:
            if isinstance(value, list):
                return True
            return False
        return True
    except (ValueError, AttributeError):
        return False




def validate_parameters(provided_params: Dict[str, Any], parameter_schema: Dict[str, Any], similarity_threshold: float = 0.8) -> List[str]:
    """
    Validates provided parameters against the parameter schema of a function.

    Args:
        provided_params (Dict[str, Any]): The parameters extracted from the function call.
        parameter_schema (Dict[str, Any]): The schema defining expected parameters.
        similarity_threshold (float): The minimum similarity ratio to suggest parameter name corrections.

    Returns:
        List[str]: A list of difference messages.
    """
    differences = []

    required_params = parameter_schema.get('required', [])
    properties = parameter_schema.get('properties', {})

    # Check for missing required parameters
    for req in required_params:
        if req not in provided_params:
            differences.append(f'Missing required parameter: "{req}".')

    # Check for type mismatches and unexpected parameters
    for param, value in provided_params.items():
        if param in properties:
            expected_type = properties[param]['type']
            if not check_type(value, expected_type):
                provided_type = type(value).__name__
                differences.append(
                    f'Parameter "{param}" should be of type {expected_type}, but got type {provided_type}.'
                )
        else:
            # Attempt to find a similar parameter name
            expected_param_names = list(properties.keys())
            closest_matches = difflib.get_close_matches(param, expected_param_names, n=1, cutoff=similarity_threshold)
            if closest_matches:
                suggested = closest_matches[0]
                differences.append(
                    f'Unexpected parameter "{param}". Did you mean "{suggested}"?'
                )
            else:
                differences.append(f'Unexpected parameter "{param}".')

    return differences



def suggest_function_name(extracted_func: str, predefined_names: List[str], cutoff: float = 0.8) -> Optional[str]:
    """
    Suggests the closest matching function name from the predefined list.

    Args:
        extracted_func (str): The extracted function name.
        predefined_names (List[str]): The list of predefined function names.
        cutoff (float): The minimum similarity ratio to consider a suggestion.

    Returns:
        Optional[str]: The suggested function name if a close match is found, else None.
    """
    closest_matches = difflib.get_close_matches(extracted_func, predefined_names, n=1, cutoff=cutoff)
    return closest_matches[0] if closest_matches else None


def extract_and_analyze_single_function(
    input_str: str,
    predefined_functions: List[Dict[str, Any]],
    similarity_threshold: float = 0.8,
    parameter_similarity_threshold: float = 0.8,
    case_sensitive: bool = False
) -> Dict[str, Any]:
    predefined_names = [f['name'] for f in predefined_functions]
    if not case_sensitive:
        predefined_names_lower = [name.lower() for name in predefined_names]

    pattern = r'\[?([\w.]+)\((.*?)\)\]?'
    match = re.search(pattern, input_str.strip())

    if not match:
        return {
            "function_extracted": None,
            "parameters_extracted": {},
            "matched_function": None,
            "differences": ["Nessuna chiamata di funzione valida trovata nella stringa di input."]
        }

    extracted_func = match.group(1).strip()
    params_str = match.group(2).strip()

    func_for_matching = extracted_func if case_sensitive else extracted_func.lower()

    matched_func_def = None
    similarity = 0.0

    if case_sensitive:
        for predefined in predefined_functions:
            sim = difflib.SequenceMatcher(None, extracted_func, predefined['name']).ratio()
            if sim >= similarity_threshold and sim > similarity:
                matched_func_def = predefined
                similarity = sim
    else:
        for predefined, name_lower in zip(predefined_functions, predefined_names_lower):
            sim = difflib.SequenceMatcher(None, func_for_matching, name_lower).ratio()
            if sim >= similarity_threshold and sim > similarity:
                matched_func_def = predefined
                similarity = sim

    differences = []

    if matched_func_def:
        exact_match = (similarity == 1.0)
        if not exact_match:
            differences.append(
                f'Il nome della funzione "{extracted_func}" non corrisponde a nessuna funzione predefinita. Forse intendevi "{matched_func_def["name"]}"?'
            )

        params = {}
        if params_str:
            param_pattern = r'(\w+)\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|([^,]+))'
            param_matches = re.finditer(param_pattern, params_str)
            for p_match in param_matches:
                key = p_match.group(1)
                value = p_match.group(2) or p_match.group(3) or p_match.group(4)
                params[key] = value.strip()

        parameter_differences = validate_parameters(
            params,
            matched_func_def.get('parameters', {}),
            similarity_threshold=parameter_similarity_threshold
        )
        differences.extend(parameter_differences)
    else:
        suggested_name = suggest_function_name(
            extracted_func,
            predefined_names if case_sensitive else predefined_names_lower,
            cutoff=similarity_threshold
        )
        if suggested_name:
            if not case_sensitive:
                index = predefined_names_lower.index(suggested_name)
                suggested_name = predefined_names[index]
            differences.append(
                f'La funzione "{extracted_func}" non è definita. Forse intendevi "{suggested_name}"?'
            )
        else:
            differences.append(
                f'La funzione "{extracted_func}" non è definita e nessuna funzione simile è stata trovata.'
            )

    matched_function = matched_func_def if matched_func_def else None

    return {
        "function_extracted": extracted_func,
        "parameters_extracted": params if params_str else {},
        "matched_function": matched_function,
        "differences": differences
    }

def estrai_model_result_raw_and_function(file_path, start=None, end=None):
    """
    Estrae i campi 'model_result_raw' e 'function' all'interno di 'prompt' dal file JSON,
    e ritorna una lista di dizionari contenenti entrambi i campi.

    :param file_path: Percorso al file JSON.
    :param start: Indice iniziale (opzionale, base 1).
    :param end: Indice finale (opzionale, base 1).
    :return: Lista di dizionari con le chiavi 'model_result_raw' e 'function'.
    """
    # Lista per memorizzare i dizionari con 'model_result_raw' e 'function'
    risultati = []

    # Contatore di linee
    line_counter = 0

    # Apri e carica il file JSON
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line_counter += 1  # Incrementa il contatore di linee

            # Opzionale: Salta le prime linee se start è specificato
            if start is not None and line_counter < start:
                continue

            # Opzionale: Termina se raggiungi l'indice end
            if end is not None and line_counter > end:
                break

            if line.strip():
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Errore nel parsing della linea {line_counter}: {e}")
                    continue  # Salta la linea corrente in caso di errore

                # Estrai 'model_result_raw'
                model_result_raw = item.get('model_result_raw', '')

                # Estrai 'function' all'interno di 'prompt'
                prompt = item.get('prompt', {})
                function_value = prompt.get('function', [])

                # Crea un dizionario con i valori estratti
                risultato = {
                    'model_result_raw': model_result_raw,
                    'function': function_value
                }

                # Aggiungi il dizionario alla lista dei risultati
                risultati.append(risultato)

    return risultati