/*
 Navicat Premium Dump SQL

 Source Server         : data-flow
 Source Server Type    : PostgreSQL
 Source Server Version : 150003 (150003)
 Source Host           : net-power.9free.com.cn:18119
 Source Catalog        : data_flow
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 150003 (150003)
 File Encoding         : 65001

 Date: 13/08/2025 17:11:19
*/


-- ----------------------------
-- Table structure for algo_templates
-- ----------------------------
DROP TABLE IF EXISTS "public"."algo_templates";
CREATE TABLE "public"."algo_templates" (
  "id" int8 NOT NULL DEFAULT nextval('algo_templates_copy_id_seq'::regclass),
  "user_id" varchar(255) COLLATE "pg_catalog"."default",
  "name" varchar(255) COLLATE "pg_catalog"."default",
  "description" varchar(255) COLLATE "pg_catalog"."default",
  "type" varchar(255) COLLATE "pg_catalog"."default",
  "buildin" bool,
  "project_name" varchar(255) COLLATE "pg_catalog"."default",
  "dataset_path" varchar(255) COLLATE "pg_catalog"."default",
  "exprot_path" varchar(255) COLLATE "pg_catalog"."default",
  "np" varchar(255) COLLATE "pg_catalog"."default",
  "open_tracer" bool,
  "trace_num" varchar(255) COLLATE "pg_catalog"."default",
  "backend_yaml" text COLLATE "pg_catalog"."default",
  "dslText" text COLLATE "pg_catalog"."default",
  "created_at" timestamp(6),
  "updated_at" timestamp(6)
)
;
COMMENT ON COLUMN "public"."algo_templates"."user_id" IS '用户id';
COMMENT ON COLUMN "public"."algo_templates"."name" IS '算法模块名称';
COMMENT ON COLUMN "public"."algo_templates"."description" IS '算法模版描述';
COMMENT ON COLUMN "public"."algo_templates"."type" IS '算法模版类型';
COMMENT ON COLUMN "public"."algo_templates"."buildin" IS '是否为内置模版';
COMMENT ON COLUMN "public"."algo_templates"."project_name" IS '项目名称';
COMMENT ON COLUMN "public"."algo_templates"."dataset_path" IS '输入数据集路径';
COMMENT ON COLUMN "public"."algo_templates"."exprot_path" IS '输出数据集路径';
COMMENT ON COLUMN "public"."algo_templates"."np" IS '并行处理的进程数，控制CPU使用和处理速度';
COMMENT ON COLUMN "public"."algo_templates"."open_tracer" IS '是否开启操作追踪，用于调试和性能分析';
COMMENT ON COLUMN "public"."algo_templates"."trace_num" IS '追踪的样本数量，每个操作追踪多少个样本的处理过程';
COMMENT ON COLUMN "public"."algo_templates"."backend_yaml" IS '后端yaml格式';
COMMENT ON COLUMN "public"."algo_templates"."dslText" IS '前端yaml格式';
COMMENT ON COLUMN "public"."algo_templates"."created_at" IS '创建时间';
COMMENT ON COLUMN "public"."algo_templates"."updated_at" IS '修改时间';

-- ----------------------------
-- Records of algo_templates
-- ----------------------------
INSERT INTO "public"."algo_templates" VALUES (9999, 'e8e543a8-b58c-4626-8b07-28b467527dae', '数据处理-基础', '该配置文件用于定义数据流处理的各个步骤，包括字符过滤、重复数据去除和中文转换等操作。', 'data_refine', 't', 'dataflow-demo-process', '/path/to/your/dataset', '/path/to/your/dataset.jsonl', '3', 'f', '3', 'name: 数据处理-基础
description: 该配置文件用于定义数据流处理的各个步骤，包括字符过滤、重复数据去除和中文转换等操作。
type: data_refine
buildin: false
project_name: dataflow-demo-process
dataset_path: /path/to/your/dataset
exprot_path: /path/to/your/dataset.jsonl
np: 3
open_tracer: true
trace_num: 3
process:
  - chinese_convert_mapper:
      mode: t2s
  - clean_email_mapper:
  - alphanumeric_filter:
      tokenization: false
      max_ratio: 999999
      min_ratio: 0.1
  - character_repetition_filter:
      rep_len: 10
      min_ratio: 0
      max_ratio: 0.6
  - flagged_words_filter:
      lang: zh
      tokenization: true
      max_ratio: 0.01
      use_words_aug: true
  - text_length_filter:
      min_len: 10
      max_len: 999999
  - document_deduplicator:
      lowercase: true
      ignore_non_character: true
', 'name: 数据处理-基础
description: 该配置文件用于定义数据流处理的各个步骤，包括字符过滤、重复数据去除和中文转换等操作。
type: data_refine
process:
  chinese_convert_mapper:
    id: node_1754966838520_364
    operator_id: ''14''
    operator_type: Mapper
    operator_name: chinese_convert_mapper
    display_name: 汉字转换
    icon: files/operator/26269c88-3453-4c8b-8333-ec6c9c939109.png
    position:
      x: -110.33337402343739
      ''y'': 268
    configs:
      - id: 121
        operator_id: 14
        config_name: mode
        config_type: select
        select_options:
          - value: ''1''
            label: 简体转繁体
          - value: ''2''
            label: 繁体转简体
          - value: ''3''
            label: 简体转台湾正体
          - value: ''4''
            label: 台湾正体转简体
          - value: ''5''
            label: 简体转香港繁体
          - value: ''6''
            label: 香港繁体转简体
          - value: ''7''
            label: 简体转台湾正体（带标点符号）
          - value: ''8''
            label: 台湾正体转简体（带标点符号）
          - value: ''9''
            label: 繁体转台湾正体
          - value: ''10''
            label: 台湾正体转繁体
          - value: ''11''
            label: 香港繁体转繁体
          - value: ''12''
            label: 繁体转香港繁体
          - value: ''13''
            label: 繁体转日文汉字
          - value: ''14''
            label: 日文汉字转繁体
        default_value: ''2''
        is_required: true
        is_spinner: false
        final_value: ''2''
        display_name: 转换模式
  clean_email_mapper:
    id: node_1754966850804_6
    operator_id: ''3''
    operator_type: Mapper
    operator_name: clean_email_mapper
    display_name: 邮箱后缀清理
    icon: files/operator/eb0a7ba0-f54e-4328-bc6b-dafb0ac7e3e6.png
    position:
      x: 133.99995930989593
      ''y'': 269
    configs: []
  alphanumeric_filter:
    id: node_1754966879202_955
    operator_id: ''15''
    operator_type: Filter
    operator_name: alphanumeric_filter
    display_name: 字母/数字占比过滤
    icon: files/operator/7f317dc9-ba84-4660-b50f-f96b39049dba.png
    position:
      x: 383.92218153211786
      ''y'': 268.5
    configs:
      - id: 2
        operator_id: 15
        config_name: tokenization
        config_type: checkbox
        default_value: ''false''
        is_required: false
        is_spinner: false
        final_value: false
        display_name: 分词
      - id: 3
        operator_id: 15
        config_name: max_ratio
        config_type: number
        default_value: ''999999''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 999999
        display_name: 最小比例
      - id: 4
        operator_id: 15
        config_name: min_ratio
        config_type: number
        default_value: ''0.1''
        is_required: true
        is_spinner: true
        spinner_step: ''0.01''
        final_value: 0.1
        display_name: 最大比例
  character_repetition_filter:
    id: node_1754966895266_477
    operator_id: ''2''
    operator_type: Filter
    operator_name: character_repetition_filter
    display_name: 字符级重复率范围过滤
    icon: files/operator/cc49d862-693b-4107-9353-3b40593b1fd8.png
    position:
      x: 628.2999135851586
      ''y'': 268.2544335663814
    configs:
      - id: 5
        operator_id: 2
        config_name: rep_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 10
        display_name: 重复长度
      - id: 6
        operator_id: 2
        config_name: min_ratio
        config_type: slider
        default_value: ''0''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 0
        display_name: 最小比例
      - id: 7
        operator_id: 2
        config_name: max_ratio
        config_type: slider
        default_value: ''0.6''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 0.6
        display_name: 最大比例
  flagged_words_filter:
    id: node_1754966903156_935
    operator_id: ''1''
    operator_type: Filter
    operator_name: flagged_words_filter
    display_name: 标记词比例过滤
    icon: files/operator/7053eed0-b6a8-4a8a-9387-e1a0413fbce7.png
    position:
      x: 630.6519850704641
      ''y'': 459.4313163377312
    configs:
      - id: 8
        operator_id: 1
        config_name: lang
        config_type: select
        select_options:
          - value: ''15''
            label: 英文
          - value: ''16''
            label: 中文
        default_value: ''16''
        is_required: true
        is_spinner: false
        final_value: ''16''
        display_name: 语言
      - id: 9
        operator_id: 1
        config_name: tokenization
        config_type: checkbox
        default_value: ''true''
        is_required: false
        is_spinner: false
        final_value: true
        display_name: 分词
      - id: 10
        operator_id: 1
        config_name: max_ratio
        config_type: slider
        default_value: ''0.01''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 0.01
        display_name: 最大比例
      - id: 11
        operator_id: 1
        config_name: use_words_aug
        config_type: checkbox
        default_value: ''true''
        is_required: true
        is_spinner: false
        final_value: true
        display_name: 词汇增强
  text_length_filter:
    id: node_1754966911062_215
    operator_id: ''13''
    operator_type: Filter
    operator_name: text_length_filter
    display_name: 文本长度范围过滤
    icon: files/operator/3ffa0e42-974a-4b14-ab08-9cb259f83512.png
    position:
      x: 389.50550366947664
      ''y'': 456.2787562855962
    configs:
      - id: 12
        operator_id: 13
        config_name: min_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 10
        display_name: 最小长度
      - id: 13
        operator_id: 13
        config_name: max_len
        config_type: number
        default_value: ''999999''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 999999
        display_name: 最大长度
  document_deduplicator:
    id: node_1754966921771_101
    operator_id: ''12''
    operator_type: Deduplicator
    operator_name: document_deduplicator
    display_name: 文档去重（MD5）
    icon: files/operator/205a63c8-fa19-4542-add1-1b0744b95977.png
    position:
      x: 133.97784605764633
      ''y'': 457.52232487238814
    configs:
      - id: 14
        operator_id: 12
        config_name: lowercase
        config_type: checkbox
        default_value: ''true''
        is_required: true
        is_spinner: false
        final_value: true
        display_name: 小写
      - id: 15
        operator_id: 12
        config_name: ignore_non_character
        config_type: checkbox
        default_value: ''true''
        is_required: true
        is_spinner: false
        final_value: true
        display_name: 忽略非字符
edges:
  - source: node_1754966838520_364
    target: node_1754966850804_6
  - source: node_1754966850804_6
    target: node_1754966879202_955
  - source: node_1754966879202_955
    target: node_1754966895266_477
  - source: node_1754966895266_477
    target: node_1754966903156_935
  - source: node_1754966903156_935
    target: node_1754966911062_215
  - source: node_1754966911062_215
    target: node_1754966921771_101
', '2025-08-12 10:53:36.565306', '2025-08-12 17:23:56.403399');
INSERT INTO "public"."algo_templates" VALUES (10000, 'e8e543a8-b58c-4626-8b07-28b467527dae', '数据生成', '该模版用于数据增强，旨在扩展用户的提示数据，以帮助模型更好地理解任务。', 'data_refine', 't', 'dataflow-demo-process', '/path/to/your/dataset', '/path/to/your/dataset.jsonl', '3', 'f', '3', 'name: 数据生成
description: 该模版用于数据增强，旨在扩展用户的提示数据，以帮助模型更好地理解任务。
type: data_refine
buildin: false
project_name: dataflow-demo-process
dataset_path: /path/to/your/dataset
exprot_path: /path/to/your/dataset.jsonl
np: 3
open_tracer: true
trace_num: 3
process:
  - extract_qa_mapper:
      hf_model: alibaba-pai/pai-qwen1_5-7b-doc2qa
', 'name: 数据生成
description: 该模版用于数据增强，旨在扩展用户的提示数据，以帮助模型更好地理解任务。
type: data_refine
process:
  extract_qa_mapper:
    id: node_1754968895500_152
    operator_id: ''11''
    operator_type: Mapper
    operator_name: extract_qa_mapper
    display_name: 问答对提取
    icon: files/operator/2bc92637-2ca6-45d8-ab15-d54a6afe6706.png
    position:
      x: 385.6666259765625
      ''y'': 268.3333282470703
    configs:
      - id: 16
        operator_id: 11
        config_name: hf_model
        config_type: select
        select_options:
          - value: ''18''
            label: alibaba-pai/pai-qwen1_5-7b-doc2qa
        default_value: ''18''
        is_required: true
        is_spinner: false
        final_value: ''18''
        display_name: 模型名称
edges: []
', '2025-08-12 11:21:38.314545', '2025-08-12 11:21:38.314545');
INSERT INTO "public"."algo_templates" VALUES (10001, 'e8e543a8-b58c-4626-8b07-28b467527dae', '数据增强', '该模版用于数据增强，旨在扩展用户的提示数据，以帮助模型更好地理解任务。', 'data_enhancement', 't', 'dataflow-demo-process', '/path/to/your/dataset', '/path/to/your/dataset.jsonl', '3', 'f', '3', 'name: 数据增强
description: 该模版用于数据增强，旨在扩展用户的提示数据，以帮助模型更好地理解任务。
type: data_enhancement
buildin: false
project_name: dataflow-demo-process
dataset_path: /path/to/your/dataset
exprot_path: /path/to/your/dataset.jsonl
np: 3
open_tracer: true
trace_num: 3
process:
  - optimize_instruction_mapper:
      hf_model: alibaba-pai/Qwen2-7B-Instruct-Refine
', 'name: 数据增强
description: 该模版用于数据增强，旨在扩展用户的提示数据，以帮助模型更好地理解任务。
type: data_enhancement
process:
  optimize_instruction_mapper:
    id: node_1754968821594_841
    operator_id: ''21''
    operator_type: Mapper
    operator_name: optimize_instruction_mapper
    display_name: 优化Instruction
    icon: files/operator/fd013e56-4b3d-4bed-9005-b9b28d6548cc.png
    position:
      x: 261.6666259765625
      ''y'': 341
    configs:
      - id: 34
        operator_id: 21
        config_name: hf_model
        config_type: select
        select_options:
          - value: ''24''
            label: alibaba-pai/Qwen2-7B-Instruct-Refine
        default_value: ''24''
        is_required: true
        is_spinner: false
        final_value: ''24''
        display_name: 模型名称
edges: []
', '2025-08-12 11:20:29.007592', '2025-08-12 11:20:29.007592');
INSERT INTO "public"."algo_templates" VALUES (10002, 'e8e543a8-b58c-4626-8b07-28b467527dae', '数据处理-高阶', '该配置文件用于定义数据处理流程，包含多个处理机制，如清理电子邮件、链接、字符规范化、文本过滤和去重等操作。用户可根据需求调整参数，以提高数据质量和处理效率，确保最终数据集的准确性和一致性。', 'data_refine', 't', 'dataflow-demo-process', '/path/to/your/dataset', '/path/to/your/dataset.jsonl', '3', 'f', '3', 'name: 数据处理-高阶
description: 该配置文件用于定义数据处理流程，包含多个处理机制，如清理电子邮件、链接、字符规范化、文本过滤和去重等操作。用户可根据需求调整参数，以提高数据质量和处理效率，确保最终数据集的准确性和一致性。
type: data_refine
buildin: false
project_name: dataflow-demo-process
dataset_path: /path/to/your/dataset
exprot_path: /path/to/your/dataset.jsonl
np: 3
open_tracer: true
trace_num: 3
process:
  - clean_email_mapper:
  - clean_links_mapper:
  - fix_unicode_mapper:
      normalization: NFC
  - punctuation_normalization_mapper:
  - whitespace_normalization_mapper:
  - alphanumeric_filter:
      tokenization: false
      max_ratio: 999999
      min_ratio: 0.1
  - average_line_length_filter:
      min_len: 10
      max_len: 1200
  - character_repetition_filter:
      rep_len: 10
      min_ratio: 0
      max_ratio: 0.6
  - flagged_words_filter:
      lang: zh
      tokenization: true
      max_ratio: 0.01
      use_words_aug: true
  - language_id_score_filter:
      lang: zh
      min_score: 0.8
  - maximum_line_length_filter:
      min_len: 10
      max_len: 7328
  - perplexity_filter:
      lang: en
      max_ppl: 8000
  - special_characters_filter:
      min_ratio: 0
      max_ratio: 1
  - text_length_filter:
      min_len: 10
      max_len: 999999
  - words_num_filter:
      lang: en
      tokenization: true
      min_num: 20
      max_num: 999999
  - word_repetition_filter:
      lang: en
      tokenization: true
      rep_len: 10
      min_ratio: 0
      max_ratio: 0.5
  - document_simhash_deduplicator:
      tokenization: character
      window_size: 4
      lowercase: true
      ignore_pattern: ''''
      num_blocks: 10
      hamming_distance: 8
', 'name: 数据处理-高阶
description: >-
  该配置文件用于定义数据处理流程，包含多个处理机制，如清理电子邮件、链接、字符规范化、文本过滤和去重等操作。用户可根据需求调整参数，以提高数据质量和处理效率，确保最终数据集的准确性和一致性。
type: data_refine
process:
  clean_email_mapper:
    id: node_1754968371047_181
    operator_id: ''3''
    operator_type: Mapper
    operator_name: clean_email_mapper
    display_name: 邮箱后缀清理
    icon: files/operator/eb0a7ba0-f54e-4328-bc6b-dafb0ac7e3e6.png
    position:
      x: -205.5233740234371
      ''y'': 125.00000000000011
    configs: []
  clean_links_mapper:
    id: node_1754968375415_285
    operator_id: ''5''
    operator_type: Mapper
    operator_name: clean_links_mapper
    display_name: 链接地址清理
    icon: files/operator/5b10a3d2-7548-4921-a1c9-9acb7196f0dd.png
    position:
      x: 61.33329264322941
      ''y'': 126.22222222222234
    configs: []
  fix_unicode_mapper:
    id: node_1754968377786_33
    operator_id: ''7''
    operator_type: Mapper
    operator_name: fix_unicode_mapper
    display_name: Unicode错误修正
    icon: files/operator/9930ff2d-167b-426d-8294-901f5dbf0342.png
    position:
      x: 328.07884819878484
      ''y'': 130.33333333333343
    configs:
      - id: 17
        operator_id: 7
        config_name: normalization
        config_type: select
        select_options:
          - value: ''19''
            label: 组合规范化形式
          - value: ''20''
            label: 兼容性组合规范化形式
          - value: ''21''
            label: 分解规范化形式
          - value: ''22''
            label: 兼容性分解规范化形式
        default_value: ''19''
        is_required: true
        is_spinner: false
        final_value: ''19''
        display_name: 标准化
  punctuation_normalization_mapper:
    id: node_1754968512917_694
    operator_id: ''22''
    operator_type: Mapper
    operator_name: punctuation_normalization_mapper
    display_name: Unicode标点规范化
    icon: files/operator/111cb13a-b085-49d8-9684-397c7ffa4b08.png
    position:
      x: 595.0266259765623
      ''y'': 130.5200000000003
    configs: []
  whitespace_normalization_mapper:
    id: node_1754968382097_701
    operator_id: ''40''
    operator_type: Mapper
    operator_name: whitespace_normalization_mapper
    display_name: 空白规范化
    icon: files/operator/b0aed94b-84b3-416a-b91b-444cca15ea02.png
    position:
      x: 853.1124501226102
      ''y'': 134.5731084353675
    configs: []
  alphanumeric_filter:
    id: node_1754968389622_893
    operator_id: ''15''
    operator_type: Filter
    operator_name: alphanumeric_filter
    display_name: 字母/数字占比过滤
    icon: files/operator/7f317dc9-ba84-4660-b50f-f96b39049dba.png
    position:
      x: 1135.6710111937816
      ''y'': 134.40240666517798
    configs:
      - id: 2
        operator_id: 15
        config_name: tokenization
        config_type: checkbox
        default_value: ''false''
        is_required: false
        is_spinner: false
        final_value: false
        display_name: 分词
      - id: 3
        operator_id: 15
        config_name: max_ratio
        config_type: number
        default_value: ''999999''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 999999
        display_name: 最小比例
      - id: 4
        operator_id: 15
        config_name: min_ratio
        config_type: number
        default_value: ''0.1''
        is_required: true
        is_spinner: true
        spinner_step: ''0.01''
        final_value: 0.1
        display_name: 最大比例
  average_line_length_filter:
    id: node_1754968394726_69
    operator_id: ''41''
    operator_type: Filter
    operator_name: average_line_length_filter
    display_name: 平均行长度范围过滤
    icon: files/operator/21e83be6-d67e-4e1e-ba2c-4ae1c10b7d18.png
    position:
      x: 1373.6572201085091
      ''y'': 134.16654511011188
    configs:
      - id: 53
        operator_id: 41
        config_name: min_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 10
        display_name: 最小长度
      - id: 54
        operator_id: 41
        config_name: max_len
        config_type: number
        default_value: ''1200''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 1200
        display_name: 最大长度
  character_repetition_filter:
    id: node_1754968409509_51
    operator_id: ''2''
    operator_type: Filter
    operator_name: character_repetition_filter
    display_name: 字符级重复率范围过滤
    icon: files/operator/cc49d862-693b-4107-9353-3b40593b1fd8.png
    position:
      x: 1373.3209979785536
      ''y'': 338.39218441025673
    configs:
      - id: 5
        operator_id: 2
        config_name: rep_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 10
        display_name: 重复长度
      - id: 6
        operator_id: 2
        config_name: min_ratio
        config_type: slider
        default_value: ''0''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 0
        display_name: 最小比例
      - id: 7
        operator_id: 2
        config_name: max_ratio
        config_type: slider
        default_value: ''0.6''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 0.6
        display_name: 最大比例
  flagged_words_filter:
    id: node_1754968412370_11
    operator_id: ''1''
    operator_type: Filter
    operator_name: flagged_words_filter
    display_name: 标记词比例过滤
    icon: files/operator/7053eed0-b6a8-4a8a-9387-e1a0413fbce7.png
    position:
      x: 1129.9077638684714
      ''y'': 339.61329432424486
    configs:
      - id: 8
        operator_id: 1
        config_name: lang
        config_type: select
        select_options:
          - value: ''15''
            label: 英文
          - value: ''16''
            label: 中文
        default_value: ''16''
        is_required: true
        is_spinner: false
        final_value: ''16''
        display_name: 语言
      - id: 9
        operator_id: 1
        config_name: tokenization
        config_type: checkbox
        default_value: ''true''
        is_required: false
        is_spinner: false
        final_value: true
        display_name: 分词
      - id: 10
        operator_id: 1
        config_name: max_ratio
        config_type: slider
        default_value: ''0.01''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 0.01
        display_name: 最大比例
      - id: 11
        operator_id: 1
        config_name: use_words_aug
        config_type: checkbox
        default_value: ''true''
        is_required: true
        is_spinner: false
        final_value: true
        display_name: 词汇增强
  language_id_score_filter:
    id: node_1754968415885_135
    operator_id: ''42''
    operator_type: Filter
    operator_name: language_id_score_filter
    display_name: 特定语言置信度过滤
    icon: files/operator/fe9da7e9-ff19-4c92-b1cc-6456ab855441.png
    position:
      x: 858.2621756223643
      ''y'': 343.01503341760514
    configs:
      - id: 55
        operator_id: 42
        config_name: lang
        config_type: select
        select_options:
          - value: ''15''
            label: 英文
          - value: ''16''
            label: 中文
          - value: ''25''
            label: 法语
          - value: ''26''
            label: 德语
        default_value: ''16''
        is_required: true
        is_spinner: false
        final_value: ''16''
        display_name: 语言
      - id: 56
        operator_id: 42
        config_name: min_score
        config_type: slider
        default_value: ''0.8''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 0.8
        display_name: 最小分数
  maximum_line_length_filter:
    id: node_1754968418480_222
    operator_id: ''43''
    operator_type: Filter
    operator_name: maximum_line_length_filter
    display_name: 最大行长度范围过滤
    icon: files/operator/a8b4ff5e-2d12-40c5-b483-c6f4c8492ef5.png
    position:
      x: 598.9688984049084
      ''y'': 341.24995124096233
    configs:
      - id: 1
        operator_id: 43
        config_name: min_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 10
        display_name: 最小长度
      - id: 57
        operator_id: 43
        config_name: max_len
        config_type: number
        default_value: ''7328''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 7328
        display_name: 最大长度
  perplexity_filter:
    id: node_1754968422689_201
    operator_id: ''44''
    operator_type: Filter
    operator_name: perplexity_filter
    display_name: 困惑度范围过滤
    icon: files/operator/4b7e5905-74fe-42ba-97a5-b873e21421fa.png
    position:
      x: 331.0400634536948
      ''y'': 342.4489830479768
    configs:
      - id: 58
        operator_id: 44
        config_name: lang
        config_type: select
        select_options:
          - value: ''15''
            label: 英文
          - value: ''16''
            label: 中文
        default_value: ''15''
        is_required: true
        is_spinner: false
        final_value: ''15''
        display_name: 语言
      - id: 59
        operator_id: 44
        config_name: max_ppl
        config_type: number
        default_value: ''8000''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 8000
        display_name: 最大困惑度
  special_characters_filter:
    id: node_1754968429009_728
    operator_id: ''45''
    operator_type: Filter
    operator_name: special_characters_filter
    display_name: 特殊字符比例过滤
    icon: files/operator/ac509abf-55ba-47c7-8b5e-d5080dfbe3d9.png
    position:
      x: 67.68026500167855
      ''y'': 344.0068126612566
    configs:
      - id: 60
        operator_id: 45
        config_name: min_ratio
        config_type: slider
        default_value: ''0''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 0
        display_name: 最小比例
      - id: 61
        operator_id: 45
        config_name: max_ratio
        config_type: slider
        default_value: ''1''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 1
        display_name: 最大比例
  text_length_filter:
    id: node_1754968433508_624
    operator_id: ''13''
    operator_type: Filter
    operator_name: text_length_filter
    display_name: 文本长度范围过滤
    icon: files/operator/3ffa0e42-974a-4b14-ab08-9cb259f83512.png
    position:
      x: -202.98062002876208
      ''y'': 345.0150734342167
    configs:
      - id: 12
        operator_id: 13
        config_name: min_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 10
        display_name: 最小长度
      - id: 13
        operator_id: 13
        config_name: max_len
        config_type: number
        default_value: ''999999''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 999999
        display_name: 最大长度
  words_num_filter:
    id: node_1754968441638_368
    operator_id: ''24''
    operator_type: Filter
    operator_name: words_num_filter
    display_name: 单词数量范围过滤
    icon: files/operator/89e8db71-801e-4241-a637-1e28d55ee53b.png
    position:
      x: -200.73515162543254
      ''y'': 567.1768507831089
    configs:
      - id: 85
        operator_id: 24
        config_name: lang
        config_type: select
        select_options:
          - value: ''15''
            label: 英文
          - value: ''16''
            label: 中文
        default_value: ''15''
        is_required: true
        is_spinner: false
        final_value: ''15''
        display_name: 语言
      - id: 86
        operator_id: 24
        config_name: tokenization
        config_type: checkbox
        default_value: ''true''
        is_required: false
        is_spinner: false
        final_value: true
        display_name: 分词
      - id: 87
        operator_id: 24
        config_name: min_num
        config_type: number
        default_value: ''20''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 20
        display_name: 最小数量
      - id: 88
        operator_id: 24
        config_name: max_num
        config_type: number
        default_value: ''999999''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 999999
        display_name: 最大数量
  word_repetition_filter:
    id: node_1754968447223_158
    operator_id: ''18''
    operator_type: Filter
    operator_name: word_repetition_filter
    display_name: 词级重复率范围过滤
    icon: files/operator/8c65e9aa-898e-4d25-aac2-9741623e7bb6.png
    position:
      x: 73.91708968139449
      ''y'': 564.9133286679211
    configs:
      - id: 80
        operator_id: 18
        config_name: lang
        config_type: select
        select_options:
          - value: ''15''
            label: 英文
          - value: ''16''
            label: 中文
        default_value: ''15''
        is_required: true
        is_spinner: false
        final_value: ''15''
        display_name: 语言
      - id: 81
        operator_id: 18
        config_name: tokenization
        config_type: checkbox
        default_value: ''true''
        is_required: false
        is_spinner: false
        final_value: true
        display_name: 分词
      - id: 82
        operator_id: 18
        config_name: rep_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 10
        display_name: 重复长度
      - id: 83
        operator_id: 18
        config_name: min_ratio
        config_type: slider
        default_value: ''0''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 0
        display_name: 最小比例
      - id: 84
        operator_id: 18
        config_name: max_ratio
        config_type: slider
        default_value: ''0.5''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: true
        is_spinner: false
        final_value: 0.5
        display_name: 最大比例
  document_simhash_deduplicator:
    id: node_1754968450834_22
    operator_id: ''19''
    operator_type: Deduplicator
    operator_name: document_simhash_deduplicator
    display_name: 文档去重（SimHash）
    icon: files/operator/57593071-d5c2-4277-90af-99c524b7ea8c.png
    position:
      x: 337.5138069090609
      ''y'': 561.9920226074149
    configs:
      - id: 98
        operator_id: 19
        config_name: tokenization
        config_type: select
        select_options:
          - value: ''30''
            label: 空格
          - value: ''31''
            label: 标点符号
          - value: ''32''
            label: 字符
        default_value: ''32''
        is_required: false
        is_spinner: false
        final_value: ''32''
        display_name: 分词
      - id: 99
        operator_id: 19
        config_name: window_size
        config_type: number
        default_value: ''4''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 4
        display_name: 窗口大小
      - id: 100
        operator_id: 19
        config_name: lowercase
        config_type: checkbox
        default_value: ''true''
        is_required: true
        is_spinner: false
        final_value: true
        display_name: 小写
      - id: 101
        operator_id: 19
        config_name: ignore_pattern
        config_type: input
        is_required: false
        is_spinner: false
        final_value: ''''
        display_name: 忽略模式
      - id: 102
        operator_id: 19
        config_name: num_blocks
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 10
        display_name: 块数量
      - id: 103
        operator_id: 19
        config_name: hamming_distance
        config_type: number
        default_value: ''8''
        min_value: ''0''
        is_required: true
        is_spinner: true
        spinner_step: ''1''
        final_value: 8
        display_name: 汉明距离
edges:
  - source: node_1754968371047_181
    target: node_1754968375415_285
  - source: node_1754968375415_285
    target: node_1754968377786_33
  - source: node_1754968382097_701
    target: node_1754968389622_893
  - source: node_1754968389622_893
    target: node_1754968394726_69
  - source: node_1754968394726_69
    target: node_1754968409509_51
  - source: node_1754968409509_51
    target: node_1754968412370_11
  - source: node_1754968412370_11
    target: node_1754968415885_135
  - source: node_1754968415885_135
    target: node_1754968418480_222
  - source: node_1754968418480_222
    target: node_1754968422689_201
  - source: node_1754968422689_201
    target: node_1754968429009_728
  - source: node_1754968429009_728
    target: node_1754968433508_624
  - source: node_1754968433508_624
    target: node_1754968441638_368
  - source: node_1754968441638_368
    target: node_1754968447223_158
  - source: node_1754968447223_158
    target: node_1754968450834_22
  - source: node_1754968377786_33
    target: node_1754968512917_694
  - source: node_1754968512917_694
    target: node_1754968382097_701
', '2025-08-12 11:17:09.866443', '2025-08-12 17:30:01.807169');

-- ----------------------------
-- Indexes structure for table algo_templates
-- ----------------------------
CREATE INDEX "ix_algo_templates_copy_id" ON "public"."algo_templates" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table algo_templates
-- ----------------------------
ALTER TABLE "public"."algo_templates" ADD CONSTRAINT "algo_templates_copy_pkey" PRIMARY KEY ("id");
