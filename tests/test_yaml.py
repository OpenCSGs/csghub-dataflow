import io
import sys
from pathlib import Path

# 将项目根目录添加到Python路径中，以确保模块导入正常
sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_server.logic.models import Recipe
from data_server.logic import config as server_config
from data_server.logic import constant as server_constant

def test_parse_yaml_from_string():
    """
    测试从字符串解析YAML配置
    """
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

    # `parse_yaml` 方法期望一个文件类对象。我们使用 `io.StringIO` 来模拟一个文件。
    # 该方法在出错时会访问文件的 .name 属性，所以我们也设置一下。
    string_io = io.StringIO(yaml_string)
    string_io.name = "from_string.yaml"

    try:
        # 调用我们想要测试的方法
        print("\n正在解析YAML字符串...")
        recipe_obj = Recipe.parse_yaml(string_io)
        print("成功将YAML字符串解析为Recipe对象。")

        print("\n--- 解析后的Recipe对象 (JSON格式) ---")
        # 使用 model_dump() 结合标准库 json 来序列化，以兼容旧版 Pydantic 并支持中文字符正确显示
        import json
        print(json.dumps(recipe_obj.model_dump(mode='json'), indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n在解析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parse_yaml_from_string()
