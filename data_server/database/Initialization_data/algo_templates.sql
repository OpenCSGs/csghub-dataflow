/*
 Navicat Premium Dump SQL

 Source Server         : pg-local-docker
 Source Server Type    : PostgreSQL
 Source Server Version : 150010 (150010)
 Source Host           : localhost:5433
 Source Catalog        : data_flow
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 150010 (150010)
 File Encoding         : 65001

 Date: 21/08/2025 11:01:42
*/


-- ----------------------------
-- Table structure for algo_templates
-- ----------------------------
DROP TABLE IF EXISTS "public"."algo_templates";
-- Drop and recreate sequence to ensure clean state
DROP SEQUENCE IF EXISTS algo_templates_id_seq;
CREATE SEQUENCE algo_templates_id_seq;

CREATE TABLE "public"."algo_templates" (
  "id" int8 NOT NULL DEFAULT nextval('algo_templates_id_seq'),
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
INSERT INTO "public"."algo_templates" VALUES (1, '54', '数据处理-基础', '该配置文件用于定义数据流处理的各个步骤，包括字符过滤、重复数据去除和中文转换等操作。', 'data_refine', 't', 'dataflow-demo-process', '/path/to/your/dataset', '/path/to/your/dataset.jsonl', '1', 'f', '3', 'name: 数据处理-基础
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
      min_ratio: 0.1
      max_ratio: 999999
  - character_repetition_filter:
      rep_len: 10
      min_ratio: 0
      max_ratio: 0.5
  - flagged_words_filter:
      lang: en
      tokenization: true
      max_ratio: 0.01
      use_words_aug: false
  - text_length_filter:
      min_len: 10
      max_len: 136028
  - document_deduplicator:
      lowercase: true
      ignore_non_character: true
', 'name: 数据处理-基础
description: 该配置文件用于定义数据流处理的各个步骤，包括字符过滤、重复数据去除和中文转换等操作。
type: data_refine
process:
  chinese_convert_mapper:
    id: node_1755742725315_552
    operator_id: ''14''
    operator_type: Mapper
    operator_name: chinese_convert_mapper
    display_name: 汉字转换
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6MzRBNTlGMDE0MzQxN0Q0RjgxNEFBNTIxNTE4Nzg3RUIiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6QUMwMkMwRUZDRjQ0RTM0Q0E5NjcwMDk4ODhENjc0Q0EiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+xm6m7wAADiJJREFUeJztnXmQXUUVxn/vJZ1ksnUSsoEiW0GzBkQSwLDvoCWbAgooIouAIggoKKAkFFAmhhIhhEAhJEQppAgKxADGEFBZNBIQAg0Ji2whC5nOJENmehb/OH159y2zv3ffLO+rmnr39r3dt+e7fU+fPn1Od4pHd6MEGAGkSlFwGVAPbCp2of27mH9r4HDgYGA3YEeE9N6I9wELLAOeAhbThReS6kSLHwCcCXwbOJDe07I7ilpgPjAbeLqjmTtCfBo4H/gZ8Pk27nVAU0cr000xEBjcxj3PAFcB/2hvoe0lfk/gbmDvnPQG5JNbBDwPvA6sau/DexD6A9sCuwIHAUcDu+fc0wzcA1wCbGirwPYQfxEwHRgUS/sYmBEetLqtAnopvohwcyYifiO8DXwDWNpa5nQr11LAzcCtZEj/FLgW2A74FX2XdIAXgXOAnRBZH2E7YAlwbGuZWyI+BdyBfDYRliEiZyryAioQvAucBJxKRsQMAf4U0guiJeJvAM6NnT8I7A+82eVq9l48AEwC3gnnCvgD0ifkoRDxXwd+GjufB5wGbC5aFXsvLPBlYEU4HwDcD4zLvTGX+K2AO8no5o8B3wEaS1LN3omPEPm+JpxviWiEWcglfjqZkee7SI9dIb3jWIFIiWgscxwiST5DnPj9gG/Gzs8G1peydr0cfwNuj51PR+Q+kE38z2PH94eMFXQNV5NRubcBzoguRMRvD3wlHDcB1yVWtd6NamQsFOHi6CAi/kwyHeoCZOhfQXEwi8y4Zy9gD8gQf3LsxjnJ1alPoBoZTEU4AYT4sYS3ANQBf0myVn0Ej8SODwMhflIs8T/AxiRr1EewOHY8CUilgZ1jiS8nW58+g4+AteF4MLB1muxJjYotpnRYGTveLg0MiyVUJ1uXPoW1sePhabInOCrm3tKhJnY8rLWJkAqKi6w56K66d7QKo/QM4ERkvrKhSMWmQ1mrgNHIF1usifV+SEe42Hp3Rls3dwUlJR64NPwuRAgqhitIA6IZ7A/8FyFqYBHKBRG1xwCnE7OrlAKlJh7gcetdq/OPHYVROo1Mtk+x3n1S5LJnIW4sJUWpiW8gtEaj9Ahan1xvL5oRkfBLoMkovUVI6zLCSxxSjLLaQhItPhIvaYpDfBrxZ9wI6HBeFOIDEvGM64lazWZExk9DbNw1rd/ePdETia8HqoB9kA7bl7c6nUMSoqYQ+gF11rvqeGLoBwbQtnqYIjaN1hNRLuI3A8oofQHi6r0CeMl6txTAKD2WlskfGPLfhbgS5naGaWCT9W5TKGs4xdX1i4KyEG+9c0bpU4CZseRmo/RjwCXWu5WtkD8I2Gi9u8soPRjpYD2h07XeVRul+xuljwGarHdPABuM0qORL6WYHXGnURbijdIDgReAdcAWITkFfBXY3Si9N+LqPaxAdg8MMEofiLigrLbefeZsFdKnIsESGKUXIPr+80ZpjXwxZW/95epctfXuHWSUmIttgXOsd3XhPGqldUBN0LXXI6Pizda7zUbpXY3S5xql5yNBAgfHyjsOeM4ofan1ziGdc9lRLuKbjNKjrXf/RqbCcj//nWLHKevdOiTsZbBRehsk/GdrYJpRejEyczabMJ/ZAmYYpc/N7dDLhXJ1rgApo/QW1rvFRunJyGz8hHBtbjALNALOKH0lQuooxM0w6lD3aaHsZgoPhLYsVuW7inLq8c1A2ig9xnr3LHAIYpg60Hr3NDAS6Rw9cBawLxLcVmhIXw/8HRlU/ZDCERlLgJuM0omYBNpCOVp8vDU2AxilxwHrrXfzwvmYcH1AIGo/YArS+Y5DRq4vhb/ngKetd6+GvKPJdiICCSI40nrnjdIj6Qb+oEkS3w/pHOMayABEHWwChhulo0vNOb8TkCi7lYhImo/EId1tvasNZenQeZ5O9v/VCJwWSB9HNyAdkiW+FhhvlD4NsVr+D1hkvVsTWvVQ8klpsN5tMkrfi2g7IB1vP+RlLDFKv4Z4OEcq4v45ZTxpvXsjjIq7BemQIPGBwFsReR3hLaP0bCSeqh9QZb37GDIjTqN0P8Tn8M8hzxeQiJVVoawmpK+qDmLmyJxHzw2/7TFFJIakO9d/5ZxvD9wE/MR6twFYZ5TexSj9LcQQVgeMtN49gnS+62J5xwM/tt41AY3WuwZENR0Vu2c1sMAorehGpEOCxBulh1nvZgK3Fbh8uVG6fyBvPhL+c3yQ2amg8y9B4oni1sgbjNJ7BD0f4KicchcGvX14Uf+ZIqDUxEcT0yBio8p69wPytY7R1rsGo/R5gAlpUb5NQG3oPJcjYS7xifO5AEbpKvKj7B4Iv5uRPqYxVqfa8FeHaFmRppWImbnUxDcAVUbpQYiuPdwoPQq4jOy4oKVhCm9qOF8FPBTk/PjwN8woPcJ6twi4PpZ3T6P0SYiWMzKW/jrweJD740IZAxBihyCDqfGIVtWAGOmGhmslN6SVunNdhazqcSMyR1qNhKSMRTyr5iHD/VeQsPyxId89wcp4DTJwagb+CtxmlP4C+VF088j3grstfEXTgDFIa78TCag7Ahms9Qt1vAIZdF0NTKYEy6TkotTEjwZeBX5LZuJiFiJzG4DlQdvZBglejjAv/D4MPBGOqxGVswaJLTIEl2fEVDw+lr8W+KNRun/Os1cjLfwFJB41jXS6CunMZyKh8kX1iiiEUhM/CHDWu7eCiBmIxPpHcjSSq7fE8iyx3r1ilB6GDJiie6NVNOqRiZOTEZk+i/zZqOnWu4+DmFlORn8fHMqpBj4MaZH/6EDr3Sqj9GrkSygpSk181Jri59ESJP0COccCX4vdc3/4rSJfBWxCiEsH8/DdRukzEVUzwmrr3S+iZyBfSaE66QLpUDznqFZRLiNZCqgJFshfx9KrgQfb0LvrkA77CKP0qWSLKIChRunvh+ONdNMJ/bJVKthYfgTsEkt+wHq3lpb17hTwqfXuA0QDup9sTQbki7rdKH1ZmHddTwKio6MoB/FpZIQ6GlmCJY77YvcUyldrvaszSh9AfkvPxXSj9FTrnQ9miLiuXnYkTXzkAdCE+D6OiF1bDjwbBkJxPToFYL1bHTSg85GlqKpi9yxFXsSynOddbZReYJTewXq3Bvgk1KHsLyBJ4tOAD+SdjcTWxnFfMBlEnWEKaLberbHerTVKTwheCLNy8i0DjrbevRzKzO0bjgVeNkpfAQwOL3ANoh2V7QUkaRauR4b+U5GBShyNwEPhOI3I8Q0ARmmDrCByVYEy5wDfCwOl0UENPYv8WN3BiAX0fKP0PcDD1rtXoouhk488GhJ5GUkSX4O4cuSSDvCM9c6G2aEa612tUfpIZFGL08le8wtk8PUicGEgfRwyga6td3ON0hORKcBc7IB0ylOM0k8BTyIWU2u9ey/ck4jNPkniqxDylwJfyrkWjU43I/acx8jWzSM0Ix5ks5H1wIxR+hUyZA00Sg+03l0cvpRca2WEFHBo+ANYY5R+NZRb10KeoiJJGV8VfGVuKXDtn+G3Hmndh8SuOWRe9XpgovXuPCQedwLyMuMttInQYVvvjkbsP+3BmPDMaOG7ktvukyS+2Sg91Ho3h+ylAT8FXgtydhRiPNsJOAXpGCcCB1jvrrHeLQ0WyzHILNT75I9MG4PoAXFmup3W191xyJJWDyMj6A0kwEvSXgZDkNHkGcBrIW2x9W51mBMFGG69e5NYsLNRemgwLYMMhmqtd4+GtJHk29Aj8j+x3l1olJ6OrJwxHvlCapCXsQ5RMT+23tWEZ11UzH+4JSRNfGPQPl4PNppDgXuD7h7NiTaGwVVLqEdk+QmIyFlLfucLQvAIo3QT8Lb17q2WCjRKVxmlR1rv1pPQFGE5/GpSRumx1ruFwMIgYiJ7eXuwGZHjlwNXIo6rhYiHjA/PFjHXkW6Bcjk0NYdWHRHTURUuhaiU3WoCuyMot+WuM4OVqM4rkf6iR0aGlNNptbOoQgi/PJwPo5sEG3QE5W7xnUEK6WA30I0iPDqKUrf4/sj8ZxS8WzQYpacANwf7fTHhilxeQSQhao4ySt+BGKqKYYCqR6btTgImGaXfI9tE3BVsQlbFLjlKTfwsZC+R80pQdi3iS1NseGQUW1KUlHjr3QXABaV8Rk9FT+xceyqyGnmabK+pbhGm0ksRDx11abIXYRhFBaXCmNhxdZrsZfl2poJSYcfY8co02Qs470EFpcD2ZDzXqoFVaWTOMfI334uKuCkFDosdPwvSudYg3rMgkwwnJFunPoETY8eLIKNOxpfZPiup2vQRbEVm0r2Z4MYSEX8fGXFzIPkhixV0HpeS0eGfQdzUPyP+Q+D3sZvjoS4VdB6fI3vkPiM6iI9cbyTT6g8je4ecCjqH35AZlL5EJlY3i/jXyQ6FvI1MNHUFHcd3yWwB0owESX82d5Brq7kWiFzZRiLhim1tIltBPvZFnKMi/I6cXY5zid+A+CpGfioTkc+jYsNpPyYge4JEDfY1YtsQRShknXwG2SA2+iwOJzsUsoKWcSiyLk5kl/kE8U7LC99sySx8J9k7XO6LdA6HF6+OvQr9gWsQ59sRIa0acSFcUShDa/b4aUjLj3xexiNuzXNoe7P0voSDEbPLFDL6+kch/fmWMrU1ETITeWvRFpkpJOpiJeIu3VcHWoOQfbmXAE8hNq4IzyESotUdhtq7S/1WyEs4vsC1t5ENGZ8D3gA+QPxeusUyg0XAEGQSY1syu9QfQn5k4qeIB/NNtGN3iPYSH+EoROWc3JFMvRz1iMnlOmTVqXaho8RHmIzs93oy+RHSfQUrgXvDX7sJj9BZ4iMoZAu1g5BVOrZHVtYYSg/1aSyATYjo/BARpcuQLeTe6Eqh/wexxAzhRCF4CwAAAABJRU5ErkJggg==
    position:
      x: 123.6666259765625
      ''y'': 199.3333282470703
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
        is_required: false
        is_spinner: false
        final_value: ''2''
        display_name: 转换模式
  clean_email_mapper:
    id: node_1755742731920_356
    operator_id: ''3''
    operator_type: Mapper
    operator_name: clean_email_mapper
    display_name: 邮箱后缀清理
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6MUNCRTkwQThGNzMyNDk0NEI4ODc5M0I5RjkwRjE0NUYiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6NTZCN0NBM0U4QzBCRDc0Nzk5RTU0REJERkNEODg1NDciIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+rNuRTAAACEBJREFUeJzt3XuMnFUZx/FPp1gQKbdgVAI2RMl6QVrReCkEpGiLtAqNCligRhNbVFDwAgoqEQKaABIR8RY1QVFQLm2IUorVIAr2IkFRqaDEW2gkqUhQDL24/vG80/fMsrM7sztnZmf2/SaTPe/tnLO/97znPZfnPO+MoTvm6wB7YKj47Y99OhHpFOJxbMVmPIxtk41wt0lcO4R3YCFei1mTzUyf8F/cgztxA/4ykUhmTKDEL8LH8YaJJDhg/A9rcKm4GS3TTol/Ba7B0aMcG8Yf8Qc8Kh7NQWEG9sPB4ik/JDlWwwnF74f4EP7USqStCF/Dhfj0iPO3i8ftevwYj7WS4ABwoHjql2GB0AcWF9vniQI6JuNVNXvj+0VCdbbja7jcBOu3AWIIF+B05Q0gNHs3nmp2Ya3ZATwfd2kU/R7Mw1kq0Ymq9V14HX6d7D9Z1AZNW3fNhN8Ha4XIRB1+KY7B7yeX14Fko2jZXZvsm49bsPtoF4wm/EzcJF6msBPL8Uns6FROB5Cn8QF8VBRUos6/brSTZx5wxsEj912E9xThYVFXfbvj2Rxc7hU34Y3F9stFw2NTetLIEj9PlOw6l2hyxyrG5HMaq50rNDZDG4SfgS+LqoZ4sV6cM3cDzrnKF+6e+EJ6MBV+iXg7E4/KClG/V0yMbVgperfwFrymfjAV/oIkfC0eyp61wWc9vpts79K4LvzLNJb2y7uTr2nBZcpWzmLRP9ol/GnJiauxpXv5GngexN1FeDecSin8kuTE9NGo6AzXJ+GFhPD7KTtLO8SAV0VnWZuEj8ZuNcwVTUl4AP/pdq6mAX8Ww+XwHBxSw4uSEzZ3O0fTiAeT8FANz012/LXLmZlO/C0Jv6CG2cmOJ7ucmelEqu3smsZOVNVTzUf67pw11kRIRUYq4XtEJXyPqITvEZOxJGuVA8RY0NwupNUJfoebRacnG7mFH8JtODRzOp3mY1gqpvGykLOq2VfMvveb6PA8YcpyYK4Ecgr/QY2ds34k29RnTuGPyRh3tzg2V8Q5he/30k5GO/+cwp+rnOjtV5bnijin8L8Q87j9Kv4i/ChX5Lk7UBv1p/iLNM4adZycwp9T/O038eui76n8HzpOTuGvUj6q/SJ+WtJ/ic/kSiin8A/jzfhKsb0Rrzd1xV+oFH2VMADYkCuxnMLXV0OsVIq/wdQUf6FYSECIfmIRzmaWnlP4mUl4pTCIZeqJ30x0MurTzWHhMz1T/OHmp3eFsUTPSrfH46eS+D0Tnd5MhKTir9cb8XsqOr2bgeql+IuUoq/WA9Hp7dRfL8RP2+mr8dbM6TWl13OuZ+J7RXi96GTlEj8V/ad6KDq9F57Sdpx44ebo4Y4ce7m5w/G3TS+F/xdeqVwdd3Lxt9Pt/FT0+jLSa4q0/9mhNNqmV8L/A6/C/cX29bgR3yy26+JP1qQwFf12fEO5SOD+Ig9bJ5nGhOiF8A+K0vZIsX2j8IRBLGbu1PBCKvoqHF+ElwkHP4QJxzw9ME/vtvA/E/Y1W8Qa/58oq5g6K/HVIjzRUc2Roo9sMp5SpP1s/B2Hixdu1+im8GvFBPh2MR+7SfPJ5BWeKX6rfsBS0W/VvJ1+LH6FvYo8LRA3oyvkFD6tn69Tul95Ie7DYeNcP1L8w43tfmozjtIo+knjpPHSIi91+5njNPptyGa2ntOSbN/i7xXCMguOEI/03i3GsULM9J8qfMMcKW7g8eLG7RB+c9bhB8U1NWG9dkKLaRwq1n4dL27wclEVnicW5mUhp/Bz8C2l6PNFm73dp+wUYQp4oZjRuqP4jcZSsaD3JW2msb/owB0lnqrzcZCMtkE5hU/r2pPEoz9R5glna3cUcW5QGpXOEa2fxSbnGXCGsIxYKl7Ip0l8D3SanMLXRU9noCbLIo2uunJwK94vxpH6cuqPmKXvlOjd5FphkJWNnMJfLCwN+pXPC8emWcgp/Ecyxt0tTs8VcU7hB2GxcrZxnJzC92zkr4NM2mt2M3IKf8P4p0x5snkfzCn8F4UZXL+yTkYPhLmbk/OFH+InMqfTSbbiSqXfyCzkXvU3LDpQKzOn03dMhTnXaUklfI+ohO8RlfA9ohK+R9Q0TiRXNyIfeybhbTWNvrJanZKraJ9U2ydrwriozjO8+Fd0jIOS8JaaWCRWp925yorWSbV9qCYc49Tr+cM01kUVnWGOssQ/hUdq4itlvyl2zhK2JRWdJR33uRs76q2Y1IR5mYpOk7qJX0vZfLwxOXCi8FBU0RmGlPY5OxXzFHXh7xNWVIQh5yDMl04VPqHU+XaFV+20w/TZJHy2Ri/bFRPj1RonzHdpnAq/SvmRqD2EwWjVk504s/B15Qr3NRKj21TYYbxPaSF7nLBXrJgYVyi/lfi0ES5YRpboTWLaq85FeHumjA0yZ4nqus75wtp5F6NVJZ/Cz4vwTLFmqGpits7ZuDrZvmXENkYXfpv4Ss4DxfYsfEfckKrOb86zhMni1cpvrqzHGUZZu9tMyCeEof5vi+0ZwhbyTry4g5kdFOaKHuk5yb57hWXzqF8xHqsEPyo+nXNXsm+BuBlXyuj+tY84RJivbBIf0q2zWgwTNDVrGa/qeLyI4BLlQNru+LBYLnkT3qZcdjMdOADvFAslHsZ7lWYy20Tnc6kxvtfN+B9LTzkCX1J+EzBlp1i/ulksX/x38RsEZhe/g8VitSFlHZ6yTrRmWloz247wigSXiObRke1cOKAMC8Ev0+Y62XYtyYbFirrbxMD+6XiTWJo+c4zrBontorWyRngeeWTs00en3RLfjNniRgyJD3rtJT6tNgg8KarNx0QnaLNx6u9W+D+ts5w73Al8LQAAAABJRU5ErkJggg==
    position:
      x: 408.6666259765625
      ''y'': 198.3333282470703
    configs: []
  alphanumeric_filter:
    id: node_1755742744761_861
    operator_id: ''15''
    operator_type: Filter
    operator_name: alphanumeric_filter
    display_name: 字母/数字占比过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6NTQ0NUExNUYwNzk2MDc0ODg2NTcyNzVBNTFEOEQyRDciIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6Qjg0OTZGMjcwMzZGMkM0NzhCMDQyNTZDQzU2OTc5QTAiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 714.6666259765625
      ''y'': 197.3333282470703
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
        config_name: min_ratio
        config_type: number
        default_value: ''0.1''
        is_required: false
        is_spinner: false
        spinner_step: ''0.01''
        final_value: 0.1
        display_name: 最小比例
      - id: 4
        operator_id: 15
        config_name: max_ratio
        config_type: number
        default_value: ''999999''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 999999
        display_name: 最大比例
  character_repetition_filter:
    id: node_1755742766906_855
    operator_id: ''2''
    operator_type: Filter
    operator_name: character_repetition_filter
    display_name: 字符级重复率范围过滤
    icon: >-
      data:image/png;base64,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
    position:
      x: 1048.2603359222412
      ''y'': 198.83332347869873
    configs:
      - id: 5
        operator_id: 2
        config_name: rep_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: false
        is_spinner: false
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
        is_required: false
        is_spinner: false
        final_value: 0
        display_name: 最小比例
      - id: 7
        operator_id: 2
        config_name: max_ratio
        config_type: slider
        default_value: ''0.5''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: false
        is_spinner: false
        final_value: 0.5
        display_name: 最大比例
  flagged_words_filter:
    id: node_1755742778765_570
    operator_id: ''1''
    operator_type: Filter
    operator_name: flagged_words_filter
    display_name: 标记词比例过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6RTE4RTVCOTdDRjczQjE0Qzg2QTE4RUVBN0ZDMDZBNzkiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6OTZBNTY2QUE0M0U3QTU0Mjk1OUE1OTM4Qzg5OEY4NTYiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 1050.2603359222412
      ''y'': 488.83332347869873
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
        default_value: ''15''
        is_required: false
        is_spinner: false
        final_value: ''15''
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
        is_required: false
        is_spinner: false
        final_value: 0.01
        display_name: 最大比例
      - id: 11
        operator_id: 1
        config_name: use_words_aug
        config_type: checkbox
        default_value: ''false''
        is_required: false
        is_spinner: false
        final_value: false
        display_name: 词汇增强
  text_length_filter:
    id: node_1755742954844_938
    operator_id: ''13''
    operator_type: Filter
    operator_name: text_length_filter
    display_name: 文本长度范围过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6OTEyREZEQkZDMzhBNTM0Nzg5QUQwRUI1QjEzREY2RkUiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6OTAwRjAxNzc3NEI5NjI0NzgxOTkzMTk0Mzg0NTZERDUiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 725.2603359222412
      ''y'': 488.83332347869873
    configs:
      - id: 12
        operator_id: 13
        config_name: min_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 10
        display_name: 最小长度
      - id: 13
        operator_id: 13
        config_name: max_len
        config_type: number
        default_value: ''136028''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 136028
        display_name: 最大长度
  document_deduplicator:
    id: node_1755743003935_137
    operator_id: ''12''
    operator_type: Deduplicator
    operator_name: document_deduplicator
    display_name: 文档去重（MD5）
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABdCAYAAAAsRtHAAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6QzA1MDExNkU3NjcyNjY0RkExNDQzRUIyNjI1MTVEQkQiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6N0Y2NDJBOEM2NjU4NkQ0RDlDOTIxQjJGMjlGMDY2MTMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 409.2603359222412
      ''y'': 486.83332347869873
    configs:
      - id: 14
        operator_id: 12
        config_name: lowercase
        config_type: checkbox
        default_value: ''true''
        is_required: false
        is_spinner: false
        final_value: true
        display_name: 小写
      - id: 15
        operator_id: 12
        config_name: ignore_non_character
        config_type: checkbox
        default_value: ''true''
        is_required: false
        is_spinner: false
        final_value: true
        display_name: 忽略非字符
edges:
  - source: node_1755742731920_356
    target: node_1755742744761_861
  - source: node_1755742778765_570
    target: node_1755742954844_938
  - source: node_1755742766906_855
    target: node_1755742778765_570
  - source: node_1755742954844_938
    target: node_1755743003935_137
  - source: node_1755742725315_552
    target: node_1755742731920_356
  - source: node_1755742744761_861
    target: node_1755742766906_855
', '2025-08-21 10:24:02.369476', '2025-08-21 10:25:37.779773');
INSERT INTO "public"."algo_templates" VALUES (3, '54', '数据增强', '该模版用于数据增强，旨在扩展用户的提示数据，以帮助模型更好地理解任务。', 'data_enhancement', 't', 'dataflow-demo-process', '/path/to/your/dataset', '/path/to/your/dataset.jsonl', '1', 'f', '3', 'name: 数据增强
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
    id: node_1755743178730_333
    operator_id: ''21''
    operator_type: Mapper
    operator_name: optimize_instruction_mapper
    display_name: 优化Instruction
    icon: >-
      data:image/png;base64,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
    position:
      x: 438.6666259765625
      ''y'': 323.3333282470703
    configs:
      - id: 34
        operator_id: 21
        config_name: hf_model
        config_type: select
        select_options:
          - value: ''24''
            label: alibaba-pai/Qwen2-7B-Instruct-Refine
        default_value: ''24''
        is_required: false
        is_spinner: false
        final_value: ''24''
        display_name: 模型名称
edges: []
', '2025-08-21 10:26:21.114035', '2025-08-21 10:26:21.114035');
INSERT INTO "public"."algo_templates" VALUES (4, '54', '数据生成', '该模版用于数据增强，旨在扩展用户的提示数据，以帮助模型更好地理解任务。', 'data_generation', 't', 'dataflow-demo-process', '/path/to/your/dataset', '/path/to/your/dataset.jsonl', '1', 'f', '3', 'name: 数据生成
description: 该模版用于数据增强，旨在扩展用户的提示数据，以帮助模型更好地理解任务。
type: data_generation
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
type: data_generation
process:
  extract_qa_mapper:
    id: node_1755743324810_423
    operator_id: ''11''
    operator_type: Mapper
    operator_name: extract_qa_mapper
    display_name: 问答对提取
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6OUQwNjhCRURBNTc1MkY0NTlBNjNEQzNEQTBBNkVBQTUiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6NDI2M0Q2N0NEQ0Y2QzQ0MUE2MjlGMTdDMURBMjkyNTAiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 403.6666259765625
      ''y'': 277.3333282470703
    configs:
      - id: 16
        operator_id: 11
        config_name: hf_model
        config_type: select
        select_options:
          - value: ''18''
            label: alibaba-pai/pai-qwen1_5-7b-doc2qa
        default_value: ''18''
        is_required: false
        is_spinner: false
        final_value: ''18''
        display_name: 模型名称
edges: []
', '2025-08-21 10:28:47.141256', '2025-08-21 10:29:14.172232');
INSERT INTO "public"."algo_templates" VALUES (2, '54', '数据处理-高阶', '该配置文件用于定义数据处理流程，包含多个处理机制，如清理电子邮件、链接、字符规范化、文本过滤和去重等操作。用户可根据需求调整参数，以提高数据质量和处理效率，确保最终数据集的准确性和一致性。', 'data_refine', 't', 'dataflow-demo-process', '/path/to/your/dataset', '/path/to/your/dataset.jsonl', '1', 'f', '3', 'name: 数据处理-高阶
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
      min_ratio: 0.1
      max_ratio: 999999
  - average_line_length_filter:
      min_len: 10
      max_len: 999999
  - character_repetition_filter:
      rep_len: 10
      min_ratio: 0
      max_ratio: 0.5
  - flagged_words_filter:
      lang: en
      tokenization: true
      max_ratio: 0.01
      use_words_aug: false
  - language_id_score_filter:
      lang: en
      min_score: 0.5
  - maximum_line_length_filter:
      min_len: 10
      max_len: 7328
  - perplexity_filter:
      lang: en
      max_ppl: 8000
  - special_characters_filter:
      min_ratio: 0
      max_ratio: 0.84
  - text_length_filter:
      min_len: 10
      max_len: 136028
  - words_num_filter:
      lang: en
      tokenization: true
      min_num: 20
      max_num: 23305
  - word_repetition_filter:
      lang: en
      tokenization: true
      rep_len: 10
      min_ratio: 0
      max_ratio: 0.6
  - document_simhash_deduplicator:
      tokenization: space
      window_size: 6
      lowercase: true
      ignore_pattern: ''''
      num_blocks: 6
      hamming_distance: 4
', 'name: 数据处理-高阶
description: >-
  该配置文件用于定义数据处理流程，包含多个处理机制，如清理电子邮件、链接、字符规范化、文本过滤和去重等操作。用户可根据需求调整参数，以提高数据质量和处理效率，确保最终数据集的准确性和一致性。
type: data_refine
process:
  clean_email_mapper:
    id: node_1755743393403_766
    operator_id: ''3''
    operator_type: Mapper
    operator_name: clean_email_mapper
    display_name: 邮箱后缀清理
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6MUNCRTkwQThGNzMyNDk0NEI4ODc5M0I5RjkwRjE0NUYiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6NTZCN0NBM0U4QzBCRDc0Nzk5RTU0REJERkNEODg1NDciIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 152.6666259765625
      ''y'': 125.33332824707031
    configs: []
  clean_links_mapper:
    id: node_1755743399116_476
    operator_id: ''5''
    operator_type: Mapper
    operator_name: clean_links_mapper
    display_name: 链接地址清理
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6M0RDMzhDOEY2OEEyRTQ0MjhEMzIyODJFRDMzMjVDNzciIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6MDIxNjZCRDIwNTQyQ0M0N0JGN0Y4RDZCQzg2RTYxRDkiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 466.6666259765626
      ''y'': 124.22221713595923
    configs: []
  fix_unicode_mapper:
    id: node_1755743407480_656
    operator_id: ''7''
    operator_type: Mapper
    operator_name: fix_unicode_mapper
    display_name: Unicode错误修正
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6Q0M4RTMwRkI2RDM3REE0NjhEMEEwQ0Q2OThGRUIyN0QiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6NDBFRTREMkU1MkMyNUQ0RkE3QUVCMTdBRTY4NDlENTgiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 774.5555148654514
      ''y'': 121.62962454336662
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
        is_required: false
        is_spinner: false
        final_value: ''19''
        display_name: 标准化
  punctuation_normalization_mapper:
    id: node_1755743417339_310
    operator_id: ''22''
    operator_type: Mapper
    operator_name: punctuation_normalization_mapper
    display_name: Unicode标点规范化
    icon: >-
      data:image/png;base64,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
    position:
      x: 1056.0246506679207
      ''y'': 119.69135293842837
    configs: []
  whitespace_normalization_mapper:
    id: node_1755743427415_413
    operator_id: ''40''
    operator_type: Mapper
    operator_name: whitespace_normalization_mapper
    display_name: 空白规范化
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6NzMyMjQ3NjdCMjdEQjc0Q0E0MjBDRTEwREJBNUE4MDciIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6Qjc3OEE5ODM5RjdEQjI0NzhBODQzNkM0NTYxOTlBNDgiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpkZWExYmQ4YS1iZDgyLTQ4MDItYWIxMi0wYTEwOTU2YzYzZmIiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 1409.1110704210068
      ''y'': 118.45678503719378
    configs: []
  alphanumeric_filter:
    id: node_1755743437240_279
    operator_id: ''15''
    operator_type: Filter
    operator_name: alphanumeric_filter
    display_name: 字母/数字占比过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6NTQ0NUExNUYwNzk2MDc0ODg2NTcyNzVBNTFEOEQyRDciIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6Qjg0OTZGMjcwMzZGMkM0NzhCMDQyNTZDQzU2OTc5QTAiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 1425.1604531370563
      ''y'': 446.85184676558885
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
        config_name: min_ratio
        config_type: number
        default_value: ''0.1''
        is_required: false
        is_spinner: false
        spinner_step: ''0.01''
        final_value: 0.1
        display_name: 最小比例
      - id: 4
        operator_id: 15
        config_name: max_ratio
        config_type: number
        default_value: ''999999''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 999999
        display_name: 最大比例
  average_line_length_filter:
    id: node_1755743444173_375
    operator_id: ''41''
    operator_type: Filter
    operator_name: average_line_length_filter
    display_name: 平均行长度范围过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6RDhDNUFDRTRBOEEzRjY0REJCMDIxMDgyMEU2NDk5MjEiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6REU1MzdEQTc1QjlCM0U0QjkwRUYxNkYwQkE0RUUyNkUiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpkZWExYmQ4YS1iZDgyLTQ4MDItYWIxMi0wYTEwOTU2YzYzZmIiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+UAKmSAAACiJJREFUeJztnX/QVFUZxz/nDVAIEEyIECnEjISUKZAfAolU+MI0qOEPHBOdMBiCkSytDpBT5JlJbJwcAUepeEkbRIhiBI3yB74QCqSogYXiqIEakyI/LATl9Mdzd/fc3bvv3t137927++7nr3vPfc65z373zLnnnnvOcxTlwtiewOeArkCnspVbeU4AB4G9wB60Ol6OQlXJOY3tDUwGxgGjgFPL4VDC+RB4AXgCWAs0o5UtpaDihTd2LHAL8FXgY6XctIZ4A1gMLEarw8VkDC+8sYOBu4DReSwOAbuB/cD7xTiRcNoB3YF+QF+CNTsA/ARYhFYfhim0sPDGtgMWAN/3nEhxAngKWAk8hla7w9ywqjG2C/Bl4GJgCrnN6w5gClr9o1BRLQtvbC9gDTDcST0GLAN+jlavhvW55jD2JOAa4EdAf+fKEWAGWj3QUvb8wht7FvAn4Ewn9XFgJlr9s1R/aw5jOwA3AbcCJ3upFvgBWi3Mly1YeGP7AFuAPl7KR8Bc4PZSn+I1j7GDgIeAAU7qd9BqcZB5rvDGdgU2AV/wUv4HXIVWa8vraQ1ibHekmznKS7HAFWi1Ktu0ISD7fWREPwZ8vS56SLQ6AIwHnvFSFLAUY/tnm/qFN/ZK4Aon5dto9VhEbtYmWv0XmAi84qWcAjRhrK91yQgvXaVfONd+g1ZNEbtZm2j1DnA50mIAXABc75q4NX4WcLp3/BYwJ2L3ahutduCvyAswtmPqRIQ3thPwXcdoLlodisO/GudnwNvecW+k3w9kavylQA/v+DXgt3F5VtNIe3+nk3JD6iAl/Dedi/eGHW+oE4qlwAfe8VCMHQDQgLGdgYscw/vj9qym0epdYJ2T0ghS40cA7b3EnWj1r5hdawtscI7Hggj/JSdxU6zutB2eco4Hgwh/lpO4K05v2hAvA6lPhn0wtnMD8EnH4LXYXWoLSGdln3emgN4NQBfHpN53jw5X284N+L+b1ruR0eEK36ldXrNqxtiJwEhkvOmVQuaVIGhYuLoxdjzwMKCBZow9o8IeBVJbwhv7NeBRJ6UX8Dfvi1qiqB3hjR2BfCPOpgfwNMZ+ImaPWqQ2hDd2JPDXFixOB7YlSfzqF15q+uYQlv0Q8U+J2KNQVLfwhWt6Nv2AJ6NxpjiqV3gRPUxNz2YwxlZ8TKo6hTd2GLmiTwGuClnCBRhbyp9WNqpPeGMH4h9FPYLMbluBVg8CPw1Z0kiM/XPZ/QtJdQkvs7W24Z88ewitlqTPtLoVMCFL/ArGri+fg+GpHuGNPQfYCnTMutIbY3dg7MnpFK3mIjOcj1GYRox9pGx+hqQ6hDe2BzKX0xX9Bef4PKSrmFkCpNWPvTxhuDjump984Y09DWleujqps9HqPGSeYopBwNb0jC1jZwNDirhTI8auK2xWHpItvLGnAtuBTzupt6DV3QBoNQlwa+pAYA3GzkFWr3y8yDtOwNj13mKMSEmu8NJsbMEvOsjEoAxaTcQv/iT8c1mKpRG4uRX5Q5FM4UX0rcDZAVfnYOzvfCkifjkfkN3LWFYgyRNe5hc+gzQbKZYAq53zKRjrX+qi1QT8Nb9UmpEeUaQkS/hMTR/kpZwAlqPVTLSaDDztWF+Nsff58kvNf5TS2YhWY4pdOlkKyRE+V3SAV9FqqnM+EnjROZ+Gsff4ytGqkdLmB21HqwtLyFcSyRA+uHkB6Iuxt6fPZP3VGOB1x2Y6xi7x5dJqNMUNoD1PZvlMLCRDeOm9DApI7wDcjLGZXopW76HVZwB35eGMAPFHIe11IXYAw9Dqg0KG5aSywhurMHYL8uaZYjmyrvY9J20Oxi5w8g0md+hghq/ZMfZsMlPP8/EmMCJu0cE/2FQJNuNfvLwErWYCYOxQ5I21m3dtHsbuRZqFfEMB0z2bR5AHcUu/723gfLQ6WrL3raByNd7YDchMZZeN6SOZDzMEiROQ4h4Kj78sQN52C4k+BK32tWATKZUR3tiVSPSPbFZg7LXpM632AOcj8WLKxSEqLDpUQnhjH0RWxKXYRGZCJ8jSxG+kzzI1vxxNwmHkQVpR0SFu4Y1twr+Ottnr+o3LslyFsZelz0T8EYQbX8/HIWBomMgacRCf8MYuBa51Up5DqzEAXlCKy7JyrM6q+TuAYZQm/mHkQZqY4BfxCC+v9t/KSj0NY7+YPtNqDbL60GVVgPjDKY4jJEx0iEN4EX1awJUzkHmNY9MpWv0BWQj3jmOX3ew8hwwdvBni7qkHaSKaF5dohTd2HsGiuzyOsWPSZ1o9gdRSl9UYO8Gx2ULhns5HJLCmp4j6BSq73c7HRozthlYHMXYPuR8/ANZh7LnIOq2XgM+2UN4JYHhSRYfom5qbirB9FmOfxx8RKpvNFBb9OCL69iLuHTvRCq/Vk8CFIa3PBM4tYNOFlkUHGIdW20Les2JE/3DVaiPBb6lRcAlahRmRrDjxdCe1+gvyETpKLkWrP0Z8j7IR3wuUhNeKSvzLva5o1RDvkIGIf01Bu+K4LijYWtKJf5BMAmHOLlNpU6s1fFdlhoVlJtisVpZyHVotL4c7laByH0K0WkTpcc+ur9aanqKy31y1+iUwr8hcU9FqWQTexErlZxlodRsSPjcM06q5eXGpvPAAWhkKi38jWv0qDnfiIBnCQ0r8fM3OjWh1V5zuRE1yhId8zc78WhMdKj+vJhetDMYeRzZ+Wev9GTVH8oQHvID3eYPe1wLJampqG3fK4bEG/CGbulInKlxtjzQA7zoJn4rZmbZEL+d4fwMSEzHFAOqUH4kQlYp2eACt/tMA7HRMhsXvVZvAnQv0d5CHazOyiQjAMG/nhDrlxZ2i2AzQgFb7ySxP70DubK46rcHY9vinuWyATHfyIedCoQlIdYpjEtDTO95LusYLTWQmg47G2FgXYtU4P3SOl6PVCUgJr9Ve/AH7F2Js/eWqtRh7NZkw8UeBu1OXXHENmS0VhgMzYnGuVpFQi+6uOIvQ6q3USUZ4Wfbijo/cgbHuarw6YZHQLU1kXpr2Ifu9psluTgyZ4P0dgYeTGB62CliI7H4G0lWfkb1MP2iTxYHIUsXOXspLwPj63iEhkJp+G7LHa4o70ConDEvuA1SrncAlZHo5nwc2Y2wx0Y7aHhIT7df4RV+Lv1eTpqWNdCcDDyAvVSAP3vnAnfV9orKQJUVN+MMCrEfmcwau2Sq0dfQ44Pf4hzRfRP6AtW1+U11j+yI1/Ab8O08sQ3YGPR6UDcJtlt4fWEFuYLVd3g1WotXr2dlqFok0chEwFWmS2ztXjyIf5u8tVExh4eVm7ZFNGOeTeei67EGWse9GlqsfQXY+rnYUEkuhGxIQ+hxkBPekANsNwCy0ejngWmDB4ZFd678HTMe/m05bZiNg0GpDQUuH4oRPIfsDTgauBEZTfJjBamcX0mO53+sFFk1pwrsY2wHZRm0gso6pJ9IctW8hVzVxEHgfeAN5p3kWrf7d2kL/D1Wan/AIvBh0AAAAAElFTkSuQmCC
    position:
      x: 1069.6048975815006
      ''y'': 448.08641466682343
    configs:
      - id: 53
        operator_id: 41
        config_name: min_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 10
        display_name: 最小长度
      - id: 54
        operator_id: 41
        config_name: max_len
        config_type: number
        default_value: ''999999''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 999999
        display_name: 最大长度
  character_repetition_filter:
    id: node_1755743453405_671
    operator_id: ''2''
    operator_type: Filter
    operator_name: character_repetition_filter
    display_name: 字符级重复率范围过滤
    icon: >-
      data:image/png;base64,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
    position:
      x: 778.2468728901428
      ''y'': 445.61727886435426
    configs:
      - id: 5
        operator_id: 2
        config_name: rep_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: false
        is_spinner: false
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
        is_required: false
        is_spinner: false
        final_value: 0
        display_name: 最小比例
      - id: 7
        operator_id: 2
        config_name: max_ratio
        config_type: slider
        default_value: ''0.5''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: false
        is_spinner: false
        final_value: 0.5
        display_name: 最大比例
  flagged_words_filter:
    id: node_1755743461811_356
    operator_id: ''1''
    operator_type: Filter
    operator_name: flagged_words_filter
    display_name: 标记词比例过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6RTE4RTVCOTdDRjczQjE0Qzg2QTE4RUVBN0ZDMDZBNzkiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6OTZBNTY2QUE0M0U3QTU0Mjk1OUE1OTM4Qzg5OEY4NTYiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 464.6666259765625
      ''y'': 446.8518467655889
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
        default_value: ''15''
        is_required: false
        is_spinner: false
        final_value: ''15''
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
        is_required: false
        is_spinner: false
        final_value: 0.01
        display_name: 最大比例
      - id: 11
        operator_id: 1
        config_name: use_words_aug
        config_type: checkbox
        default_value: ''false''
        is_required: false
        is_spinner: false
        final_value: false
        display_name: 词汇增强
  language_id_score_filter:
    id: node_1755743489928_91
    operator_id: ''42''
    operator_type: Filter
    operator_name: language_id_score_filter
    display_name: 特定语言置信度过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6QzMzNEQyQkM4OUE4RDc0NDlEMTNBNjY0RUQxNjIyMEQiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6NzNBRTFCNzY0RUE5RTk0RUE3MUQwOEYyNzQ1RUNGMDIiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpkZWExYmQ4YS1iZDgyLTQ4MDItYWIxMi0wYTEwOTU2YzYzZmIiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 472.0740333839699
      ''y'': 766.6049331853419
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
        default_value: ''15''
        is_required: false
        is_spinner: false
        final_value: ''15''
        display_name: 语言
      - id: 56
        operator_id: 42
        config_name: min_score
        config_type: slider
        default_value: ''0.5''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: false
        is_spinner: false
        final_value: 0.5
        display_name: 最小分数
  maximum_line_length_filter:
    id: node_1755743497094_507
    operator_id: ''43''
    operator_type: Filter
    operator_name: maximum_line_length_filter
    display_name: 最大行长度范围过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6MDJFRkQxRTU0MjNFRUQ0NUIzOTg0QTQ2RTc4RTFEQTEiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6QzJCQTIyQkJDQTQwNzE0NEE5RDhEOThGODIzNDlFMDIiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpkZWExYmQ4YS1iZDgyLTQ4MDItYWIxMi0wYTEwOTU2YzYzZmIiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 794.2962556061921
      ''y'': 760.4320936791692
    configs:
      - id: 1
        operator_id: 43
        config_name: min_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 10
        display_name: 最小长度
      - id: 57
        operator_id: 43
        config_name: max_len
        config_type: number
        default_value: ''7328''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 7328
        display_name: 最大长度
  perplexity_filter:
    id: node_1755743505435_969
    operator_id: ''44''
    operator_type: Filter
    operator_name: perplexity_filter
    display_name: 困惑度范围过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6OTZCMzZEMkFDNUNGNTA0QkJDMEYzMjE2NThFQzMzMUUiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6MDIzNEI2REU2RUVFMzM0NUJFM0ZBMUNDNDhEQjNFREYiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpkZWExYmQ4YS1iZDgyLTQ4MDItYWIxMi0wYTEwOTU2YzYzZmIiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 1094.2962556061918
      ''y'': 756.7283899754655
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
        is_required: false
        is_spinner: false
        final_value: ''15''
        display_name: 语言
      - id: 59
        operator_id: 44
        config_name: max_ppl
        config_type: number
        default_value: ''8000''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 8000
        display_name: 最大困惑度
  special_characters_filter:
    id: node_1755743517278_692
    operator_id: ''45''
    operator_type: Filter
    operator_name: special_characters_filter
    display_name: 特殊字符比例过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABdCAYAAAAsRtHAAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6RUExOUVBMzI4MDc1QTU0NDk1RjY2RTUwQkE5Njk3MzgiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6MkUxMDY3OTQzODgwRUY0QkFBRjJGMDZFNTJCMDI2RUMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpkZWExYmQ4YS1iZDgyLTQ4MDItYWIxMi0wYTEwOTU2YzYzZmIiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+ESoobgAACcFJREFUeJztnX+QVWUZxz+7S0srrJuCWtgE/kDcyFwrERhKwNFSacrVYRxLTBNDzTGCMkOryaZyJjZqNEHHrMypSRKzX2sZyIRImtNS5MpCiDkpJNqiLGsrG/3xvYf73sO59/y673su997PDMO57z3nvC9fzn1/PM/zPqeBvk5SMBGYBUwF3gkcB7QBI9PctMIYAl4FngU2AxuANcDTaW7akED4I4D5wGVI7FplC/Aj4E7g33EvjiP8aOBG4NPA4XErqmL2IvFvAV6JelFU4S8AbgPG+coHgUeA1cBG9FN8BXg9agMOAUaiX/kk4BRgNnA2ehBNdgGL0K8glDDh3wx0AVf7yp8GlgIrUf9Xa7QAnUjo03zf3QcsAPaUukEp4Y8AHgJmGGUvAp8DfgL8L357q44G4KPAt4HxRnkPcC6wo9iFjUXK21D3YYp+PxpM76Muusd+YBXS5R6jvANYCxxV7MIg4ZuBB3IXezdfDMwF+tO2tErZC1yBupjhXNlJwK+B1qALgoRfigYQkOifzJXVCWcFcDF58U8Hlged6Bf+w2i66PFFCn9CdcJZCVxnfL4ErXkKMAfXUWi28o7c5weAi9BTXyc+d6CuB+BlNB192fvSfOIXkRf9JeBK6qKnYTGwPXc8BviS+aUnfCtwvVF+A/Af2y2rcgaAhcbn+cAx3gdP+EuBI3PHW4F7nTSt+nkQeCp33ILEBwqF91gG7HPRqhrBnBHO8w4aUb8+Nfd5CPipw0bVAg+SN6tMRPYeGsnP2QHWYYy8dcrCIPA74/NskPBTjMI1LltUQ6w2js8ACT/ZKOxx2Zoa4q/G8ckg4Y81Crc4bU7t0GccjwcJb3qT6nN3O7xkHLeBhG82Cv/rtDm1xUDu7yagpZg9vk75MddGzSMya0Z0xgHvB96LDE3HIO/YKDRVG0BT4E2oL30E+X4rmkoV/ijgI2hFPZ1o7TTXI39HC8GVwDNlb10ZqLSu5gzguyh46C7gAyR7OCajcIte4OcoSqKiqBThW1FsygbkRBhVxnt3It/CH4D3lPG+qagE4c9DffP8sBNTMhtZChdZricSWQu/BDmE3+qwzm+h7idTshT+WuBrGdXdiWY/mZGV8NeikMAsOQv4YVaVZyH8ErIX3WMe8KssKnYt/Cyy616KcT6aejrFpfCHAb9xWF8cbkIrY2e4FH45ij6Ow93IVbYp5nUfRANonA0DTmc6roQ/kUKHehhrgZkotmcTcsBH5SHkaluVq7eLaM778cDnY9STClfCL4543pMoQnkmEt/jbqIZvobRk+7xGlownYhMEWHcSnlXzUVxIXwrcFXIOTtRuNsU4LGA729E0VhhNKBYz4m+8udQwNYUtGArxYyQ78uCC+HnIkGKsRU9kSt85WNQV/MM8HVgbIS6GlGX1oue8HYK/41PAnNQ91OMgwJMbeBC+DAbzL8I3rZyOrJQTkpQZxMytn2BYOtmT4lr51Ikpr2c2Bb+cHLhDCVoKVLeDZxAtL7ZTx96cq9EQVp+SnVbTcCZCeqMhW3hz0l5/TbUN89E+67C2IoG8klo990bCes9N+F1kbEtfNyBqgEt4zt85WtRgP9pyLbuZzdwMxpUg3avnEW87mNajHMTYVt4/+wijP3IlvMXNKdu9n3fA1yIfLCeS28FGpyDTBHTgD+jX8tgjHa8Pca5ibAtfJJ/QE/u71tRV7Mg4Jx1wLvQrGUB2txrMgHN/dcjU8DzxIuA9m8eLju2hY+STMIviLmV81i0pWU1muWYDBPsyL4JDa5XGGX+neYDlMZ6mLpt4aOsAkei/tf7c1jAObOAJ4DvAKcWuccc4HFkaXxTSB1HkjEN9HX2kwsrA96CBqpysQ2lUinFMNon6tFCeGTBN9CORNDD8wSlrYv+Opop/Wt8jfInyujH0Nl2XE2U/8Qm4i9Y2o3jRuDdZa6jKWZ7YmO7q/EPeuXCDK7dT4J8MSFYTxlgW/htlu9vi+dsV2Bb+F7L97eF9XbbFv4Xlu9vi9/arsC28M9yaHY3D9uuwIVZOFKqqBD2hnw/bBynzRj1KDJVW8WF8HelvH4XcDyyOnoCm9PgYfI5GJahPDFpBscfpLg2Mi6EfwH4fYrrL0euwaVo/r4BIycAcDTKOnI5yh2wE1kyky77uxO3NAauNiZ0ocx1cdlIYaTXFmRxbEcm5P3IDjPZd9169J8d167+M/QfZx1XUQbdyN8Zl+ORc/pkX3kv+ZQu/j69BcXaT49Z1xDwiZjXJMZlQNPcBNe0ovj5vwHXRDj/FNTtzCdvF4nKNcSz2afCpfDbSb4pYARwO7I+Ti1yzlfQDuoJCe7fjez3znAdtNqFIrySMhWJ/z3yTvIZqBv7csJ77kC52JySRZh2OTYFXI221dwG/BF4X8L7vIiCnJzn58lqY8LZwI9T3qMdbXBIyi40Jjyfsh2JyHIrzqWEh9PZYjtynGSWmyfrzWdzUHieS1ahef8/HddbQNbCg8I5zqEwp4sNdqPg2U7CbT/WqQThQavMU9F000bqlvtR7E1au1HZqBThPbqQc/wCZNUsmYM9hIdRXuQT0OLNlhsyEbajDNIyFkWNzUa/iHaCowOGkd1/C1oMPUblZZvqx2GUQVp2ocEwzaKrIqm0rqaaMYOshhopTIdVTe9vqiQayEfI7QMGG1HUlEfmoW1VytHG8W5QV2M6o09y2pzawQxX3w4S3oy47XDYmFqiwzjeDBL+caPQzOtVp3zMMo7Xg4RfQ96NNp3C/qhOekZR6G9+FCT8DhTmDJryXOK0WdXPheQjlXtRhsAD83gzYc71VG5axEONBgrdnQfeRNFoFHjGqQnYT8xWK1xEPnZ/EMNI5wm/ByVJ87iFEq9LqxOJ0egdgB53YBjqTJNBF/k5/RgUylYqB0Gd0iwnnyJ+J74sUKbwryMfpjfDOc9/cp3IXAd8zPj8GXzvSfQbybrRzjqPJRS+H6pOOJdRqOH3CXjhTZB18gYKXyayDPgq9W4nCgtRvhxPqz9R+N6/AwQJP4Q8QOaK9mbgl9QH3GK0oW37XeRF34iCZgP9u8Xs8XuRA9p88s9HC4CrqM/zPRqBjyNdLjbK1yEzQVH/cSlHyB4UfrGU/IA7BiVt6EM/oSjpqqqRNuBTKFHdvcDbjO/uRCaCkk77qG+p/xCKV/Tv0n4DhdCtQRk3/oGmTgMEJ+g51BiBlvtjkdO8A+XOOZODUzm+gCYiK6PcOKrwoCDRhcBnqd0nPYhXUQznNyl0KpUkjvAeo1G/Ng8HCXUqmKdQ/Oc9JIjMSCK8yThkw5+Gdm2MR+7D0RycQeNQZB96ivvRhrbNaA/WalKGAP4fwYjHnuOgkcUAAAAASUVORK5CYII=
    position:
      x: 1439.975267951871
      ''y'': 758.3744742311078
    configs:
      - id: 60
        operator_id: 45
        config_name: min_ratio
        config_type: slider
        default_value: ''0''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: false
        is_spinner: false
        final_value: 0
        display_name: 最小比例
      - id: 61
        operator_id: 45
        config_name: max_ratio
        config_type: slider
        default_value: ''0.84''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: false
        is_spinner: false
        final_value: 0.84
        display_name: 最大比例
  text_length_filter:
    id: node_1755743527323_910
    operator_id: ''13''
    operator_type: Filter
    operator_name: text_length_filter
    display_name: 文本长度范围过滤
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6OTEyREZEQkZDMzhBNTM0Nzg5QUQwRUI1QjEzREY2RkUiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6OTAwRjAxNzc3NEI5NjI0NzgxOTkzMTk0Mzg0NTZERDUiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 1448.617243260513
      ''y'': 1045.6172788643541
    configs:
      - id: 12
        operator_id: 13
        config_name: min_len
        config_type: number
        default_value: ''10''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 10
        display_name: 最小长度
      - id: 13
        operator_id: 13
        config_name: max_len
        config_type: number
        default_value: ''136028''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 136028
        display_name: 最大长度
  words_num_filter:
    id: node_1755743533468_245
    operator_id: ''24''
    operator_type: Filter
    operator_name: words_num_filter
    display_name: 单词数量范围过滤
    icon: >-
      data:image/png;base64,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
    position:
      x: 1114.0493420259452
      ''y'': 1051.790118370527
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
        is_required: false
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
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 20
        display_name: 最小数量
      - id: 88
        operator_id: 24
        config_name: max_num
        config_type: number
        default_value: ''23305''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 23305
        display_name: 最大数量
  word_repetition_filter:
    id: node_1755743543432_421
    operator_id: ''18''
    operator_type: Filter
    operator_name: word_repetition_filter
    display_name: 词级重复率范围过滤
    icon: >-
      data:image/png;base64,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
    position:
      x: 804.1727988160685
      ''y'': 1055.4938220742306
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
        is_required: false
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
        is_required: false
        is_spinner: false
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
        is_required: false
        is_spinner: false
        final_value: 0
        display_name: 最小比例
      - id: 84
        operator_id: 18
        config_name: max_ratio
        config_type: slider
        default_value: ''0.6''
        min_value: ''0''
        max_value: ''1''
        slider_step: ''0.01''
        is_required: false
        is_spinner: false
        final_value: 0.6
        display_name: 最大比例
  document_simhash_deduplicator:
    id: node_1755744114030_934
    operator_id: ''19''
    operator_type: Deduplicator
    operator_name: document_simhash_deduplicator
    display_name: 文档去重（SimHash）
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAABGdBTUEAALGPC/xhBQAACklpQ0NQc1JHQiBJRUM2MTk2Ni0yLjEAAEiJnVN3WJP3Fj7f92UPVkLY8LGXbIEAIiOsCMgQWaIQkgBhhBASQMWFiApWFBURnEhVxILVCkidiOKgKLhnQYqIWotVXDjuH9yntX167+3t+9f7vOec5/zOec8PgBESJpHmomoAOVKFPDrYH49PSMTJvYACFUjgBCAQ5svCZwXFAADwA3l4fnSwP/wBr28AAgBw1S4kEsfh/4O6UCZXACCRAOAiEucLAZBSAMguVMgUAMgYALBTs2QKAJQAAGx5fEIiAKoNAOz0ST4FANipk9wXANiiHKkIAI0BAJkoRyQCQLsAYFWBUiwCwMIAoKxAIi4EwK4BgFm2MkcCgL0FAHaOWJAPQGAAgJlCLMwAIDgCAEMeE80DIEwDoDDSv+CpX3CFuEgBAMDLlc2XS9IzFLiV0Bp38vDg4iHiwmyxQmEXKRBmCeQinJebIxNI5wNMzgwAABr50cH+OD+Q5+bk4eZm52zv9MWi/mvwbyI+IfHf/ryMAgQAEE7P79pf5eXWA3DHAbB1v2upWwDaVgBo3/ldM9sJoFoK0Hr5i3k4/EAenqFQyDwdHAoLC+0lYqG9MOOLPv8z4W/gi372/EAe/tt68ABxmkCZrcCjg/1xYW52rlKO58sEQjFu9+cj/seFf/2OKdHiNLFcLBWK8ViJuFAiTcd5uVKRRCHJleIS6X8y8R+W/QmTdw0ArIZPwE62B7XLbMB+7gECiw5Y0nYAQH7zLYwaC5EAEGc0Mnn3AACTv/mPQCsBAM2XpOMAALzoGFyolBdMxggAAESggSqwQQcMwRSswA6cwR28wBcCYQZEQAwkwDwQQgbkgBwKoRiWQRlUwDrYBLWwAxqgEZrhELTBMTgN5+ASXIHrcBcGYBiewhi8hgkEQcgIE2EhOogRYo7YIs4IF5mOBCJhSDSSgKQg6YgUUSLFyHKkAqlCapFdSCPyLXIUOY1cQPqQ28ggMor8irxHMZSBslED1AJ1QLmoHxqKxqBz0XQ0D12AlqJr0Rq0Hj2AtqKn0UvodXQAfYqOY4DRMQ5mjNlhXIyHRWCJWBomxxZj5Vg1Vo81Yx1YN3YVG8CeYe8IJAKLgBPsCF6EEMJsgpCQR1hMWEOoJewjtBK6CFcJg4Qxwicik6hPtCV6EvnEeGI6sZBYRqwm7iEeIZ4lXicOE1+TSCQOyZLkTgohJZAySQtJa0jbSC2kU6Q+0hBpnEwm65Btyd7kCLKArCCXkbeQD5BPkvvJw+S3FDrFiOJMCaIkUqSUEko1ZT/lBKWfMkKZoKpRzame1AiqiDqfWkltoHZQL1OHqRM0dZolzZsWQ8ukLaPV0JppZ2n3aC/pdLoJ3YMeRZfQl9Jr6Afp5+mD9HcMDYYNg8dIYigZaxl7GacYtxkvmUymBdOXmchUMNcyG5lnmA+Yb1VYKvYqfBWRyhKVOpVWlX6V56pUVXNVP9V5qgtUq1UPq15WfaZGVbNQ46kJ1Bar1akdVbupNq7OUndSj1DPUV+jvl/9gvpjDbKGhUaghkijVGO3xhmNIRbGMmXxWELWclYD6yxrmE1iW7L57Ex2Bfsbdi97TFNDc6pmrGaRZp3mcc0BDsax4PA52ZxKziHODc57LQMtPy2x1mqtZq1+rTfaetq+2mLtcu0W7eva73VwnUCdLJ31Om0693UJuja6UbqFutt1z+o+02PreekJ9cr1Dund0Uf1bfSj9Rfq79bv0R83MDQINpAZbDE4Y/DMkGPoa5hpuNHwhOGoEctoupHEaKPRSaMnuCbuh2fjNXgXPmasbxxirDTeZdxrPGFiaTLbpMSkxeS+Kc2Ua5pmutG003TMzMgs3KzYrMnsjjnVnGueYb7ZvNv8jYWlRZzFSos2i8eW2pZ8ywWWTZb3rJhWPlZ5VvVW16xJ1lzrLOtt1ldsUBtXmwybOpvLtqitm63Edptt3xTiFI8p0in1U27aMez87ArsmuwG7Tn2YfYl9m32zx3MHBId1jt0O3xydHXMdmxwvOuk4TTDqcSpw+lXZxtnoXOd8zUXpkuQyxKXdpcXU22niqdun3rLleUa7rrStdP1o5u7m9yt2W3U3cw9xX2r+00umxvJXcM970H08PdY4nHM452nm6fC85DnL152Xlle+70eT7OcJp7WMG3I28Rb4L3Le2A6Pj1l+s7pAz7GPgKfep+Hvqa+It89viN+1n6Zfgf8nvs7+sv9j/i/4XnyFvFOBWABwQHlAb2BGoGzA2sDHwSZBKUHNQWNBbsGLww+FUIMCQ1ZH3KTb8AX8hv5YzPcZyya0RXKCJ0VWhv6MMwmTB7WEY6GzwjfEH5vpvlM6cy2CIjgR2yIuB9pGZkX+X0UKSoyqi7qUbRTdHF09yzWrORZ+2e9jvGPqYy5O9tqtnJ2Z6xqbFJsY+ybuIC4qriBeIf4RfGXEnQTJAntieTE2MQ9ieNzAudsmjOc5JpUlnRjruXcorkX5unOy553PFk1WZB8OIWYEpeyP+WDIEJQLxhP5aduTR0T8oSbhU9FvqKNolGxt7hKPJLmnVaV9jjdO31D+miGT0Z1xjMJT1IreZEZkrkj801WRNberM/ZcdktOZSclJyjUg1plrQr1zC3KLdPZisrkw3keeZtyhuTh8r35CP5c/PbFWyFTNGjtFKuUA4WTC+oK3hbGFt4uEi9SFrUM99m/ur5IwuCFny9kLBQuLCz2Lh4WfHgIr9FuxYji1MXdy4xXVK6ZHhp8NJ9y2jLspb9UOJYUlXyannc8o5Sg9KlpUMrglc0lamUycturvRauWMVYZVkVe9ql9VbVn8qF5VfrHCsqK74sEa45uJXTl/VfPV5bdra3kq3yu3rSOuk626s91m/r0q9akHV0IbwDa0b8Y3lG19tSt50oXpq9Y7NtM3KzQM1YTXtW8y2rNvyoTaj9nqdf13LVv2tq7e+2Sba1r/dd3vzDoMdFTve75TsvLUreFdrvUV99W7S7oLdjxpiG7q/5n7duEd3T8Wej3ulewf2Re/ranRvbNyvv7+yCW1SNo0eSDpw5ZuAb9qb7Zp3tXBaKg7CQeXBJ9+mfHvjUOihzsPcw83fmX+39QjrSHkr0jq/dawto22gPaG97+iMo50dXh1Hvrf/fu8x42N1xzWPV56gnSg98fnkgpPjp2Snnp1OPz3Umdx590z8mWtdUV29Z0PPnj8XdO5Mt1/3yfPe549d8Lxw9CL3Ytslt0utPa49R35w/eFIr1tv62X3y+1XPK509E3rO9Hv03/6asDVc9f41y5dn3m978bsG7duJt0cuCW69fh29u0XdwruTNxdeo94r/y+2v3qB/oP6n+0/rFlwG3g+GDAYM/DWQ/vDgmHnv6U/9OH4dJHzEfVI0YjjY+dHx8bDRq98mTOk+GnsqcTz8p+Vv9563Or59/94vtLz1j82PAL+YvPv655qfNy76uprzrHI8cfvM55PfGm/K3O233vuO+638e9H5ko/ED+UPPR+mPHp9BP9z7nfP78L/eE8/stRzjPAAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAAJcEhZcwAACxMAAAsTAQCanBgAAAdvSURBVHic7d17zFxFGcfxz7stBcWCRfAWG9N4eVFRQBAUYzVc6oWqISJRFI0QMMaCKCiKQI1QJFyiguIFb1GraEwDUWJtvQRQLrExAVQqaqNiSiQaJFXw7YXXP57d7uzL7nvZd+fsObv7TU4yZ845M7O/M2d2Ls/MjI3/5Cg9YC+M14/9sG8vAi0RD+Ff2Iw/Yvt8A1w4j2fH8VaswJFYNN/EVIRHcRs24nr8tZtAxrrI8a/FR/GabiIcMB7DeqwRL2PWzCXHvxifw/I21ybxJ/wBW8WnOSiMYQmWiq98WXKthjfUj5vwAfx5NoHORvgaPo6Lpty/Q3xua/FTPDibCAeAZ4qv/mQcLfSB4+vnHxEZdFpmKmr2wffrETXYgS/jCl2WbwPEOM7HOzVfAKHZe/BIpwdrnS7g6bhZq+i34RCsMhKdKFrfjZfjrsT/JFEadKzddRJ+X2wQIhNl+Bq8Gr+fX1oHkl+Lmt21id9RWIc92z3QTvgF+IH4M4VdeBcuwM5epXQAmcD7ca7IqESZ/812Ny/Y/5SlU/1W49S6e1KUVd/qeTIHl9vFSzi2fv4iUfHYlN40NccfInJ2g4t1eGMjpuUyrcXOlVqroS3Cj+ELoqgh/lg/mTN1A84HNf9wn4jPphdT4VeKf2fiUzlDlO8jumM73itat/BGHNG4mAp/fuK+FvdlT9rgcye+k5zv1rgh/Au15vYriknXUHCpZi3neNE+2i38O5Ibb8QDxaVr4LkXt9bdC/E2msKvTG5MP40RvWFt4l5BCL9Es7G0U3R4jegtGxL3ciys4WBRlYR78N+iUzUE/EV0l8PeWFbDc5IbNhedoiHi3sQ9XsMBicffCk7MMHF/4n5GDYsTj20FJ2aYSLVdXNPaiBq1VPOR/ncumo+VQbcchhNxEJ7Sh/hTtglzjXX4eZERFyn8U3GNGJ0pEytEP/otokn/qyIinW7or5e8RNSYyiZ6ynL8EqcVEVkRwi8RnUVLCoirF3xFDHFmpQjhvypM/KrEDTJbxuUW/vk4IXMcOXiy6EvPRm7hz8ocfk6Oyxl4buGfmzn8nGS1eM4t/D6Zw8/JHjkDzy18UdXVHIzNfEv35BbmsZlvKS2TM9/SPVXOkZWmH301nbgfv9AsWyfwKq3jBbNlixjnbNTFJ8Qo22HzTGPPKJPwGz2+uf5pnN1FWD8SkwRSTsL3uggrC2UqavZu47e4jd9saPfcfl2GlYUyCd+uFtFtzaLdc2X6reVKzDAxEr5PjITvEyPh+8RI+D4xEr5PVFn4Sls0V1X460Vf/9f6nZBuqaLwl+DtYtb0aWKCXOWomvCX4MIpfhep4CS5sgufmhS2E73Baq3il94UsezCN6ajr9FZ9Aap+O063EpFmbqF23GEMOq/YIb7GqzGK3BorgT1ijLn+DExY+5lHa6/soP/m/AJmcdM50uZhZ8Uayj8s821q4Sd4zVtrv1PVDezjpnOlzIL34nL8aG6e5WKzsmtmvCX48NT/M4VizRUiioJ3070BueomPhVEf4ynUVvUCnxyyT8wx3834fzZhnGdOJv7eDfF8pUjz9cmEandjVHmvsMjXPEJIg7RANsTNR0slr/zpUyCX8ovtijsE7VXN6rlOQuakrdiOknI+E7U2lr4YnM4edk3kuVT0du4au8OOijOQPPLfx3M4efkztyBp5b+FvElPUq8pmcgRfRgDqxgDh6zVn4d84IihD+biWvU0/hOu27m3tKUV0GX8frxa4KZWVC9HSeUURkRbZc1+N5OF2sMn2AWPq1n+wQCy7fhW/g70VF3I8ug+vqx1BT0zolsky9lYNG+nVvr2ldK6vKM7HLTqrtthr+kXg8bhX/ET3jWYn7gZrWBs6BBSdmmEi1va+G32mW8wfpf01jEHm2Zo5/BFtqYpeyu+uei3BMHxI26BybuG/FzkYtJl10+OTi0jM0pMvEb6BZfUynmr8ZTysqRUPAuObicruEldtu4X8jNpGCJ4gB4xG94WOaOv9Y3dohbTB9KnGfqbtVM0a0crjYB7DBbo1T4W/Q3CRqL3zJqCU7HxaJrpHG9k7rJXu+psJOCuOhxmyKY8R2oiO640rNvRInTFn+ZWqO3iRMoBusVs2BjH6zShTXDc4TO2Hupl1RcqGwPSc+k7VGVcy5cCauTs7XTTlHe+G3i11y7qmfL8K3xQsZlfmd2UOsKHW1pk3OnThFm0kSnYR8GK/Db+vnY2Ji10bVXsQzFweLFunZid/tYhPitrsYT5eDt4qlvW9O/I4WL+MqsXf1sLNMbKO9SRjYNrhRdBN0soCeseh4qB7AxZodaXuKqTBbxIa7bxGLIA8L+4uZ5TeJnt3TNUfytovG5wmm2a+bmTdLT3kpPq+5J2DKLrHdzmYxbvmf+jEILK4fS/EC0QXQzq7yZ6I2M6stneYivHqEK0X1qNN0x2FiUgh+qVgzc9bMdbB7Ej+sHweK5vBxYiHNBdM8N0jsELWV9cJEcUs3gcw1x3disXgR48Js40kqMK19lmwTxeaDohG02Qzl92z4PyTfNXX/JkUOAAAAAElFTkSuQmCC
    position:
      x: 475.3085605951003
      ''y'': 1053.7098666885752
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
        default_value: ''30''
        is_required: false
        is_spinner: false
        final_value: ''30''
        display_name: 分词
      - id: 99
        operator_id: 19
        config_name: window_size
        config_type: number
        default_value: ''6''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 6
        display_name: 窗口大小
      - id: 100
        operator_id: 19
        config_name: lowercase
        config_type: checkbox
        default_value: ''true''
        is_required: false
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
        default_value: ''6''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 6
        display_name: 块数量
      - id: 103
        operator_id: 19
        config_name: hamming_distance
        config_type: number
        default_value: ''4''
        min_value: ''0''
        is_required: false
        is_spinner: false
        spinner_step: ''1''
        final_value: 4
        display_name: 汉明距离
edges:
  - source: node_1755743407480_656
    target: node_1755743417339_310
  - source: node_1755743453405_671
    target: node_1755743461811_356
  - source: node_1755743461811_356
    target: node_1755743489928_91
  - source: node_1755743497094_507
    target: node_1755743505435_969
  - source: node_1755743517278_692
    target: node_1755743527323_910
  - source: node_1755743527323_910
    target: node_1755743533468_245
  - source: node_1755743533468_245
    target: node_1755743543432_421
  - source: node_1755743393403_766
    target: node_1755743399116_476
  - source: node_1755743444173_375
    target: node_1755743453405_671
  - source: node_1755743427415_413
    target: node_1755743437240_279
  - source: node_1755743437240_279
    target: node_1755743444173_375
  - source: node_1755743489928_91
    target: node_1755743497094_507
  - source: node_1755743505435_969
    target: node_1755743517278_692
  - source: node_1755743417339_310
    target: node_1755743427415_413
  - source: node_1755743399116_476
    target: node_1755743407480_656
  - source: node_1755743543432_421
    target: node_1755744114030_934
', '2025-08-21 10:36:16.100906', '2025-08-21 10:51:12.731616');

-- ----------------------------
-- Indexes structure for table algo_templates
-- ----------------------------
CREATE INDEX "ix_algo_templates_id" ON "public"."algo_templates" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table algo_templates
-- ----------------------------
ALTER TABLE "public"."algo_templates" ADD CONSTRAINT "algo_templates_pkey" PRIMARY KEY ("id");

-- Set sequence owner and starting value
ALTER SEQUENCE algo_templates_id_seq OWNED BY algo_templates.id;
-- User data starts from ID 1, template data uses high IDs starting from 9999+
ALTER SEQUENCE algo_templates_id_seq RESTART WITH 1000;
