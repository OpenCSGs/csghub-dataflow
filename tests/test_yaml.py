import io
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_server.logic.models import Recipe
from data_server.logic import config as server_config
from data_server.logic import constant as server_constant

def test_parse_yaml_from_string():

    yaml_string = """
name: 202508模板
description: ''
type: data_refine
project_name: 202508041632任务
repo_id: z275748353/lambert_test
text_keys: text
np: '3'
open_tracer: 'true'
trace_num: '3'
process:
  - clean_copyright_mapper:
  - clean_ip_mapper:
  - generate_code_qa_pair_mapper:
      hf_model: AIWizards/Llama2-Chinese-7b-Chat
      prompt_template: test
"""

    print("--- 输入的YAML字符串 ---")
    print(yaml_string)


    string_io = io.StringIO(yaml_string)
    string_io.name = "from_string.yaml"

    try:

        print("\n正在解析YAML字符串...")
        recipe_obj = Recipe.parse_yaml(string_io)
        print("成功将YAML字符串解析为Recipe对象。")

        print("\n--- 解析后的Recipe对象 (JSON格式) ---")

        import json
        print(json.dumps(recipe_obj.model_dump(mode='json'), indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n在解析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parse_yaml_from_string()
