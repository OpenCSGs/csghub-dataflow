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

 Date: 20/08/2025 11:01:39
*/


-- ----------------------------
-- Table structure for operator_info
-- ----------------------------
DROP TABLE IF EXISTS "public"."operator_info";
-- Drop and recreate sequence to ensure clean state
DROP SEQUENCE IF EXISTS operator_info_id_seq;
CREATE SEQUENCE operator_info_id_seq;
CREATE TABLE "public"."operator_info" (
  "id" int8 NOT NULL DEFAULT nextval('operator_info_id_seq'::regclass),
  "operator_name" varchar(255) COLLATE "pg_catalog"."default",
  "operator_type" varchar(255) COLLATE "pg_catalog"."default",
  "execution_order" int4,
  "is_enabled" bool,
  "description" text COLLATE "pg_catalog"."default",
  "before_cleaning" text COLLATE "pg_catalog"."default",
  "after_cleaning" text COLLATE "pg_catalog"."default",
  "icon" text COLLATE "pg_catalog"."default",
  "created_at" timestamp(6),
  "updated_at" timestamp(6),
  "is_public" bool
)
;

-- ----------------------------
-- Records of operator_info
-- ----------------------------
INSERT INTO "public"."operator_info" VALUES (8, 'generate_code_qa_pair_mapper', 'Mapper', 0, 't', 'Mapper to generate new instruction data based on code.
    ', 'def hello_world():
    print("Hello, World!")
hello_world()', 'message:[{"input": "create hello word function by python", "response": "def hello_world():
    print("Hello, World!")
hello_world()" }]', 'api/v1/dataflow/real_static_files/operator/9057f5d6-2116-4a85-a30b-9038f0208281.png', '2025-07-28 21:56:42.429', '2025-07-30 14:38:18.883288', 't');
INSERT INTO "public"."operator_info" VALUES (9, 'clean_ip_mapper', 'Mapper', 0, 't', 'Mapper to clean ipv4 and ipv6 address in text samples.', 'ftp://example.com/188.46.244.216my-page.html', 'ftp://example.com/my-page.html', 'api/v1/dataflow/real_static_files/operator/539ee039-5e9c-4268-a3e9-bca7a64ece8f.png', '2025-07-26 14:21:23.800177', '2025-07-30 14:37:33.257106', 't');
INSERT INTO "public"."operator_info" VALUES (10, 'clean_html_mapper', 'Mapper', 0, 't', 'Mapper to clean html code in text samples.', '<a href=''https://www.example.com/file.html?;name=Test'' rel=''noopener noreferrer'' target=''_blank''>Test</a>', 'Test', 'api/v1/dataflow/real_static_files/operator/2155c5d7-3a33-4f75-988d-265abac54887.png', '2025-07-26 14:20:45.188039', '2025-07-30 14:38:25.833147', 't');
INSERT INTO "public"."operator_info" VALUES (13, 'text_length_filter', 'Filter', 0, 't', 'Filter to keep samples with total text length within a specific
    range.', 'Today is Sund Sund Sund Sund Sund Sunda and it''s a happy day!', NULL, 'api/v1/dataflow/real_static_files/operator/3ffa0e42-974a-4b14-ab08-9cb259f83512.png', '2025-07-25 17:23:47.854313', '2025-07-30 14:40:10.303067', 't');
INSERT INTO "public"."operator_info" VALUES (14, 'chinese_convert_mapper', 'Mapper', 0, 't', 'Mapper to convert Chinese between Traditional Chinese, Simplified Chinese and Japanese Kanji.', '这是几个简体字，会被转换为繁体字', '這是幾個簡體字，會被轉換爲繁體字', 'api/v1/dataflow/real_static_files/operator/26269c88-3453-4c8b-8333-ec6c9c939109.png', '2025-07-25 16:59:37.14472', '2025-07-30 14:40:18.970169', 't');
INSERT INTO "public"."operator_info" VALUES (15, 'alphanumeric_filter', 'Filter', 0, 't', 'Filter to keep samples with alphabet/numeric ratio within a specific
    range.', 'emoji表情测试下😊，😸31231
', NULL, 'api/v1/dataflow/real_static_files/operator/7f317dc9-ba84-4660-b50f-f96b39049dba.png', '2025-07-25 17:07:16.848742', '2025-07-30 14:40:26.711944', 't');
INSERT INTO "public"."operator_info" VALUES (16, 'nlpaug_en_mapper', 'Mapper', 0, 't', 'Mapper to simply augment samples in English based on nlpaug library.', 'I am going to the park.', 'I am proceeding to the park.', 'api/v1/dataflow/real_static_files/operator/c47fc2a0-0c8e-4fd0-981e-9947903a608c.png', '2025-07-28 22:02:58.658819', '2025-07-30 14:40:34.720072', 't');
INSERT INTO "public"."operator_info" VALUES (17, 'nlpcda_zh_mapper', 'Mapper', 0, 't', 'Mapper to simply augment samples in Chinese based on nlpcda library.', '这里一共有5种不同的数据增强方法', '这里一共有伍种不同的数据增强方法', 'api/v1/dataflow/real_static_files/operator/983021a9-a149-4fb3-afe1-989f3d00fc9d.png', '2025-07-28 22:06:37.125394', '2025-07-30 14:40:43.117797', 't');
INSERT INTO "public"."operator_info" VALUES (18, 'word_repetition_filter', 'Filter', 0, 't', 'Filter to keep samples with word-level n-gram repetition ratio within a
    specific range.', '根据算子使用使用使用使用安装方案确定', NULL, 'api/v1/dataflow/real_static_files/operator/8c65e9aa-898e-4d25-aac2-9741623e7bb6.png', '2025-07-29 16:56:04.709136', '2025-07-30 14:40:57.296525', 't');
INSERT INTO "public"."operator_info" VALUES (19, 'document_simhash_deduplicator', 'Deduplicator', 0, 't', 'Deduplicator to deduplicate samples at document-level using SimHash.', NULL, NULL, 'api/v1/dataflow/real_static_files/operator/57593071-d5c2-4277-90af-99c524b7ea8c.png', '2025-07-29 17:05:32.159066', '2025-07-30 14:39:46.855227', 't');
INSERT INTO "public"."operator_info" VALUES (20, 'text_action_filter', 'Filter', 0, 't', 'Filter to keep texts those contain actions in the text..', '我有一只猫，它是一只猫', NULL, 'api/v1/dataflow/real_static_files/operator/0be7e20d-9f2f-4861-9b7e-485dd11dabed.png', '2025-07-29 16:49:06.936807', '2025-07-30 14:41:06.691885', 't');
INSERT INTO "public"."operator_info" VALUES (23, 'remove_bibliography_mapper', 'Mapper', 0, 't', 'Mapper to remove bibliography at the end of documents in Latex
    samples.', '%%
%% This is file `sample-sigconf.tex\clearpage
\bibliographystyle{ACM-Reference-Format}
\bibliography{sample-base}
\end{document}
\endinput
%%
%% End of file `sample-sigconf.tex''.
', '%%
%% This is file `sample-sigconf.tex\clearpage
\bibliographystyle{ACM-Reference-Format}
', 'api/v1/dataflow/real_static_files/operator/fab1e123-e28f-4f52-a03c-41075147723a.png', '2025-07-28 22:30:47.636405', '2025-07-30 14:42:09.515676', 't');
INSERT INTO "public"."operator_info" VALUES (24, 'words_num_filter', 'Filter', 0, 't', 'Filter to keep samples with total words number within a specific
    range.', '根据算子使用使用使用使用安装方案确定', NULL, 'api/v1/dataflow/real_static_files/operator/89e8db71-801e-4241-a637-1e28d55ee53b.png', '2025-07-29 16:56:11.789035', '2025-07-30 14:42:17.729019', 't');
INSERT INTO "public"."operator_info" VALUES (27, 'frequency_specified_field_selector', 'Selector', 0, 't', 'Selector to select samples based on the sorted frequency of specified
    field.', '{''text'': ''，。、„”“«»１」「《》´∶：？！'',''count'': None,''meta'': {    ''suffix'': ''.html'',    ''key1'': {        ''key2'': {            ''count'': 18        },        ''count'': 48    }}}', NULL, 'api/v1/dataflow/real_static_files/operator/f04dcec3-5618-438a-a47a-3252b88f08cf.png', '2025-07-29 17:05:42.404482', '2025-07-30 14:42:38.548727', 't');
INSERT INTO "public"."operator_info" VALUES (28, 'random_selector', 'Selector', 0, 't', 'Selector to random select samples. ', '{''text'': ''，。、„”“«»１」「《》´∶：？！'',''count'': None,''meta'': {    ''suffix'': ''.html'',    ''key1'': {        ''key2'': {            ''count'': 18        },        ''count'': 48    }}}', NULL, 'api/v1/dataflow/real_static_files/operator/7375d836-71d1-4451-ad59-20e8a624e8d9.png', '2025-07-29 17:05:48.112859', '2025-07-30 14:42:45.36178', 't');
INSERT INTO "public"."operator_info" VALUES (29, 'range_specified_field_selector', 'Selector', 0, 't', 'Selector to select a range of samples based on the sorted
    specified field value from smallest to largest. ', '{''text'': ''，。、„”“«»１」「《》´∶：？！'',''count'': None,''meta'': {    ''suffix'': ''.html'',    ''key1'': {        ''key2'': {            ''count'': 18        },        ''count'': 48    }}}', NULL, 'api/v1/dataflow/real_static_files/operator/0e72f0dc-8ac4-40eb-9fa5-0219e7da0346.png', '2025-07-29 17:05:56.428539', '2025-07-30 14:42:53.870455', 't');
INSERT INTO "public"."operator_info" VALUES (30, 'topk_specified_field_selector', '', 0, 't', NULL, NULL, NULL, 'api/v1/dataflow/real_static_files/operator/2ef54c00-67b1-4b39-bc2b-682e6a7a7b59.png', '2025-07-29 17:06:02.746543', '2025-07-30 14:43:04.545865', 't');
INSERT INTO "public"."operator_info" VALUES (35, 'remove_specific_chars_mapper', 'Mapper', 0, 't', 'Mapper to clean specific chars in text samples. now support: ◆●■►▼▲▴∆▻▷❖♡□', '多个●■►▼这样的特殊字符可以►▼▲▴∆吗？', '多个这样的特殊字符可以吗？', 'api/v1/dataflow/real_static_files/operator/69ea24c1-b010-4ab4-8735-ccf9338fb3ec.png', '2025-07-29 09:34:21.502534', '2025-07-30 14:43:50.369974', 't');
INSERT INTO "public"."operator_info" VALUES (43, 'maximum_line_length_filter', 'Filter', 0, 't', 'Filter to keep samples with maximum line length within a specific
    range.', 'Today is Sund Sund Sund Sunda and it''s a happy day!
You know', NULL, 'api/v1/dataflow/real_static_files/operator/a8b4ff5e-2d12-40c5-b483-c6f4c8492ef5.png', '2025-07-29 16:46:18.557698', '2025-07-30 14:50:01.143674', 't');
INSERT INTO "public"."operator_info" VALUES (44, 'perplexity_filter', 'Filter', 0, 't', 'Filter to keep samples with perplexity score less than a specific max
    value.', 'Today is Sund Sund Sund Sunda and it''s a happy day!
You know', NULL, 'api/v1/dataflow/real_static_files/operator/4b7e5905-74fe-42ba-97a5-b873e21421fa.png', '2025-07-29 16:46:34.277471', '2025-07-30 14:45:46.690086', 't');
INSERT INTO "public"."operator_info" VALUES (54, 'text_high_score_filter', 'Filter', 0, 't', 'Filter text samples based on score value range in specified field.', NULL, NULL, 'api/v1/dataflow/real_static_files/operator/789a36c3-9b6b-4a63-86e0-66a2029fadca.png', '2025-08-13 15:27:30.79789', '2025-08-18 13:48:46.334386', 't');
INSERT INTO "public"."operator_info" VALUES (1, 'flagged_words_filter', 'Filter', 0, 't', 'Filter to keep samples with flagged-word ratio less than a specific max
    value.', '基于前一步结果，除掉骂人、脏字等污秽数据和敏感词', NULL, 'api/v1/dataflow/real_static_files/operator/7053eed0-b6a8-4a8a-9387-e1a0413fbce7.png', '2025-07-25 17:17:10.255559', '2025-07-30 14:34:12.397997', 't');
INSERT INTO "public"."operator_info" VALUES (2, 'character_repetition_filter', 'Filter', 0, 't', 'Filter to keep samples with char-level n-gram repetition ratio within a
    specific range.', 'Today is Sund Sund Sund Sund Sund Sunda and it''s a happy day!', NULL, 'api/v1/dataflow/real_static_files/operator/cc49d862-693b-4107-9353-3b40593b1fd8.png', '2025-07-25 17:12:04.389578', '2025-07-30 14:35:39.735916', 't');
INSERT INTO "public"."operator_info" VALUES (5, 'clean_links_mapper', 'Mapper', 0, 't', 'Mapper to clean links like http/https/ftp in text samples.', '这是个测试,https://example.com/my-page.html?param1=value1&param2=value2', '这是个测试', 'api/v1/dataflow/real_static_files/operator/5b10a3d2-7548-4921-a1c9-9acb7196f0dd.png', '2025-07-26 14:22:26.486592', '2025-07-30 14:37:46.253479', 't');
INSERT INTO "public"."operator_info" VALUES (7, 'fix_unicode_mapper', 'Mapper', 0, 't', 'Mapper to fix unicode errors in text samples.', 'The Mona Lisa doesnÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢t have eyebrows.', 'The Mona Lisa doesn''t have eyebrows.', 'api/v1/dataflow/real_static_files/operator/9930ff2d-167b-426d-8294-901f5dbf0342.png', '2025-07-28 21:51:46.932663', '2025-07-30 14:38:09.802052', 't');
INSERT INTO "public"."operator_info" VALUES (22, 'punctuation_normalization_mapper', 'Mapper', 0, 't', 'Mapper to normalize unicode punctuations to English punctuations in text samples.', '，。、„”“«»１」「《》´∶：？！（）；–—．～’…━〈〉【】％►', ',.,""""""""""''::?!();- - . ~''...-<>[]%-', 'api/v1/dataflow/real_static_files/operator/111cb13a-b085-49d8-9684-397c7ffa4b08.png', '2025-07-28 22:28:48.966792', '2025-07-30 14:41:56.607038', 't');
INSERT INTO "public"."operator_info" VALUES (39, 'sentence_split_mapper', 'Mapper', 0, 't', 'Mapper to split text samples to sentences.', 'Smithfield employs 3,700 people at its plant in Sioux Falls, South Dakota. The plant slaughters 19,500 pigs a day — 5 percent of U.S. pork.', 'Smithfield employs 3,700 people at its plant in Sioux Falls, South Dakota.
The plant slaughters 19,500 pigs a day — 5 percent of U.S. pork.', 'api/v1/dataflow/real_static_files/operator/1e91ba97-1067-4f05-8654-375f6e00eadd.png', '2025-07-29 16:43:50.676209', '2025-07-30 14:44:36.669174', 't');
INSERT INTO "public"."operator_info" VALUES (40, 'whitespace_normalization_mapper', 'Mapper', 0, 't', '
    Mapper to normalize different kinds of whitespaces to whitespace '' '' (0x20)
    in text samples.

    Different kinds of whitespaces can be found here:
    https://en.wikipedia.org/wiki/Whitespace_character
    ', 'hello world', 'world hello', 'api/v1/dataflow/real_static_files/operator/b0aed94b-84b3-416a-b91b-444cca15ea02.png', '2025-07-29 16:43:56.227611', '2025-07-30 14:44:48.577719', 't');
INSERT INTO "public"."operator_info" VALUES (41, 'average_line_length_filter', 'Filter', 0, 't', 'Filter to keep samples with average line length within a specific
    range.', 'short', NULL, 'api/v1/dataflow/real_static_files/operator/21e83be6-d67e-4e1e-ba2c-4ae1c10b7d18.png', '2025-07-29 16:44:17.527904', '2025-07-30 14:44:58.221537', 't');
INSERT INTO "public"."operator_info" VALUES (42, 'language_id_score_filter', 'Filter', 0, 't', '
    Filter to keep samples in a specific language with confidence score
    larger than a specific min value.
    ', 'Today is Sund Sund Sund Sunda and it''s a happy day!
You know', NULL, 'api/v1/dataflow/real_static_files/operator/fe9da7e9-ff19-4c92-b1cc-6456ab855441.png', '2025-07-29 16:45:37.653325', '2025-07-30 14:45:11.857961', 't');
INSERT INTO "public"."operator_info" VALUES (45, 'special_characters_filter', 'Filter', 0, 't', 'Filter to keep samples with special-char ratio within a specific
    range.', 'emoji表情测试下😊，😸31231', NULL, 'api/v1/dataflow/real_static_files/operator/ac509abf-55ba-47c7-8b5e-d5080dfbe3d9.png', '2025-07-29 16:46:45.170847', '2025-07-30 14:45:55.891903', 't');
INSERT INTO "public"."operator_info" VALUES (46, 'specified_field_filter', 'Filter', 0, 't', '
    Filter based on specified field information.

    If the specified field information in the sample is not within the
    specified target value, the sample will be filtered.
    ', '{''text'': ''中文也是一个字算一个长度'',''meta'': {    ''suffix'': ''.txt'',    ''star'': 100}}', NULL, 'api/v1/dataflow/real_static_files/operator/37412326-3231-4e0a-bc36-aa1e7f79dce4.png', '2025-07-29 16:46:52.653937', '2025-07-30 14:46:06.188056', 't');
INSERT INTO "public"."operator_info" VALUES (47, 'specified_numeric_field_filter', 'Filter', 0, 't', '
    Filter based on specified numeric field information.

    If the specified numeric information in the sample is not within the
    specified range, the sample will be filtered.
    ', '{''text'': ''中文也是一个字算一个长度'',''meta'': {    ''suffix'': ''.txt'',    ''star'': 100}}', NULL, 'api/v1/dataflow/real_static_files/operator/ecd85741-b01b-4447-b21a-d19df67aeec6.png', '2025-07-29 16:46:59.738091', '2025-07-30 14:46:15.195593', 't');
INSERT INTO "public"."operator_info" VALUES (48, 'stopwords_filter', 'Filter', 0, 't', 'Filter to keep samples with stopword ratio larger than a specific min
    value.', '?', NULL, 'api/v1/dataflow/real_static_files/operator/c584cde4-a0d4-4a47-9d69-1f80e1909add.png', '2025-07-29 16:47:06.907246', '2025-07-30 14:52:50.980428', 't');
INSERT INTO "public"."operator_info" VALUES (49, 'suffix_filter', 'Filter', 0, 't', 'Filter to keep samples with specified suffix.', '{''text'': ''中文也是一个字算一个长度'',Fields.suffix: ''.txt''}', NULL, 'api/v1/dataflow/real_static_files/operator/68fb57ba-1f98-436c-a929-daafce8d05d6.png', '2025-07-29 16:47:13.268523', '2025-07-30 14:46:36.201431', 't');
INSERT INTO "public"."operator_info" VALUES (50, 'text_entity_dependency_filter', 'Filter', 0, 't', '
    Identify the entities in the text which are independent with other token,
    and filter them. The text containing no entities will be omitted.
    ', '上上下下左左右右', NULL, 'api/v1/dataflow/real_static_files/operator/336427a9-2ab8-430e-a45a-2a680a811925.png', '2025-07-29 16:50:09.302578', '2025-07-30 14:46:45.668245', 't');
INSERT INTO "public"."operator_info" VALUES (51, 'token_num_filter', 'Filter', 0, 't', 'Filter to keep samples with total token number within a specific
    range.', 'Today is Sund Sund Sund Sund Sund Sunda and it''s a happy day!', NULL, 'api/v1/dataflow/real_static_files/operator/438a3016-4ca3-4c21-8ed1-ffe0306b935a.png', '2025-07-29 16:55:55.213657', '2025-07-30 14:46:54.05137', 't');
INSERT INTO "public"."operator_info" VALUES (56, 'make_cosmopedia_mapper', 'Mapper', 0, 't', 'Mapper to generate synthetic tutorial data from seed text samples.', 'How to Train Your Dog to Sit', 'Training your dog to sit is one of the most fundamental commands...', 'api/v1/dataflow/real_static_files/operator/376559b2-b641-4318-9f2f-b854b7ccc1e4.png', '2025-08-13 15:36:12.917019', '2025-08-18 13:49:12.109903', 't');
INSERT INTO "public"."operator_info" VALUES (57, 'gather_generated_data', 'Filter', 0, 't', 'Filter for collecting and processing generated data.', '基于前一步结果，除掉 || 与 <|im_end|> 字符并且过滤 出 content 为空的数据 ', '', 'api/v1/dataflow/real_static_files/operator/83e4db09-5585-418a-8cd2-8a56093436bb.png', '2025-08-13 15:37:25.142613', '2025-08-18 13:49:21.645847', 't');
INSERT INTO "public"."operator_info" VALUES (11, 'extract_qa_mapper', 'Mapper', 0, 't', '
    Mapper to extract question and answer pair from text samples.
    Recommended model list: [
        ''alibaba-pai/pai-qwen1_5-7b-doc2qa'',
    ]
    These recommended models are all trained with Chinese data
    and are suitable for Chinese.
    ', '蒙古国的首都是乌兰巴托（Ulaanbaatar）', 'Human: 请问蒙古国的首都是哪里？Assistant: 你好，根据提供的信息，蒙古国的首都是乌兰巴托（Ulaanbaatar）', 'api/v1/dataflow/real_static_files/operator/2bc92637-2ca6-45d8-ab15-d54a6afe6706.png', '2025-07-28 18:10:15.17163', '2025-07-30 14:41:24.156999', 't');
INSERT INTO "public"."operator_info" VALUES (12, 'document_deduplicator', 'Deduplicator', 0, 't', '
    Deduplicator to deduplicate samples at document-level using exact matching.

    Using md5 hash to deduplicate samples.
    ', '{    ''text'':    ''This paper proposed a novel method on LLM pretraining.''},{    ''text'':    ''This paper proposed a novel method on LLM pretraining.''}', '{    ''text'':    ''This paper proposed a novel method on LLM pretraining.''},', 'api/v1/dataflow/real_static_files/operator/205a63c8-fa19-4542-add1-1b0744b95977.png', '2025-07-25 17:27:21.293129', '2025-07-30 14:39:24.563715', 't');
INSERT INTO "public"."operator_info" VALUES (26, 'document_minhash_deduplicator', 'Deduplicator', 0, 't', 'Deduplicator to deduplicate samples at document-level using MinHashLSH.

    Different from simhash, minhash is stored as bytes, so they won''t be
    kept in the final dataset.
    ', NULL, NULL, 'api/v1/dataflow/real_static_files/operator/898a3cb8-fa01-4a7f-9a92-5de322bc4802.png', '2025-07-29 17:04:52.917296', '2025-07-30 14:40:00.661726', 't');
INSERT INTO "public"."operator_info" VALUES (31, 'remove_header_mapper', 'Mapper', 0, 't', 'Mapper to remove headers at the beginning of documents in Latex
    samples.', '%% %% This is file `sample-sigconf.tex'', %% The first command in your LaTeX source must be the \documentclass command. \documentclass[sigconf,review,anonymous]{acmart} %% NOTE that a single column version is required for %% submission and peer review. This can be done by changing \input{math_commands.tex} %% end of the preamble, start of the body of the document source. \begin{document} %% The "title" command has an optional parameter, \title{Hierarchical Cross Contrastive Learning of Visual Representations} %% %% The "author" command and its associated commands are used to define %% the authors and their affiliations. \author{Hesen Chen} \affiliation{% \institution{Alibaba Group} \city{Beijing} \country{China}} \email{hesen.chs@alibaba-inc.com} %% By default, the full list of authors will be used in the page \begin{abstract}The rapid \end{abstract} \begin{CCSXML} \ccsdesc[500]{Computing methodologies~Image representations} %% Keywords. The author(s) should pick words that accurately describe \keywords{self-supervised, ontrastive Learning, hierarchical projection, cross-level} %% page. \begin{teaserfigure} \end{teaserfigure} %% This command processes the author and affiliation and title \maketitle \section{Introduction} \begin{itemize} \end{itemize} \section{Related Work} \label{gen_inst} Self-supervised \section{Method} \label{method}In this section, \subsection{Framework} kkk \subsection{Cross Contrastive Loss} Since $\sZ^n$ are extracted \subsection{Implementation details} \textbf{Image augmentations} We use \textbf{Architecture} We use \textbf{Optimization} We adapt \section{Experiments} \label{experiments}In this section \subsection{Linear and Semi-Supervised Evaluations on ImageNet} \textbf{Linear evaluation on ImageNet} We firs \textbf{Semi-supervised learning on ImageNet} We simply \subsection{Transfer to other datasets and tasks} \textbf{Image classification with fixed features} We follow \section{Ablations} We present \subsection{Influence of hierarchical projection head and cross contrastive loss} get out \subsection{Levels and depth of projector network} \end{center} \caption{\label{figure3} \textbf{Different way of cross-correlation on 3 level hierarchical projection head.} ''='' denotes stop gradient.} \end{figure} \subsection{Analyze of} In this \textbf{Similarity between} Using SimSiam \textbf{Feature similarity} We extracted \section{Conclusion} We propose HCCL \clearpage \bibliographystyle{ACM-Reference-Format} \bibliography{sample-base} \end{document} \endinput %% %% End of file `sample-sigconf.tex''.

', '\section{Introduction} \begin{itemize} \end{itemize} \section{Related Work} \label{gen_inst} Self-supervised \section{Method} \label{method}In this section, \subsection{Framework} kkk \subsection{Cross Contrastive Loss} Since $\sZ^n$ are extracted \subsection{Implementation details} \textbf{Image augmentations} We use \textbf{Architecture} We use \textbf{Optimization} We adapt \section{Experiments} \label{experiments}In this section \subsection{Linear and Semi-Supervised Evaluations on ImageNet} \textbf{Linear evaluation on ImageNet} We firs \textbf{Semi-supervised learning on ImageNet} We simply \subsection{Transfer to other datasets and tasks} \textbf{Image classification with fixed features} We follow \section{Ablations} We present \subsection{Influence of hierarchical projection head and cross contrastive loss} get out \subsection{Levels and depth of projector network} \end{center} \caption{\label{figure3} \textbf{Different way of cross-correlation on 3 level hierarchical projection head.} ''='' denotes stop gradient.} \end{figure} \subsection{Analyze of} In this \textbf{Similarity between} Using SimSiam \textbf{Feature similarity} We extracted \section{Conclusion} We propose HCCL \clearpage \bibliographystyle{ACM-Reference-Format} \bibliography{sample-base} \end{document} \endinput %% %% End of file `sample-sigconf.tex''.

', 'api/v1/dataflow/real_static_files/operator/b9bcd635-7325-4534-b57f-c15c9d1dd264.png', '2025-07-28 22:35:47.937164', '2025-07-30 14:43:13.484934', 't');
INSERT INTO "public"."operator_info" VALUES (32, 'remove_long_words_mapper', 'Mapper', 0, 't', 'Mapper to remove long words within a specific range.', 'This paper a novel eqeqweqwewqeqwe121e1 method on LLM pretrain.', 'This paper novel method LLM pretrain.', 'api/v1/dataflow/real_static_files/operator/4137928e-256e-444a-942d-4f029ade11d5.png', '2025-07-29 09:23:12.613326', '2025-07-30 14:43:21.965993', 't');
INSERT INTO "public"."operator_info" VALUES (33, 'remove_non_chinese_character_mapper', 'Mapper', 0, 't', 'Mapper to remove non chinese Character in text samples.', '👊    所有的非汉字a44sh都12@46h会被*&……*qb^4525去掉', '所有的非汉字都会被去掉', 'api/v1/dataflow/real_static_files/operator/174b3132-9fe4-42a5-9191-b51b6ed92829.png', '2025-07-29 09:25:10.258087', '2025-07-30 14:43:29.975755', 't');
INSERT INTO "public"."operator_info" VALUES (34, 'remove_repeat_sentences_mapper', 'Mapper', 0, 't', 'Mapper to remove repeat sentences in text samples.', '今天天气真不错，阳光明媚，适合出去散步。小明说：“今天天气真不错，我们去海边吧。” 小红回答说：“好主意！” 但是，小李觉得：“今天天气真不错，我们去爬山吧。” 今天天气真不错，阳光明媚，适合出去散步。昨天下了一整天的雨，今天终于放晴了。昨天下了一整天的雨，今天终于放晴了。', '今天天气真不错，阳光明媚，适合出去散步。小明说：“今天天气真不错，我们去海边吧。” 小红回答说：“好主意！” 但是，小李觉得：“今天天气真不错，我们去爬山吧。”昨天下了一整天的雨，今天终于放晴了。', 'api/v1/dataflow/real_static_files/operator/1e86edad-423c-4334-ae62-ac2faea9d6cf.png', '2025-07-29 09:27:45.016877', '2025-07-30 14:43:36.759913', 't');
INSERT INTO "public"."operator_info" VALUES (37, 'remove_words_with_incorrect_substrings_mapper', 'Mapper', 0, 't', 'Mapper to remove words with incorrect substrings.', '请用百度www.baidu.com进行搜索', '请用百度www.baidu进行搜索', 'api/v1/dataflow/real_static_files/operator/0f31522d-d362-4e85-b02f-57182dc97f6f.png', '2025-07-29 16:43:33.213743', '2025-07-30 14:44:20.634694', 't');
INSERT INTO "public"."operator_info" VALUES (38, 'replace_content_mapper', 'Mapper', 0, 't', 'Mapper to replace all content in the text that matches
    a specific regular expression pattern with a designated
    replacement string.', '多个●■►▼这样的特殊字符可以►▼▲▴∆吗？', '多个<SPEC>►▼这样的特殊字符可以►▼▲▴∆吗？', 'api/v1/dataflow/real_static_files/operator/9b1aa7d6-2265-47bc-9a6a-f0c83d3aa538.png', '2025-07-29 16:43:42.176801', '2025-07-30 14:44:28.552504', 't');
INSERT INTO "public"."operator_info" VALUES (55, 'text_bloom_filter', 'Filter', 0, 't', 'Filter to deduplicate samples using Bloom Filter.', '包含重复文本的数据集，如多次出现的相同句子', '去重后的数据集，只保留每个唯一文本的一个实例', 'api/v1/dataflow/real_static_files/operator/e6aebe22-3205-4e43-b73f-d221a46b741b.png', '2025-08-13 15:34:00.008215', '2025-08-18 13:49:02.643745', 't');
INSERT INTO "public"."operator_info" VALUES (58, 'encode_and_get_nearest_mapper', 'Mapper', 0, 't', 'Encode texts and find nearest neighbours using Faiss.', '数据集包含first_prompt字段的文本数据，如[''What is artificial intelligence?'', ''How does machine learning work?'']', '数据集增加了embedding、nn_indices和nn_scores字段，包含文本的向量表示和最近邻信息', 'api/v1/dataflow/real_static_files/operator/00ec2df9-63ce-4167-9b0f-b50a910157fd.png', '2025-08-18 10:05:33.199011', '2025-08-18 13:48:17.300256', 't');
INSERT INTO "public"."operator_info" VALUES (3, 'clean_email_mapper', 'Mapper', 0, 't', 'Mapper to clean email in text samples.', 'happy day euqdh@cjqi.com', 'happy day', 'api/v1/dataflow/real_static_files/operator/eb0a7ba0-f54e-4328-bc6b-dafb0ac7e3e6.png', '2025-07-25 17:01:23.81786', '2025-07-30 14:36:05.326827', 't');
INSERT INTO "public"."operator_info" VALUES (4, 'clean_copyright_mapper', 'Mapper', 0, 't', 'Mapper to clean copyright comments at the beginning of the text
    samples.', '这是一段 /* 多行注释
注释内容copyright
*/ 的文本。另外还有一些 // 单行注释。', '这是一段  的文本。另外还有一些 // 单行注释。', 'api/v1/dataflow/real_static_files/operator/8430683a-eb75-4937-a20b-37ca5bce26b8.png', '2025-07-26 14:19:25.192786', '2025-07-30 14:36:31.80043', 't');
INSERT INTO "public"."operator_info" VALUES (6, 'expand_macro_mapper', 'Mapper', 0, 't', 'Mapper to expand macro definitions in the document body of Latex
    samples.', '\documentclass{article} % Recommended, but optional, packages for figures and better typesetting: \usepackage{microtype} \usepackage{graphicx} % Attempt to make hyperref and algorithmic work together better: \newcommand{\theHalgorithm}{\arabic{algorithm}} % For theorems and such \usepackage{amsmath} %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% % THEOREMS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% \theoremstyle{plain} \newtheorem{lemma}[theorem]{Lemma} \newtheorem{corollary}[theorem]{Corollary} \theoremstyle{definition} \usepackage[textsize=small]{todonotes} \setuptodonotes{inline} \usepackage{makecell} \newcommand{\cmark}{\ding{51}\xspace}% \newcommand{\xmark}{\ding{55}\xspace}% \def \alambic {\includegraphics[height=1.52ex]{img/alembic-crop.pdf}\xspace} \newcommand\binke[1]{{\color{blue} \footnote{\color{blue}binke: #1}} } \newcommand\Zerocost{Zero-cost} \newcommand\imagenet{ImageNet} \begin{document} \begin{abstract} The wide \end{abstract} \section{Introduction} \label{introduction} The main contributions are summarized as follows: \section{Background and Related Work}\label{background} \subsection{One-Shot NAS} In one-shot NAS \section{PreNAS}\label{method}In this \subsection{One-Shot NAS with Preferred Learning} In the specialization stage, the optimal architectures under given resource constraints can be directly obtained: \begin{equation} \widetilde{\mathcal{A}}^* = \widetilde{\mathcal{A}} . \end{equation} \subsection{Zero-Cost Transformer Selector}\label{sub:layerNorm} \subsection{Performance Balancing} We discuss \section{Experiments}\label{experiments} \subsection{Setup} \subsection{Main Results}\label{sec:sota} \subsection{Analysis and Ablation study}\label{ablation} \begin{figure}[t] \vskip 0.1in \centering \subfigure[Search spaces]{\includegraphics[width=0.36\linewidth]{img/search_space.pdf}\label{fg:search_space:a}}% \hfil% \subfigure[Error distributions]{\includegraphics[width=0.58\linewidth]{img/cumulation.pdf}\label{fg:search_space:b}} \caption{Model quality} \vskip -0.1in \end{figure} \paragraph{Effect of Performance Balancing} During \subsection{Transfer Learning Results} \subsection{CNN Results} in terms of similar FLOPs. \FloatBarrier \section{Conclusion}\label{conclusion} In this % Acknowledgements should only appear in the accepted version. \bibliography{ref} \bibliographystyle{icml2023} \clearpage \appendix \onecolumn \section{Statistical} \label{appendix:snipAnalysis} We analyze \section{The Greedy Algorithm} \label{appendix:greedy} \section{Regularization \& Data Augmentation}\label{appendix:aug} \renewcommand{\arraystretch}{1.2} \end{document}

', '\documentclass{article} % Recommended, but optional, packages for figures and better typesetting: \usepackage{microtype} \usepackage{graphicx} % Attempt to make hyperref and algorithmic work together better: \newcommand{\arabic{algorithm}}{\arabic{algorithm}} % For theorems and such \usepackage{amsmath} %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% % THEOREMS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% \theoremstyle{plain} \newtheorem{lemma}[theorem]{Lemma} \newtheorem{corollary}[theorem]{Corollary} \theoremstyle{definition} \usepackage[textsize=small]{todonotes} \setuptodonotes{inline} \usepackage{makecell} \newcommand{\cmark}{\ding{51}\xspace}% \newcommand{\xmark}{\ding{55}\xspace}% \def \includegraphics[height=1.52ex]{img/alembic-crop.pdf}\xspace {\includegraphics[height=1.52ex]{img/alembic-crop.pdf}\xspace} \newcommand\binke[1]{{\color{blue} \footnote{\color{blue}binke: #1}} } \newcommand\Zerocost{Zero-cost} \newcommand\imagenet{ImageNet} \begin{document} \begin{abstract} The wide \end{abstract} \section{Introduction} \label{introduction} The main contributions are summarized as follows: \section{Background and Related Work}\label{background} \subsection{One-Shot NAS} In one-shot NAS \section{PreNAS}\label{method}In this \subsection{One-Shot NAS with Preferred Learning} In the specialization stage, the optimal architectures under given resource constraints can be directly obtained: \begin{equation} \widetilde{\mathcal{A}}^* = \widetilde{\mathcal{A}} . \end{equation} \subsection{Zero-Cost Transformer Selector}\label{sub:layerNorm} \subsection{Performance Balancing} We discuss \section{Experiments}\label{experiments} \subsection{Setup} \subsection{Main Results}\label{sec:sota} \subsection{Analysis and Ablation study}\label{ablation} \begin{figure}[t] \vskip 0.1in \centering \subfigure[Search spaces]{\includegraphics[width=0.36\linewidth]{img/search_space.pdf}\label{fg:search_space:a}}% \hfil% \subfigure[Error distributions]{\includegraphics[width=0.58\linewidth]{img/cumulation.pdf}\label{fg:search_space:b}} \caption{Model quality} \vskip -0.1in \end{figure} \paragraph{Effect of Performance Balancing} During \subsection{Transfer Learning Results} \subsection{CNN Results} in terms of similar FLOPs. \FloatBarrier \section{Conclusion}\label{conclusion} In this % Acknowledgements should only appear in the accepted version. \bibliography{ref} \bibliographystyle{icml2023} \clearpage \appendix \onecolumn \section{Statistical} \label{appendix:snipAnalysis} We analyze \section{The Greedy Algorithm} \label{appendix:greedy} \section{Regularization \& Data Augmentation}\label{appendix:aug} \renewcommand{\arraystretch}{1.2} \end{document}

', 'api/v1/dataflow/real_static_files/operator/b439841c-cbc8-4e71-9ee6-96325875f6e9.png', '2025-07-28 18:00:40.431969', '2025-07-30 14:37:54.224796', 't');
INSERT INTO "public"."operator_info" VALUES (21, 'optimize_instruction_mapper', 'Mapper', 0, 't', 'Mapper to optimize instruction.', '鱼香肉丝怎么做？', '请提供一份完整的“鱼香肉丝”食谱，包括以下详细信息：所需材料清单：请列出所有必要的主料和辅料，包括肉的种类和处理方式，以及所有蔬菜和调味料的具体量。准备工作指南：描述准备工作的具体步骤，如肉丝的腌制过程、蔬菜的切割技巧等。详细烹饪步骤：请按照烹饪的逻辑顺序，逐步解释如何将材料炒制成鱼香肉丝，包括火候控制、调味料添加的时机等详细操作。盛盘和陈设建议：给出如何将完成的鱼香肉丝装盘摆放，以及可以搭配的其他菜品或饭类推荐，以便提升整体用餐体验。附加小贴士：如有任何专业小窍门或注意事项，例如如何切肉更易入味，或特定调味料的选择建议等，也请一并提供。', 'api/v1/dataflow/real_static_files/operator/fd013e56-4b3d-4bed-9005-b9b28d6548cc.png', '2025-07-28 22:26:54.685618', '2025-07-30 14:41:46.776216', 't');
INSERT INTO "public"."operator_info" VALUES (25, 'remove_comments_mapper', 'Mapper', 0, 't', 'Mapper to remove comments in different kinds of documents.

    Only support ''tex'' for now.
    ', '%% %% This is file `sample-sigconf.tex'', %% The first command in your LaTeX source must be the \documentclass command. \documentclass[sigconf,review,anonymous]{acmart} %% NOTE that a single column version is required for %% submission and peer review. This can be done by changing \input{math_commands.tex} %% end of the preamble, start of the body of the document source. \begin{document} %% The "title" command has an optional parameter, \title{Hierarchical Cross Contrastive Learning of Visual Representations} %% %% The "author" command and its associated commands are used to define %% the authors and their affiliations. \author{Hesen Chen} \affiliation{% \institution{Alibaba Group} \city{Beijing} \country{China}} \email{hesen.chs@alibaba-inc.com} %% By default, the full list of authors will be used in the page \begin{abstract}The rapid \end{abstract} \begin{CCSXML} \ccsdesc[500]{Computing methodologies~Image representations} %% Keywords. The author(s) should pick words that accurately describe \keywords{self-supervised, ontrastive Learning, hierarchical projection, cross-level} %% page. \begin{teaserfigure} \end{teaserfigure} %% This command processes the author and affiliation and title \maketitle \section{Introduction} \begin{itemize} \end{itemize} \section{Related Work} \label{gen_inst} Self-supervised \section{Method} \label{method}In this section, \subsection{Framework} kkk \subsection{Cross Contrastive Loss} Since $\sZ^n$ are extracted \subsection{Implementation details} \textbf{Image augmentations} We use \textbf{Architecture} We use \textbf{Optimization} We adapt \section{Experiments} \label{experiments}In this section \subsection{Linear and Semi-Supervised Evaluations on ImageNet} \textbf{Linear evaluation on ImageNet} We firs \textbf{Semi-supervised learning on ImageNet} We simply \subsection{Transfer to other datasets and tasks} \textbf{Image classification with fixed features} We follow \section{Ablations} We present \subsection{Influence of hierarchical projection head and cross contrastive loss} get out \subsection{Levels and depth of projector network} \end{center} \caption{\label{figure3} \textbf{Different way of cross-correlation on 3 level hierarchical projection head.} ''='' denotes stop gradient.} \end{figure} \subsection{Analyze of} In this \textbf{Similarity between} Using SimSiam \textbf{Feature similarity} We extracted \section{Conclusion} We propose HCCL \clearpage \bibliographystyle{ACM-Reference-Format} \bibliography{sample-base} \end{document} \endinput %% %% End of file `sample-sigconf.tex''.

', '\documentclass[sigconf,review,anonymous]{acmart} \input{math_commands.tex} \begin{document} \title{Hierarchical Cross Contrastive Learning of Visual Representations} \author{Hesen Chen} \affiliation{% \institution{Alibaba Group} \city{Beijing} \country{China}} \email{hesen.chs@alibaba-inc.com} \begin{abstract}The rapid \end{abstract} \begin{CCSXML} \ccsdesc[500]{Computing methodologies~Image representations} \keywords{self-supervised, ontrastive Learning, hierarchical projection, cross-level} \begin{teaserfigure} \end{teaserfigure} \maketitle \section{Introduction} \begin{itemize} \end{itemize} \section{Related Work} \label{gen_inst} Self-supervised \section{Method} \label{method}In this section, \subsection{Framework} kkk \subsection{Cross Contrastive Loss} Since $\sZ^n$ are extracted \subsection{Implementation details} \textbf{Image augmentations} We use \textbf{Architecture} We use \textbf{Optimization} We adapt \section{Experiments} \label{experiments}In this section \subsection{Linear and Semi-Supervised Evaluations on ImageNet} \textbf{Linear evaluation on ImageNet} We firs \textbf{Semi-supervised learning on ImageNet} We simply \subsection{Transfer to other datasets and tasks} \textbf{Image classification with fixed features} We follow \section{Ablations} We present \subsection{Influence of hierarchical projection head and cross contrastive loss} get out \subsection{Levels and depth of projector network} \end{center} \caption{\label{figure3} \textbf{Different way of cross-correlation on 3 level hierarchical projection head.} ''='' denotes stop gradient.} \end{figure} \subsection{Analyze of} In this \textbf{Similarity between} Using SimSiam \textbf{Feature similarity} We extracted \section{Conclusion} We propose HCCL \clearpage \bibliographystyle{ACM-Reference-Format} \bibliography{sample-base} \end{document} \endinput

', 'api/v1/dataflow/real_static_files/operator/d7d1a896-6a66-404c-9230-1d589dce80cb.png', '2025-07-28 22:33:35.42515', '2025-07-30 14:42:27.543635', 't');
INSERT INTO "public"."operator_info" VALUES (36, 'remove_table_text_mapper', 'Mapper', 0, 't', '
    Mapper to remove table texts from text samples.

    Regular expression is used to remove tables in the range of column
    number of tables.
    ', 'This is a table:
编号 分行 营运资金1 营运资金2 营运资金3 营运资金4 营运资金5
① 北京分行 495,000,000.00 200,000,000.00 295,000,000.00 - 495,000,000.00
② 大连分行 440,000,000.00 100,000,000.00 340,000,000.00 - 440,000,000.00
③ 重庆分行 500,000,000.00 100,000,000.00 400,000,000.00 - 500,000,000.00
④ 南京分行 430,000,000.00 100,000,000.00 330,000,000.00 - 430,000,000.00
⑤ 青岛分行 500,000,000.00 - 100,159,277.60 399,840,722.40 500,000,000.00
The end of the table.', 'This is a table:
The end of the table.', 'api/v1/dataflow/real_static_files/operator/52fcc0d8-9265-49e9-8d0f-5c488463e4f3.png', '2025-07-29 16:43:07.170951', '2025-07-30 14:44:11.203543', 't');

-- ----------------------------
-- Indexes structure for table operator_info
-- ----------------------------
CREATE INDEX "ix_operator_info_id" ON "public"."operator_info" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table operator_info
-- ----------------------------
ALTER TABLE "public"."operator_info" ADD CONSTRAINT "operator_info_pkey" PRIMARY KEY ("id");

-- Set sequence owner and starting value
ALTER SEQUENCE operator_info_id_seq OWNED BY operator_info.id;
-- Set sequence to current max ID, with is_called=true so next value will be max+1
ALTER SEQUENCE operator_info_id_seq RESTART WITH 1000;
