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

 Date: 13/08/2025 17:11:07
*/


-- ----------------------------
-- Table structure for operator_config_select_options
-- ----------------------------
DROP TABLE IF EXISTS "public"."operator_config_select_options";
CREATE TABLE "public"."operator_config_select_options" (
  "id" int8 NOT NULL DEFAULT nextval('operator_config_select_options_copy_id_seq'::regclass),
  "name" varchar(255) COLLATE "pg_catalog"."default",
  "is_enable" bool,
  "sort" int4,
  "created_at" timestamp(6),
  "updated_at" timestamp(6)
)
;

-- ----------------------------
-- Records of operator_config_select_options
-- ----------------------------
INSERT INTO "public"."operator_config_select_options" VALUES (1, 's2t', 'f', 0, '2025-07-25 16:24:58.545561', '2025-07-25 16:24:58.545561');
INSERT INTO "public"."operator_config_select_options" VALUES (2, 't2s', 'f', 0, '2025-07-25 16:25:11.324732', '2025-07-25 16:25:11.324732');
INSERT INTO "public"."operator_config_select_options" VALUES (3, 's2tw', 'f', 0, '2025-07-25 16:25:20.228439', '2025-07-25 16:25:20.228439');
INSERT INTO "public"."operator_config_select_options" VALUES (4, 'tw2s', 'f', 0, '2025-07-25 16:25:27.180679', '2025-07-25 16:25:27.180679');
INSERT INTO "public"."operator_config_select_options" VALUES (5, 's2hk', 'f', 0, '2025-07-25 16:25:32.92963', '2025-07-25 16:25:32.92963');
INSERT INTO "public"."operator_config_select_options" VALUES (6, 'hk2s', 'f', 0, '2025-07-25 16:25:37.442863', '2025-07-25 16:25:37.442863');
INSERT INTO "public"."operator_config_select_options" VALUES (7, 's2twp', 'f', 0, '2025-07-25 16:25:42.535801', '2025-07-25 16:25:42.535801');
INSERT INTO "public"."operator_config_select_options" VALUES (8, 'tw2sp', 'f', 0, '2025-07-25 16:25:48.229256', '2025-07-25 16:25:48.229256');
INSERT INTO "public"."operator_config_select_options" VALUES (9, 't2tw', 'f', 0, '2025-07-25 16:25:53.326925', '2025-07-25 16:25:53.326925');
INSERT INTO "public"."operator_config_select_options" VALUES (10, 'tw2t', 'f', 0, '2025-07-25 16:25:58.101863', '2025-07-25 16:25:58.101863');
INSERT INTO "public"."operator_config_select_options" VALUES (11, 'hk2t', 'f', 0, '2025-07-25 16:26:02.434436', '2025-07-25 16:26:02.434436');
INSERT INTO "public"."operator_config_select_options" VALUES (12, 't2hk', 'f', 0, '2025-07-25 16:26:07.400241', '2025-07-25 16:26:07.400241');
INSERT INTO "public"."operator_config_select_options" VALUES (13, 't2jp', 'f', 0, '2025-07-25 16:26:11.456982', '2025-07-25 16:26:11.456982');
INSERT INTO "public"."operator_config_select_options" VALUES (14, 'jp2t', 'f', 0, '2025-07-25 16:26:15.851434', '2025-07-25 16:26:15.851434');
INSERT INTO "public"."operator_config_select_options" VALUES (15, 'en', 'f', 0, '2025-07-25 16:26:46.455569', '2025-07-25 16:26:46.455569');
INSERT INTO "public"."operator_config_select_options" VALUES (16, 'zh', 'f', 0, '2025-07-25 16:26:52.044461', '2025-07-25 16:26:52.044461');
INSERT INTO "public"."operator_config_select_options" VALUES (18, 'alibaba-pai/pai-qwen1_5-7b-doc2qa', 'f', 0, '2025-07-28 18:05:10.083942', '2025-07-28 18:05:10.083942');
INSERT INTO "public"."operator_config_select_options" VALUES (19, 'NFC', 'f', 0, '2025-07-28 21:16:14.158499', '2025-07-28 21:16:14.158499');
INSERT INTO "public"."operator_config_select_options" VALUES (20, 'NFKC', 'f', 0, '2025-07-28 21:16:22.57648', '2025-07-28 21:16:22.57648');
INSERT INTO "public"."operator_config_select_options" VALUES (21, 'NFD', 'f', 0, '2025-07-28 21:16:33.58735', '2025-07-28 21:16:33.58735');
INSERT INTO "public"."operator_config_select_options" VALUES (22, 'NFKD', 'f', 0, '2025-07-28 21:16:51.369182', '2025-07-28 21:16:51.369182');
INSERT INTO "public"."operator_config_select_options" VALUES (23, 'AIWizards/Llama2-Chinese-7b-Chat', 'f', 0, '2025-07-28 21:54:45.693336', '2025-07-28 21:54:45.693336');
INSERT INTO "public"."operator_config_select_options" VALUES (24, 'alibaba-pai/Qwen2-7B-Instruct-Refine', 'f', 0, '2025-07-28 22:25:04.830535', '2025-07-28 22:25:04.830535');
INSERT INTO "public"."operator_config_select_options" VALUES (25, 'fr', 'f', 0, '2025-07-29 16:44:33.793899', '2025-07-29 16:44:33.793899');
INSERT INTO "public"."operator_config_select_options" VALUES (26, 'de', 'f', 0, '2025-07-29 16:44:39.125055', '2025-07-29 16:44:39.125055');
INSERT INTO "public"."operator_config_select_options" VALUES (27, 'any', 'f', 0, '2025-07-29 16:49:21.743399', '2025-07-29 16:49:21.743399');
INSERT INTO "public"."operator_config_select_options" VALUES (29, 'EleutherAI/pythia-6.9b-deduped', 'f', 0, '2025-07-29 16:51:55.635655', '2025-07-29 16:51:55.635655');
INSERT INTO "public"."operator_config_select_options" VALUES (30, 'space', 'f', 0, '2025-07-29 17:04:01.515447', '2025-07-29 17:04:01.515447');
INSERT INTO "public"."operator_config_select_options" VALUES (31, 'punctuation', 'f', 0, '2025-07-29 17:04:05.956335', '2025-07-29 17:04:05.956335');
INSERT INTO "public"."operator_config_select_options" VALUES (32, 'character', 'f', 0, '2025-07-29 17:04:09.76577', '2025-07-29 17:04:09.76577');
INSERT INTO "public"."operator_config_select_options" VALUES (33, 'sentencepiece', 'f', 0, '2025-07-29 17:04:14.044334', '2025-07-29 17:04:14.044334');
INSERT INTO "public"."operator_config_select_options" VALUES (34, 'shunk031/aesthetics-predictor-v2-sac-logos-ava1-l14-linearMSE', 'f', 0, '2025-08-02 14:26:51.922223', '2025-08-02 14:26:51.922223');
INSERT INTO "public"."operator_config_select_options" VALUES (35, 'haarcascade_frontalface_alt.xml', 'f', 0, '2025-08-02 14:48:54.199066', '2025-08-02 14:48:54.199066');
INSERT INTO "public"."operator_config_select_options" VALUES (36, 'Falconsai/nsfw_image_detection', 'f', 0, '2025-08-04 09:11:56.095296', '2025-08-04 09:11:56.095296');
INSERT INTO "public"."operator_config_select_options" VALUES (37, 'Salesforce/blip-itm-base-coco', 'f', 0, '2025-08-04 09:33:47.77734', '2025-08-04 09:33:47.77734');
INSERT INTO "public"."operator_config_select_options" VALUES (38, 'openai/clip-vit-base-patch32', 'f', 0, '2025-08-04 09:40:17.661715', '2025-08-04 09:40:17.661715');
INSERT INTO "public"."operator_config_select_options" VALUES (39, 'amrul-hzz/watermark_detector', 'f', 0, '2025-08-04 09:47:52.553982', '2025-08-04 09:47:52.553982');
INSERT INTO "public"."operator_config_select_options" VALUES (40, 'google/owlvit-base-patch32', 'f', 0, '2025-08-04 09:53:12.245911', '2025-08-04 09:53:12.245911');
INSERT INTO "public"."operator_config_select_options" VALUES (28, 'all', 'f', 0, '2025-07-29 16:49:26.670396', '2025-07-29 16:49:26.670396');

-- ----------------------------
-- Indexes structure for table operator_config_select_options
-- ----------------------------
CREATE INDEX "ix_operator_config_select_options_copy_id" ON "public"."operator_config_select_options" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table operator_config_select_options
-- ----------------------------
ALTER TABLE "public"."operator_config_select_options" ADD CONSTRAINT "operator_config_select_options_copy_pkey" PRIMARY KEY ("id");
