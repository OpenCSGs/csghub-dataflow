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

 Date: 13/08/2025 17:10:56
*/


-- ----------------------------
-- Table structure for operator_config
-- ----------------------------
DROP TABLE IF EXISTS "public"."operator_config";
CREATE TABLE "public"."operator_config" (
  "id" int8 NOT NULL DEFAULT nextval('operator_config_copy_id_seq'::regclass),
  "operator_id" int8,
  "config_name" varchar(255) COLLATE "pg_catalog"."default",
  "config_type" varchar(255) COLLATE "pg_catalog"."default",
  "select_options" jsonb,
  "default_value" varchar(255) COLLATE "pg_catalog"."default",
  "min_value" varchar(255) COLLATE "pg_catalog"."default",
  "max_value" varchar(255) COLLATE "pg_catalog"."default",
  "slider_step" varchar(255) COLLATE "pg_catalog"."default",
  "is_required" bool,
  "is_spinner" bool,
  "spinner_step" varchar(255) COLLATE "pg_catalog"."default",
  "final_value" text COLLATE "pg_catalog"."default",
  "created_at" timestamp(6),
  "updated_at" timestamp(6)
)
;
COMMENT ON COLUMN "public"."operator_config"."final_value" IS '用户最终选择的值';

-- ----------------------------
-- Records of operator_config
-- ----------------------------
INSERT INTO "public"."operator_config" VALUES (9, 1, 'tokenization', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-25 17:17:10.292128', '2025-07-25 17:17:10.292128');
INSERT INTO "public"."operator_config" VALUES (2, 15, 'tokenization', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-25 17:07:16.881312', '2025-07-25 17:07:16.881312');
INSERT INTO "public"."operator_config" VALUES (60, 45, 'min_ratio', 'slider', NULL, '0', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 16:46:45.199799', '2025-07-29 16:46:45.199799');
INSERT INTO "public"."operator_config" VALUES (61, 45, 'max_ratio', 'slider', NULL, '1', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 16:46:45.199799', '2025-07-29 16:46:45.199799');
INSERT INTO "public"."operator_config" VALUES (125, 54, 'score_field', 'input', 'null', 'score', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-08-13 15:27:30.814927', '2025-08-13 15:27:30.814927');
INSERT INTO "public"."operator_config" VALUES (126, 54, 'min_score', 'number', 'null', '0.6', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-08-13 15:27:30.814927', '2025-08-13 15:27:30.814927');
INSERT INTO "public"."operator_config" VALUES (127, 54, 'max_score', 'number', 'null', '2', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-08-13 15:27:30.814927', '2025-08-13 15:27:30.814927');
INSERT INTO "public"."operator_config" VALUES (10, 1, 'max_ratio', 'slider', NULL, '0.01', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-25 17:17:10.292128', '2025-07-25 17:17:10.292128');
INSERT INTO "public"."operator_config" VALUES (44, 35, 'chars_to_remove', 'input', NULL, '◆●■►▼▲▴∆▻▷❖♡□', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 09:34:21.516557', '2025-07-29 09:34:21.516557');
INSERT INTO "public"."operator_config" VALUES (5, 2, 'rep_len', 'number', NULL, '10', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-25 17:12:04.424873', '2025-07-25 17:12:04.424873');
INSERT INTO "public"."operator_config" VALUES (6, 2, 'min_ratio', 'slider', NULL, '0', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-25 17:12:04.424873', '2025-07-25 17:12:04.424873');
INSERT INTO "public"."operator_config" VALUES (7, 2, 'max_ratio', 'slider', NULL, '0.6', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-25 17:12:04.424873', '2025-07-25 17:12:04.424873');
INSERT INTO "public"."operator_config" VALUES (19, 8, 'prompt_template', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 21:56:42.474364', '2025-07-28 21:56:42.474364');
INSERT INTO "public"."operator_config" VALUES (16, 11, 'hf_model', 'select', '[18]', '18', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 18:10:15.204689', '2025-07-28 18:10:15.204689');
INSERT INTO "public"."operator_config" VALUES (18, 8, 'hf_model', 'select', '[23]', '23', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 21:56:42.474364', '2025-07-28 21:56:42.474364');
INSERT INTO "public"."operator_config" VALUES (13, 13, 'max_len', 'number', NULL, '999999', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-25 17:23:47.885255', '2025-07-25 17:23:47.885255');
INSERT INTO "public"."operator_config" VALUES (34, 21, 'hf_model', 'select', '[24]', '24', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:26:54.728185', '2025-07-28 22:26:54.728185');
INSERT INTO "public"."operator_config" VALUES (12, 13, 'min_len', 'number', NULL, '10', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-25 17:23:47.885255', '2025-07-25 17:23:47.885255');
INSERT INTO "public"."operator_config" VALUES (3, 15, 'max_ratio', 'number', NULL, '999999', NULL, NULL, NULL, 'f', 'f', '1', NULL, '2025-07-25 17:07:16.881312', '2025-07-25 17:07:16.881312');
INSERT INTO "public"."operator_config" VALUES (4, 15, 'min_ratio', 'number', NULL, '0.1', NULL, NULL, NULL, 'f', 'f', '0.01', NULL, '2025-07-25 17:07:16.881312', '2025-07-25 17:07:16.881312');
INSERT INTO "public"."operator_config" VALUES (47, 37, 'lang', 'select', '[15, 16]', '15', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:43:33.224115', '2025-07-29 16:43:33.224115');
INSERT INTO "public"."operator_config" VALUES (55, 42, 'lang', 'select', '[15, 16, 25, 26]', '16', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:45:37.673406', '2025-07-29 16:45:37.673406');
INSERT INTO "public"."operator_config" VALUES (58, 44, 'lang', 'select', '[15, 16]', '15', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:46:34.295683', '2025-07-29 16:46:34.295683');
INSERT INTO "public"."operator_config" VALUES (11, 1, 'use_words_aug', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-25 17:17:10.292128', '2025-07-25 17:17:10.292128');
INSERT INTO "public"."operator_config" VALUES (14, 12, 'lowercase', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-25 17:27:21.32788', '2025-07-25 17:27:21.32788');
INSERT INTO "public"."operator_config" VALUES (73, 20, 'min_action_num', 'number', NULL, '1', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:49:06.949324', '2025-07-29 16:49:06.949324');
INSERT INTO "public"."operator_config" VALUES (67, 48, 'lang', 'select', '[15, 16]', '16', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:47:06.922281', '2025-07-29 16:47:06.922281');
INSERT INTO "public"."operator_config" VALUES (15, 12, 'ignore_non_character', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-25 17:27:21.32788', '2025-07-25 17:27:21.32788');
INSERT INTO "public"."operator_config" VALUES (22, 16, 'spelling_error_word', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:02:58.91576', '2025-07-28 22:02:58.91576');
INSERT INTO "public"."operator_config" VALUES (29, 17, 'replace_similar_word', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:06:37.159089', '2025-07-28 22:06:37.159089');
INSERT INTO "public"."operator_config" VALUES (35, 25, 'inline', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:33:35.455987', '2025-07-28 22:33:35.455987');
INSERT INTO "public"."operator_config" VALUES (43, 34, 'min_repeat_sentence_length', 'number', NULL, '2', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 09:27:45.064897', '2025-07-29 09:27:45.064897');
INSERT INTO "public"."operator_config" VALUES (72, 20, 'lang', 'select', '[15, 16]', '15', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:49:06.949324', '2025-07-29 16:49:06.949324');
INSERT INTO "public"."operator_config" VALUES (45, 36, 'min_col', 'slider', NULL, '2', '2', '20', '1', 'f', 'f', NULL, NULL, '2025-07-29 16:43:07.226271', '2025-07-29 16:43:07.226271');
INSERT INTO "public"."operator_config" VALUES (46, 36, 'max_col', 'slider', NULL, '20', '2', '20', '1', 'f', 'f', NULL, NULL, '2025-07-29 16:43:07.226271', '2025-07-29 16:43:07.226271');
INSERT INTO "public"."operator_config" VALUES (49, 37, 'substrings', 'input', NULL, '.com', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:43:33.224115', '2025-07-29 16:43:33.224115');
INSERT INTO "public"."operator_config" VALUES (74, 50, 'lang', 'select', '[15, 16]', '16', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:50:09.31549', '2025-07-29 16:50:09.31549');
INSERT INTO "public"."operator_config" VALUES (53, 41, 'min_len', 'number', NULL, '10', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:44:17.555527', '2025-07-29 16:44:17.555527');
INSERT INTO "public"."operator_config" VALUES (54, 41, 'max_len', 'number', NULL, '1200', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:44:17.555527', '2025-07-29 16:44:17.555527');
INSERT INTO "public"."operator_config" VALUES (56, 42, 'min_score', 'slider', NULL, '0.8', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 16:45:37.673406', '2025-07-29 16:45:37.673406');
INSERT INTO "public"."operator_config" VALUES (57, 43, 'max_len', 'number', NULL, '7328', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:46:18.568303', '2025-07-29 16:46:18.568303');
INSERT INTO "public"."operator_config" VALUES (1, 43, 'min_len', 'number', NULL, '10', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:46:18.568303', '2025-07-29 16:46:18.568303');
INSERT INTO "public"."operator_config" VALUES (59, 44, 'max_ppl', 'number', NULL, '8000', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:46:34.295683', '2025-07-29 16:46:34.295683');
INSERT INTO "public"."operator_config" VALUES (65, 47, 'min_value', 'number', NULL, '-999999', NULL, NULL, NULL, 'f', 'f', '0.01', NULL, '2025-07-29 16:46:59.774123', '2025-07-29 16:46:59.774123');
INSERT INTO "public"."operator_config" VALUES (66, 47, 'max_value', 'number', NULL, '999999', NULL, NULL, NULL, 'f', 'f', '0.01', NULL, '2025-07-29 16:46:59.774123', '2025-07-29 16:46:59.774123');
INSERT INTO "public"."operator_config" VALUES (50, 38, 'pattern', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:43:42.188461', '2025-07-29 16:43:42.188461');
INSERT INTO "public"."operator_config" VALUES (69, 48, 'min_ratio', 'slider', NULL, '0.3', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 16:47:06.922281', '2025-07-29 16:47:06.922281');
INSERT INTO "public"."operator_config" VALUES (75, 50, 'min_dependency_num', 'number', NULL, '1', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:50:09.31549', '2025-07-29 16:50:09.31549');
INSERT INTO "public"."operator_config" VALUES (51, 38, 'repl', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:43:42.188461', '2025-07-29 16:43:42.188461');
INSERT INTO "public"."operator_config" VALUES (62, 46, 'field_key', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:46:52.665485', '2025-07-29 16:46:52.665485');
INSERT INTO "public"."operator_config" VALUES (64, 47, 'field_key', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:46:59.774123', '2025-07-29 16:46:59.774123');
INSERT INTO "public"."operator_config" VALUES (71, 49, 'suffixes', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:47:13.281359', '2025-07-29 16:47:13.281359');
INSERT INTO "public"."operator_config" VALUES (83, 18, 'min_ratio', 'slider', NULL, '0', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 16:56:04.73067', '2025-07-29 16:56:04.73067');
INSERT INTO "public"."operator_config" VALUES (102, 19, 'num_blocks', 'number', NULL, '10', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:05:32.168602', '2025-07-29 17:05:32.168602');
INSERT INTO "public"."operator_config" VALUES (103, 19, 'hamming_distance', 'number', NULL, '8', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:05:32.168602', '2025-07-29 17:05:32.168602');
INSERT INTO "public"."operator_config" VALUES (121, 14, 'mode', 'select', '[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]', '2', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-25 16:59:37.220901', '2025-07-25 16:59:37.220901');
INSERT INTO "public"."operator_config" VALUES (87, 24, 'min_num', 'number', NULL, '20', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:56:11.800614', '2025-07-29 16:56:11.800614');
INSERT INTO "public"."operator_config" VALUES (88, 24, 'max_num', 'number', NULL, '999999', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:56:11.800614', '2025-07-29 16:56:11.800614');
INSERT INTO "public"."operator_config" VALUES (8, 1, 'lang', 'select', '[15, 16]', '16', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-25 17:17:10.292128', '2025-07-25 17:17:10.292128');
INSERT INTO "public"."operator_config" VALUES (90, 26, 'window_size', 'number', NULL, '5', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:04:52.926481', '2025-07-29 17:04:52.926481');
INSERT INTO "public"."operator_config" VALUES (17, 7, 'normalization', 'select', '[19, 20, 21, 22]', '19', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 21:51:46.965124', '2025-07-28 21:51:46.965124');
INSERT INTO "public"."operator_config" VALUES (52, 39, 'lang', 'select', '[15, 16]', '15', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:43:50.685717', '2025-07-29 16:43:50.685717');
INSERT INTO "public"."operator_config" VALUES (95, 26, 'num_bands', 'number', NULL, NULL, '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:04:52.926481', '2025-07-29 17:04:52.926481');
INSERT INTO "public"."operator_config" VALUES (96, 26, 'num_rows_per_band', 'number', NULL, NULL, '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:04:52.926481', '2025-07-29 17:04:52.926481');
INSERT INTO "public"."operator_config" VALUES (84, 18, 'max_ratio', 'slider', NULL, '0.5', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 16:56:04.73067', '2025-07-29 16:56:04.73067');
INSERT INTO "public"."operator_config" VALUES (77, 51, 'hf_tokenizer', 'select', '[29]', '29', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:55:55.235961', '2025-07-29 16:55:55.235961');
INSERT INTO "public"."operator_config" VALUES (76, 50, 'any_or_all', 'select', '[27, 28]', '28', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:50:09.31549', '2025-07-29 16:50:09.31549');
INSERT INTO "public"."operator_config" VALUES (105, 27, 'top_ratio', 'slider', NULL, '0', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 17:05:42.414523', '2025-07-29 17:05:42.414523');
INSERT INTO "public"."operator_config" VALUES (106, 27, 'topk', 'number', NULL, '1', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:05:42.414523', '2025-07-29 17:05:42.414523');
INSERT INTO "public"."operator_config" VALUES (80, 18, 'lang', 'select', '[15, 16]', '15', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:56:04.73067', '2025-07-29 16:56:04.73067');
INSERT INTO "public"."operator_config" VALUES (108, 28, 'select_ratio', 'slider', NULL, '0', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 17:05:48.123415', '2025-07-29 17:05:48.123415');
INSERT INTO "public"."operator_config" VALUES (109, 28, 'select_num', 'number', NULL, '1', '0', NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:05:48.123415', '2025-07-29 17:05:48.123415');
INSERT INTO "public"."operator_config" VALUES (85, 24, 'lang', 'select', '[15, 16]', '15', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:56:11.800614', '2025-07-29 16:56:11.800614');
INSERT INTO "public"."operator_config" VALUES (111, 29, 'lower_percentile', 'slider', NULL, '0', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 17:05:56.444067', '2025-07-29 17:05:56.444067');
INSERT INTO "public"."operator_config" VALUES (128, 55, 'hash_func', 'input', 'null', 'md5', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-08-13 15:34:00.021752', '2025-08-13 15:34:00.021752');
INSERT INTO "public"."operator_config" VALUES (118, 30, 'reverse', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:06:02.760052', '2025-07-29 17:06:02.760052');
INSERT INTO "public"."operator_config" VALUES (91, 26, 'lowercase', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:04:52.926481', '2025-07-29 17:04:52.926481');
INSERT INTO "public"."operator_config" VALUES (107, 27, 'reverse', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:05:42.414523', '2025-07-29 17:05:42.414523');
INSERT INTO "public"."operator_config" VALUES (42, 34, 'ignore_special_character', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 09:27:45.064897', '2025-07-29 09:27:45.064897');
INSERT INTO "public"."operator_config" VALUES (70, 48, 'use_words_aug', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:47:06.922281', '2025-07-29 16:47:06.922281');
INSERT INTO "public"."operator_config" VALUES (33, 17, 'replace_equivalent_num', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:06:37.159089', '2025-07-28 22:06:37.159089');
INSERT INTO "public"."operator_config" VALUES (129, 55, 'initial_capacity', 'number', 'null', '100', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-08-13 15:34:00.021752', '2025-08-13 15:34:00.021752');
INSERT INTO "public"."operator_config" VALUES (26, 16, 'delete_random_char', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:02:58.91576', '2025-07-28 22:02:58.91576');
INSERT INTO "public"."operator_config" VALUES (100, 19, 'lowercase', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:05:32.168602', '2025-07-29 17:05:32.168602');
INSERT INTO "public"."operator_config" VALUES (130, 56, 'web_text_max_len', 'number', 'null', '800', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-08-13 15:36:12.930816', '2025-08-13 15:36:12.930816');
INSERT INTO "public"."operator_config" VALUES (131, 57, 'is_drop', 'checkbox', 'null', 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-08-13 15:37:25.159622', '2025-08-13 15:37:25.159622');
INSERT INTO "public"."operator_config" VALUES (81, 18, 'tokenization', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:56:04.73067', '2025-07-29 16:56:04.73067');
INSERT INTO "public"."operator_config" VALUES (98, 19, 'tokenization', 'select', '[30, 31, 32]', '32', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:05:32.168602', '2025-07-29 17:05:32.168602');
INSERT INTO "public"."operator_config" VALUES (119, 32, 'min_len', 'number', NULL, '1', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 09:23:12.623326', '2025-07-29 09:23:12.623326');
INSERT INTO "public"."operator_config" VALUES (120, 32, 'max_len', 'number', NULL, '9999999', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 09:23:12.623326', '2025-07-29 09:23:12.623326');
INSERT INTO "public"."operator_config" VALUES (116, 30, 'top_ratio', 'slider', NULL, '0', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 17:06:02.760052', '2025-07-29 17:06:02.760052');
INSERT INTO "public"."operator_config" VALUES (78, 51, 'min_num', 'number', NULL, '10', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:55:55.235961', '2025-07-29 16:55:55.235961');
INSERT INTO "public"."operator_config" VALUES (89, 26, 'tokenization', 'select', '[30, 31, 32, 33]', '30', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:04:52.926481', '2025-07-29 17:04:52.926481');
INSERT INTO "public"."operator_config" VALUES (86, 24, 'tokenization', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:56:11.800614', '2025-07-29 16:56:11.800614');
INSERT INTO "public"."operator_config" VALUES (79, 51, 'max_num', 'number', NULL, '999999', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:55:55.235961', '2025-07-29 16:55:55.235961');
INSERT INTO "public"."operator_config" VALUES (82, 18, 'rep_len', 'number', NULL, '10', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 16:56:04.73067', '2025-07-29 16:56:04.73067');
INSERT INTO "public"."operator_config" VALUES (112, 29, 'upper_percentile', 'slider', NULL, '0', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 17:05:56.444067', '2025-07-29 17:05:56.444067');
INSERT INTO "public"."operator_config" VALUES (113, 29, 'lower_rank', 'number', NULL, '1', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:05:56.444067', '2025-07-29 17:05:56.444067');
INSERT INTO "public"."operator_config" VALUES (114, 29, 'upper_rank', 'number', NULL, '1', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:05:56.444067', '2025-07-29 17:05:56.444067');
INSERT INTO "public"."operator_config" VALUES (93, 26, 'num_permutations', 'number', NULL, '256', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:04:52.926481', '2025-07-29 17:04:52.926481');
INSERT INTO "public"."operator_config" VALUES (117, 30, 'topk', 'number', NULL, '1', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:06:02.760052', '2025-07-29 17:06:02.760052');
INSERT INTO "public"."operator_config" VALUES (99, 19, 'window_size', 'number', NULL, '4', '0', NULL, NULL, 'f', 'f', '1', NULL, '2025-07-29 17:05:32.168602', '2025-07-29 17:05:32.168602');
INSERT INTO "public"."operator_config" VALUES (94, 26, 'jaccard_threshold', 'slider', NULL, '0.7', '0', '1', '0.01', 'f', 'f', NULL, NULL, '2025-07-29 17:04:52.926481', '2025-07-29 17:04:52.926481');
INSERT INTO "public"."operator_config" VALUES (30, 17, 'swap_random_word', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:06:37.159089', '2025-07-28 22:06:37.159089');
INSERT INTO "public"."operator_config" VALUES (92, 26, 'ignore_pattern', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:04:52.926481', '2025-07-29 17:04:52.926481');
INSERT INTO "public"."operator_config" VALUES (97, 26, 'tokenizer_model', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:04:52.926481', '2025-07-29 17:04:52.926481');
INSERT INTO "public"."operator_config" VALUES (104, 27, 'field_key', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:05:42.414523', '2025-07-29 17:05:42.414523');
INSERT INTO "public"."operator_config" VALUES (110, 29, 'field_key', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:05:56.444067', '2025-07-29 17:05:56.444067');
INSERT INTO "public"."operator_config" VALUES (63, 46, 'target_value', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:46:52.665485', '2025-07-29 16:46:52.665485');
INSERT INTO "public"."operator_config" VALUES (115, 30, 'field_key', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:06:02.760052', '2025-07-29 17:06:02.760052');
INSERT INTO "public"."operator_config" VALUES (101, 19, 'ignore_pattern', 'input', NULL, NULL, NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 17:05:32.168602', '2025-07-29 17:05:32.168602');
INSERT INTO "public"."operator_config" VALUES (68, 48, 'tokenization', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:47:06.922281', '2025-07-29 16:47:06.922281');
INSERT INTO "public"."operator_config" VALUES (48, 37, 'tokenization', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 16:43:33.224115', '2025-07-29 16:43:33.224115');
INSERT INTO "public"."operator_config" VALUES (31, 17, 'delete_random_char', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:06:37.159089', '2025-07-28 22:06:37.159089');
INSERT INTO "public"."operator_config" VALUES (32, 17, 'swap_random_char', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:06:37.159089', '2025-07-28 22:06:37.159089');
INSERT INTO "public"."operator_config" VALUES (36, 25, 'multiline', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:33:35.455987', '2025-07-28 22:33:35.455987');
INSERT INTO "public"."operator_config" VALUES (37, 31, 'drop_no_head', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:35:47.968904', '2025-07-28 22:35:47.968904');
INSERT INTO "public"."operator_config" VALUES (38, 33, 'keep_alphabet', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 09:25:10.277725', '2025-07-29 09:25:10.277725');
INSERT INTO "public"."operator_config" VALUES (39, 33, 'keep_number', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 09:25:10.277725', '2025-07-29 09:25:10.277725');
INSERT INTO "public"."operator_config" VALUES (40, 33, 'keep_punc', 'checkbox', NULL, 'true', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 09:25:10.277725', '2025-07-29 09:25:10.277725');
INSERT INTO "public"."operator_config" VALUES (41, 34, 'lowercase', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-29 09:27:45.064897', '2025-07-29 09:27:45.064897');
INSERT INTO "public"."operator_config" VALUES (21, 16, 'swap_random_word', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:02:58.91576', '2025-07-28 22:02:58.91576');
INSERT INTO "public"."operator_config" VALUES (20, 16, 'delete_random_word', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:02:58.91576', '2025-07-28 22:02:58.91576');
INSERT INTO "public"."operator_config" VALUES (23, 16, 'split_random_word', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:02:58.91576', '2025-07-28 22:02:58.91576');
INSERT INTO "public"."operator_config" VALUES (24, 16, 'keyboard_error_char', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:02:58.91576', '2025-07-28 22:02:58.91576');
INSERT INTO "public"."operator_config" VALUES (25, 16, 'ocr_error_char', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:02:58.91576', '2025-07-28 22:02:58.91576');
INSERT INTO "public"."operator_config" VALUES (27, 16, 'swap_random_char', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:02:58.91576', '2025-07-28 22:02:58.91576');
INSERT INTO "public"."operator_config" VALUES (28, 16, 'insert_random_char', 'checkbox', NULL, 'false', NULL, NULL, NULL, 'f', 'f', NULL, NULL, '2025-07-28 22:02:58.91576', '2025-07-28 22:02:58.91576');

-- ----------------------------
-- Indexes structure for table operator_config
-- ----------------------------
CREATE INDEX "ix_operator_config_copy_id" ON "public"."operator_config" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table operator_config
-- ----------------------------
ALTER TABLE "public"."operator_config" ADD CONSTRAINT "operator_config_copy_pkey" PRIMARY KEY ("id");
