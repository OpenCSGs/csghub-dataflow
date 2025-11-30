import json
from concurrent.futures import ProcessPoolExecutor
import os, uuid

exclude_fields_config=['buildin', 'name', 'template_id', 'description', 'type', 'job_source', 'dslText', 'is_run', 'task_run_time', 'pic_base64']
executor = None


def greate_task_uid():

    return str(uuid.uuid4())

def read_jsonl_to_list(filepath):
    data_list = [] 
    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file: 
            data = json.loads(line) 
            data_list.append(data)
    return data_list

def data_format(datalist, type):
    op_type = 'others'
    if type == 'Mapper':
        op_type = 'replace'
    elif type == 'Deduplicator':
        op_type = 'deduplicate'
    elif type == 'Filter':
        op_type = 'remove'
    
    result_dict = {"before": [], "op_type": op_type, "after": []}

    if not datalist:
        return result_dict

    if type == 'Filter' or type not in ['Mapper', 'Deduplicator']:
        result_dict["before"] = datalist
        result_dict["after"] = []
    elif type == 'Mapper':
        original_texts = []
        processed_texts = []
        for item in datalist:
            if "original text" in item:
                original_texts.append(item["original text"])
            if "processed_text" in item:
                processed_texts.append(item["processed_text"])
        result_dict["before"] = original_texts
        result_dict["after"] = processed_texts
    elif type == 'Deduplicator':
        dup1_texts = []
        dup2_texts = []
        for item in datalist:
            if "dup1" in item:
                dup1_texts.append(item["dup1"])
            if "dup2" in item:
                dup2_texts.append(item["dup2"])
        result_dict["before"] = dup1_texts
        result_dict["after"] = dup2_texts
    return result_dict

def setup_executor():
    global executor
    if executor is None:
        max_workers = int(os.getenv('MAX_WORKERS', 99))
        executor = ProcessPoolExecutor(max_workers=max_workers)
    return executor
    