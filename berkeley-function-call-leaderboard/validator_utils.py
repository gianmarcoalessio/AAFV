import json
from tabulate import tabulate
import os
from utils import leggi_file_markdown,create_agent,Mediator,add_agents_to_mediator,send_and_print,validate_and_print
from validator import ast_checker


def is_java(test_category):
    return "java" in test_category


def is_js(test_category):
    return "javascript" in test_category

def estrai_e_stampa_dati_con_validator(file_path, start=None, end=None, language='Python'):
    """
    Estrae i dati dal file JSON, esegue la validazione su 'model_result_raw' utilizzando 'ast_checker',
    stampa una tabella con gli elementi specificati e ritorna una lista di dizionari contenenti
    'model_result_raw', 'error', 'validator_result' e 'possible_answer'.

    :param file_path: Percorso al file JSON.
    :param start: Indice iniziale (opzionale).
    :param end: Indice finale (opzionale).
    :param language: Linguaggio da utilizzare per l'ast_checker (default: 'python').
    :return: Lista di dizionari con le chiavi 'model_result_raw', 'error', 'validator_result' e 'possible_answer'.
    """
    # Lista per memorizzare tutti i dati
    tutti_i_dati = []

    # Contatore di linee
    line_counter = 0

    # Apri e carica il file JSON
    with open(file_path, 'r') as file:
        for line in file:
            line_counter += 1  # Incrementa il contatore di linee
            # if line_counter == 1:
            #     continue  # Salta la prima linea
            if line.strip():
                item = json.loads(line)
                model_result_raw = item.get('model_result_raw', '')
                error = item.get('error', '')
                possible_answer = item.get('possible_answer', '')

                # Presumo che 'test_entry' sia 'item["prompt"]'
                test_entry = item.get('prompt', {})
                function = test_entry.get('function', [])
                TEST_CATEGORY = item.get('test_category', '')
                MODEL_NAME_BFCL = item.get('model_name', '')

                res_caller = model_result_raw

                # Esegui 'ast_checker'
                validator_result = ast_checker(function, res_caller, language, TEST_CATEGORY, MODEL_NAME_BFCL)

                # Aggiungi i dati alla lista
                tutti_i_dati.append({
                    'model_result_raw': model_result_raw,
                    'possible_answer': possible_answer,
                    'error': error,
                    'validator_result': validator_result,
                })

    # Se start e end non sono specificati, mostra tutti i dati
    dati_selezionati = tutti_i_dati[start:end]

    # Prepara i dati per la tabella
    data_list = []
    for item in dati_selezionati:
        data_list.append([
            item['model_result_raw'],
            item['possible_answer'],
            item['error'],
            item['validator_result'],
        ])

    # Stampa la tabella
    headers = ["model_result_raw","possible_answer", "error", "validator_result"]
    print(tabulate(data_list, headers=headers, tablefmt="grid"))

    # Ritorna la lista di dizionari
    return dati_selezionati

def estrai_e_conta_validita_dataset(file_path, language='Python', skip_header=True):
    """
    Estrae i dati dal file JSON, esegue la validazione su 'model_result_raw' utilizzando 'ast_checker',
    conta quante validator_result['valid'] sono True e quanti sono False, conta specifici messaggi di errore,
    raccoglie tutti gli errori non specificati, e calcola il totale delle righe elaborate. 
    Stampa i risultati in tabelle separate con conteggi e percentuali.

    :param file_path: Percorso al file JSON.
    :param language: Linguaggio da utilizzare per l'ast_checker (default: 'Python').
    :param skip_header: Booleano per decidere se saltare la prima linea (default: True).
    :return: Un dizionario con i conteggi di validità, messaggi di errore specifici, errori non specificati e totale righe.
    """
    # Inizializza i contatori
    total_lines = 0          # Totale righe elaborate (escluse header e righe vuote)
    total_processed = 0      # Righe con 'valid' correttamente identificato (True/False)
    invalid_valid = 0        # Righe con 'valid' non booleano
    valid_true = 0
    valid_false = 0

    # Definisci le sottostringhe da cercare nei messaggi di errore
    error_substrings = {
        'missing_comma': 'Perhaps you forgot a comma?',
        'invalid_value': 'Invalid value',
        'invalid_decimal_literal': 'invalid decimal literal',
        'nested_type_checking_failed': 'Nested type checking failed for parameter',
        'positional_after_keyword': 'positional argument follows keyword argument',
        'unterminated_string_literal': 'unterminated string literal',
        'expected_type_array': 'Expected type array, got str',
        'not_found_in_model_output': 'not found in model output',
        'not_marked_as_optional': 'not marked as optional'
    }

    # Inizializza un dizionario per memorizzare i conteggi degli errori specifici
    error_counts = {key: 0 for key in error_substrings}

    # Inizializza un dizionario per memorizzare gli errori non specificati
    unmatched_errors = {}

    # Funzione per calcolare le percentuali
    def calculate_percentage(count, total):
        return (count / total * 100) if total > 0 else 0

    # Apri e carica il file JSON
    with open(file_path, 'r') as file:
        for line_number, line in enumerate(file, start=1):
            if skip_header and line_number == 1:
                continue  # Salta la prima linea (presumibilmente un'intestazione)
            if line.strip():
                total_lines += 1  # Incrementa il totale delle righe elaborate
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"[Linea {line_number}] Errore nel parsing del JSON: {e}")
                    continue

                # Estrai i campi principali
                model_result_raw = item.get('model_result_raw', '')
                error = item.get('error', [])

                # Presumo che 'test_entry' sia 'item["prompt"]'
                test_entry = item.get('prompt', {})
                function = test_entry.get('function', [])
                TEST_CATEGORY = item.get('test_category', '')
                MODEL_NAME_BFCL = item.get('model_name', '')

                res_caller = model_result_raw

                # Esegui 'ast_checker'
                try:
                    validator_result = ast_checker(function, res_caller, language, TEST_CATEGORY, MODEL_NAME_BFCL)
                except Exception as e:
                    print(f"[Linea {line_number}] Errore nell'esecuzione di ast_checker: {e}")
                    continue

                # Estrai il valore di 'valid' da validator_result
                valid = validator_result.get('valid')

                if isinstance(valid, bool):
                    total_processed += 1  # Incrementa solo se 'valid' è booleano
                    if valid is True:
                        valid_true += 1
                    elif valid is False:
                        valid_false += 1
                else:
                    invalid_valid += 1
                    print(f"[Linea {line_number}] Valore 'valid' non booleano: {valid}")

                # Conta i messaggi di errore specifici
                if isinstance(error, list):
                    for err_msg in error:
                        if not isinstance(err_msg, str):
                            print(f"[Linea {line_number}] Messaggio di errore non stringa: {err_msg}")
                            continue
                        matched = False
                        for key, substring in error_substrings.items():
                            if substring in err_msg:
                                error_counts[key] += 1
                                matched = True
                        if not matched:
                            if err_msg in unmatched_errors:
                                unmatched_errors[err_msg] += 1
                            else:
                                unmatched_errors[err_msg] = 1
                else:
                    print(f"[Linea {line_number}] Il campo 'error' non è una lista: {error}")

    # Calcola le percentuali
    def calculate_percentage(count, total):
        return (count / total * 100) if total > 0 else 0

    # Prepara i dati per la tabella dei conteggi principali
    data_list_main = [
        ["validator: valid=True", valid_true, f"{calculate_percentage(valid_true, total_processed):.2f}%"],
        ["validator: valid=False", valid_false, f"{calculate_percentage(valid_false, total_processed):.2f}%"]
    ]

    # Aggiungi il totale delle righe e le righe non valide
    data_list_main.append(["Totale Righe Elaborate", total_lines, f"{calculate_percentage(total_lines, total_lines):.2f}%"])
    data_list_main.append(["Righe con 'valid' Non Valido", invalid_valid, f"{calculate_percentage(invalid_valid, total_lines):.2f}%"])

    # Aggiungi i conteggi degli errori specifici alla lista dei dati principali
    for key, count in error_counts.items():
        percentage = calculate_percentage(count, total_processed)
        data_list_main.append([key, count, f"{percentage:.2f}%"])


    # Prepara i dati per la tabella degli errori non specificati
    if unmatched_errors:
        data_list_unmatched = [["Errore", "Conteggio", "Percentuale"]]
        for err_msg, count in unmatched_errors.items():
            percentage = calculate_percentage(count, total_processed)
            data_list_unmatched.append([err_msg, count, f"{percentage:.2f}%"])
    else:
        data_list_unmatched = [["Nessun errore non specificato rilevato.", "-", "-"]]

    # Stampa la tabella dei conteggi principali
    print("\n--- Conteggio Validità ed Errori Specifici ---")
    headers_main = ["Parametro", "Conteggio", "Percentuale"]
    print(tabulate(data_list_main, headers=headers_main, tablefmt="grid"))

    # Stampa la tabella degli errori non specificati
    print("\n--- Errori Non Specificati ---")
    if unmatched_errors:
        print(tabulate(data_list_unmatched[1:], headers=data_list_unmatched[0], tablefmt="grid"))
    else:
        print(tabulate(data_list_unmatched, headers=data_list_unmatched[0], tablefmt="grid"))

    # Ritorna il dizionario con tutti i conteggi
    return {
        'total_lines': total_lines,
        'total_processed': total_processed,
        'invalid_valid': invalid_valid,
        'valid_true': valid_true,
        'valid_false': valid_false,
        **error_counts,
        'unmatched_errors': unmatched_errors
    }


def analisi_score_completo(file_paths_languages, skip_header=True):
    """
    Estrae i dati dai file JSON forniti in 'file_paths_languages', esegue la validazione su 'model_result_raw' utilizzando 'ast_checker',
    raccoglie tutti gli errori e calcola il totale delle righe elaborate per ciascun file.
    Stampa i risultati in tre tabelle:
    - Una tabella per il totale delle righe per file e linguaggio.
    - Una tabella che conta le occorrenze di specifiche sottostringhe negli errori, inclusi gli errori non corrispondenti.
    - Una tabella degli errori con file, errori, conteggio e percentuale (considerando solo il primo elemento dell'array 'error').

    :param file_paths_languages: Lista di tuple (file_path, language).
    :param skip_header: Booleano per decidere se saltare la prima linea di ciascun file (default: True).
    :return: Nessun valore di ritorno.
    """

    # Inizializza liste per memorizzare i dati
    total_lines_data = []
    all_data_errors = []
    substring_counts = {}
    unmatched_errors_count = 0  # Contatore per errori non corrispondenti

    # Definisci le sottostringhe da cercare nei messaggi di errore
    substrings_to_search = [
        ('The value provided for the parameter is invalid because it is not one of the expected values.', 'Invalid value for parameter'),
        ('The function provided is not found in the model output.', 'Could not find a matching function'),
        ('In the function provided, a required parameter is missing.', 'Missing required parameter'),
        ('The parameter provided is marked as optional and is not in the question.', 'Optional parameter'),
        ('The parameter provided is not expected in the function.', 'Unexpected parameter:'),
        ('The parameter provided is expected to be an array but is a string.', 'Expected type array, got str.'),
        ('The parameter provided is expected to be a string but is an integer.', 'Expected type string, got int.'),
        ('The parameter provided is expected to be a float but is a string.', 'Expected type float, got str.'),
        ('The parameter provided is expected to be a dictionary but is a string.', 'Expected type dict, got str.'),
        ('The parameter provided is expected to be an ArrayList but is a string.', "Expected type ArrayList, got str."),
        ("The parameter provided is not closed with a ']' character.", "'[' was never closed"),
        ("Nested type checking failed for parameter. Expected outer type array with inner type float.", "Expected outer type array with inner type"),
        ('Invalid syntax. Failed to decode AST. - Error parsing java the source code','Error parsing java the source code'),
        ('Invalid syntax. Failed to decode AST. - Error js parsing the source code.','Error js parsing the source code.'),
        ('The number of functions is not correct','Wrong number of functions.')
    ]

    # Crea una mappatura da sottostringa a tipologia di errore
    substring_to_typology = {substring: error_typology for error_typology, substring in substrings_to_search}

    # Inizializza il conteggio totale delle righe per il calcolo delle percentuali
    total_lines_all_files = 0

    for file_path, language in file_paths_languages:
        # Estrae il nome del file senza estensione
        filename = os.path.basename(file_path)
        file_description = os.path.splitext(filename)[0]

        # Inizializza i contatori per questo file
        total_lines = 0  # Totale righe elaborate (escluse header e righe vuote)
        error_counts = {}

        # Apri e carica il file JSON
        with open(file_path, 'r') as file:
            for line_number, line in enumerate(file, start=1):
                if skip_header and line_number == 1:
                    continue  # Salta la prima linea (presumibilmente un'intestazione)
                if line.strip():
                    total_lines += 1  # Incrementa il totale delle righe elaborate
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as e:
                        print(f"[{file_description} - Linea {line_number}] Errore nel parsing del JSON: {e}")
                        continue

                    # Estrai i campi principali
                    model_result_raw = item.get('model_result_raw', '')
                    error = item.get('error', [])

                    # Presumo che 'test_entry' sia 'item["prompt"]'
                    test_entry = item.get('prompt', {})
                    function = test_entry.get('function', [])
                    TEST_CATEGORY = item.get('test_category', '')
                    MODEL_NAME_BFCL = item.get('model_name', '')

                    res_caller = model_result_raw

                    # Esegui 'ast_checker' con il linguaggio specificato
                    try:
                        validator_result = ast_checker(function, res_caller, language, TEST_CATEGORY, MODEL_NAME_BFCL)
                    except Exception as e:
                        print(f"[{file_description} - Linea {line_number}] Errore nell'esecuzione di ast_checker: {e}")
                        continue

                    # Processa solo il primo elemento dell'array 'error'
                    if isinstance(error, list) and error:
                        first_error = error[0]
                        if isinstance(first_error, str):
                            err_msg = first_error
                            if err_msg in error_counts:
                                error_counts[err_msg] += 1
                            else:
                                error_counts[err_msg] = 1

                            # Cerca le sottostringhe nell'errore
                            matched = False
                            for substring in substring_to_typology:
                                if substring in err_msg:
                                    matched = True
                                    if substring in substring_counts:
                                        substring_counts[substring]['count'] += 1
                                    else:
                                        substring_counts[substring] = {'error_typology': substring_to_typology[substring], 'count': 1}
                                    break  # Una volta trovata una corrispondenza, interrompi il ciclo
                            if not matched:
                                unmatched_errors_count += 1
                        else:
                            print(f"[{file_description} - Linea {line_number}] Il primo elemento di 'error' non è una stringa: {first_error}")
                    else:
                        print(f"[{file_description} - Linea {line_number}] Il campo 'error' non è una lista o è vuoto: {error}")

        # Aggiungi i dati del totale delle righe per questo file
        total_lines_data.append([file_description, language, total_lines])

        # Aggiorna il conteggio totale delle righe
        total_lines_all_files += total_lines

        # Calcola le percentuali e prepara i dati per la tabella degli errori per questo file
        if error_counts:
            for err_msg, count in error_counts.items():
                percentage = (count / total_lines * 100) if total_lines > 0 else 0
                all_data_errors.append([file_description, err_msg, count, f"{percentage:.2f}%"])
        else:
            all_data_errors.append([file_description, "Nessun errore rilevato.", "-", "-"])

    # Stampa la tabella del totale delle righe
    print("\n--- Totale delle Righe per File e Linguaggio ---")
    headers_total_lines = ["File", "Linguaggio", "Totale Righe"]
    print(tabulate(total_lines_data, headers=headers_total_lines, tablefmt="grid"))

    # Stampa la tabella delle sottostringhe negli errori con descrizione
    substring_data = []
    for error_typology, substring in substrings_to_search:
        count = substring_counts.get(substring, {}).get('count', 0)
        percentage = (count / total_lines_all_files * 100) if total_lines_all_files > 0 else 0
        substring_data.append([error_typology, substring, count, f"{percentage:.2f}%"])

    # Aggiungi la riga per gli errori non corrispondenti
    if unmatched_errors_count > 0:
        percentage = (unmatched_errors_count / total_lines_all_files * 100) if total_lines_all_files > 0 else 0
        substring_data.append(["Other Errors", "Errors not matched by any substring", unmatched_errors_count, f"{percentage:.2f}%"])

    print("\n--- Conteggio delle Sottostringhe negli Errori ---")
    headers_substring = ["Tipologia di Errore", "Sottostringa", "Conteggio", "Percentuale"]
    print(tabulate(substring_data, headers=headers_substring, tablefmt="grid"))

    # Stampa la tabella degli errori per tutti i file
    print("\n--- Errori (considerando solo il primo elemento di 'error') ---")
    headers_errors = ["File", "Errore", "Conteggio", "Percentuale"]
    # Ordina all_data_errors per file e conteggio decrescente
    all_data_errors_sorted = sorted(all_data_errors, key=lambda x: (x[0], -int(x[2]) if x[2] != '-' else 0))
    print(tabulate(all_data_errors_sorted, headers=headers_errors, tablefmt="grid"))