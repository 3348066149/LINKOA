-- =============================================================
-- 青岛领客文创OA V1.2 数据库初始化脚本
-- 配套文档：
--   - 领客文创OA_V1_PRD.md
--   - 领客文创OA_V1_Database.md
--   - 青岛领客文创OA_V1_后端接口清单.md
-- 说明：
--   1. 共 16 张表（含 2 张连线表），字符集 utf8mb4，引擎 InnoDB
--   2. 不建物理外键，纯逻辑关联，级联删除/约束由后端代码事务控制
--   3. 主键全部 bigint 自增，起始值 1
--   4. 业务表均物理删除，不设软删除字段；操作审计日志永久留存
--   5. 初始数据：管理员账号 admin / admin123（明文密码，内网使用）
-- 使用方式：
--   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS linkoa DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;"
--   mysql -u root -p linkoa < init.sql
-- =============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- -------------------------------------------------------------
-- 1. 用户表 sys_user
-- 角色枚举：管理员 / 行政 / 设计总监 / 设计师
-- 用户不做物理删除，仅启用/停用；停用后禁止登录，保留历史关联
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `id`          bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `username`    varchar(64)  NOT NULL COMMENT '登录账号，唯一',
  `password`    varchar(128) NOT NULL COMMENT '明文密码，内网使用',
  `real_name`   varchar(64)  NOT NULL COMMENT '真实姓名',
  `role`        varchar(32)  NOT NULL COMMENT '角色：管理员 / 行政 / 设计总监 / 设计师 / 客户',
  `dept_id`     bigint       DEFAULT NULL COMMENT '所属部门ID（sys_dept.id，客户账号为空）',
  `customer_id` bigint       DEFAULT NULL COMMENT '客户账号绑定的客户ID（customer.id，仅 role=客户）',
  `is_enable`   tinyint      NOT NULL DEFAULT 1 COMMENT '0停用，1启用',
  `create_time` datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 部门表：仅做人员组织分组，不携带权限（V1.4 起 role 字段保留兼容，恒为 NULL）
CREATE TABLE `sys_dept` (
  `id`          bigint      NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `dept_name`   varchar(64) NOT NULL COMMENT '部门名称，唯一',
  `dept_type`   varchar(16) NOT NULL DEFAULT 'internal' COMMENT 'internal 内置员工部门 / customer 客户部门',
  `role`        varchar(32) DEFAULT NULL COMMENT '兼容字段（V1.4 起不使用，恒为 NULL）',
  `customer_id` bigint      DEFAULT NULL COMMENT '客户部门关联的客户ID（customer.id）',
  `create_time` datetime    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dept_name` (`dept_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='部门表';

-- 预置内置部门（不绑定权限模板）
INSERT INTO `sys_dept` (`dept_name`, `dept_type`) VALUES
('研发部', 'internal'),
('设计部', 'internal'),
('市场部', 'internal');

-- 自定义角色表：管理员自定义业务角色（如研发人员），建用户时可选（V1.3.1 起由部门体系替代，保留兼容）
CREATE TABLE `sys_role` (
  `id`          bigint      NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `role_name`   varchar(32) NOT NULL COMMENT '角色名称，唯一',
  `create_time` datetime    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_name` (`role_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='自定义角色表';

-- -------------------------------------------------------------
-- 2. 客户分类表 customer_category
-- 删除约束：分类下存在客户时禁止删除，后端返回 400
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `customer_category`;
CREATE TABLE `customer_category` (
  `id`            bigint      NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `category_name` varchar(128) NOT NULL COMMENT '分类名称',
  `create_time`   datetime    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`   datetime    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户分类表';

-- -------------------------------------------------------------
-- 3. 客户表 customer
-- 删除约束：客户存在关联项目时禁止删除，后端返回 400
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `customer`;
CREATE TABLE `customer` (
  `id`            bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `category_id`   bigint       NOT NULL COMMENT '关联客户分类ID（逻辑关联，无物理外键）',
  `customer_name` varchar(128) NOT NULL COMMENT '客户名称',
  `contact`       varchar(128) DEFAULT NULL COMMENT '联系方式（电话/微信/邮箱）',
  `cover_image`   varchar(512) DEFAULT NULL COMMENT '卡片封面图相对路径（uploads/cover 下）',
  `remark`        text         DEFAULT NULL COMMENT '客户备注（对接人、合作信息）',
  `create_time`   datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`   datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_category_id` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户表';

-- -------------------------------------------------------------
-- 4. 流程模板表 flow_template
-- 模板与项目为全量值拷贝、深度解绑；删除模板不影响历史项目
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `flow_template`;
CREATE TABLE `flow_template` (
  `id`            bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `template_name` varchar(128) NOT NULL COMMENT '模板名称',
  `create_user_id` bigint      NOT NULL COMMENT '创建人用户ID',
  `create_time`   datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`   datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='流程模板表';

-- -------------------------------------------------------------
-- 5. 模板节点表 flow_template_node
-- 模板编辑采用自由拓扑画布，节点带画布坐标
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `flow_template_node`;
CREATE TABLE `flow_template_node` (
  `id`          bigint        NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `template_id` bigint        NOT NULL COMMENT '所属模板ID',
  `node_template_id` bigint   DEFAULT NULL COMMENT '关联节点模板ID（表单定义来源，V1.3）',
  `node_title`  varchar(128)  NOT NULL COMMENT '节点标题',
  `node_remark` text          DEFAULT NULL COMMENT '模板节点备注',
  `sort`        int           NOT NULL DEFAULT 0 COMMENT '节点排序序号（用于列表展示顺序）',
  `pos_x`       decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT '节点画布X坐标',
  `pos_y`       decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT '节点画布Y坐标',
  `create_time` datetime      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_template_id` (`template_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模板节点表';

-- -------------------------------------------------------------
-- 6. 模板节点连线表 flow_template_node_edge
-- 复制模板时值拷贝到 project_node_edge；模板保存为整图提交
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `flow_template_node_edge`;
CREATE TABLE `flow_template_node_edge` (
  `id`             bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `template_id`    bigint       NOT NULL COMMENT '所属模板ID',
  `source_node_id` bigint       NOT NULL COMMENT '连线起始节点ID（关联 flow_template_node.id）',
  `target_node_id` bigint       NOT NULL COMMENT '连线目标节点ID（关联 flow_template_node.id）',
  `label`          varchar(128) DEFAULT NULL COMMENT '连线文字标签，可空',
  `create_time`    datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_template_id` (`template_id`),
  KEY `idx_source_target` (`source_node_id`, `target_node_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模板节点连线表';

-- -------------------------------------------------------------
-- 7. 模板节点表单定义表 flow_template_node_form
-- V1 字段类型：text_single 单行文本 / text_multi 多行文本 / select 下拉单选
-- 项目实例中不可修改表单结构，仅可填写值
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `flow_template_node_form`;
CREATE TABLE `flow_template_node_form` (
  `id`               bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `template_node_id` bigint       NOT NULL COMMENT '关联 flow_template_node.id',
  `field_label`      varchar(128) NOT NULL COMMENT '表单显示名称',
  `field_type`       varchar(32)  NOT NULL COMMENT 'text_single单行 / text_multi多行 / select下拉单选',
  `select_options`   text         DEFAULT NULL COMMENT '下拉选项JSON数组；非下拉存null',
  `sort`             int          NOT NULL DEFAULT 0 COMMENT '表单字段排序',
  `create_time`      datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`      datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_template_node_id` (`template_node_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模板节点表单定义表';

-- -------------------------------------------------------------
-- 8. 项目表 project
-- 项目状态枚举：进行中 / 已归档；已归档项目全部内容只读
-- 删除约束：已归档项目必须先取消归档才能删除，后端返回 400
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `project`;
CREATE TABLE `project` (
  `id`             bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `project_name`   varchar(256) NOT NULL COMMENT '项目名称',
  `customer_id`    bigint       NOT NULL COMMENT '关联客户ID',
  `project_desc`   text         DEFAULT NULL COMMENT '项目描述',
  `expect_time`    datetime     DEFAULT NULL COMMENT '预计时间',
  `project_status` varchar(32)  NOT NULL DEFAULT '进行中' COMMENT '进行中 / 已归档',
  `cover_image`    varchar(512) DEFAULT NULL COMMENT '卡片封面图相对路径（uploads/ 下）',
  `create_user_id` bigint       NOT NULL COMMENT '创建人ID',
  `create_time`    datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`    datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_customer_id` (`customer_id`),
  KEY `idx_project_status` (`project_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目表';

-- -------------------------------------------------------------
-- 9. 项目-设计师关联表 project_designer_rel
-- 仅用于溯源展示，不做权限控制；一个项目可关联多个设计师
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `project_designer_rel`;
CREATE TABLE `project_designer_rel` (
  `id`          bigint   NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `project_id`  bigint   NOT NULL COMMENT '项目ID',
  `user_id`     bigint   NOT NULL COMMENT '设计师用户ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目-设计师关联表';

-- -------------------------------------------------------------
-- 10. 项目画布节点表 project_node
-- 从模板节点值拷贝生成（含坐标、备注）
-- 删除节点时，事务级联删除该节点的全部出入连线（project_node_edge）
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `project_node`;
CREATE TABLE `project_node` (
  `id`            bigint        NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `project_id`    bigint        NOT NULL COMMENT '所属项目ID',
  `node_title`    varchar(128)  NOT NULL COMMENT '节点标题',
  `node_remark`   text          DEFAULT NULL COMMENT '节点备注',
  `icon`          varchar(512)  DEFAULT NULL COMMENT '节点图标（从模板冗余拷贝，V1.4.3）',
  `sort`          int           NOT NULL DEFAULT 0 COMMENT '节点排序序号',
  `pos_x`         decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT '节点画布X坐标',
  `pos_y`         decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT '节点画布Y坐标',
  `create_user_id` bigint       NOT NULL COMMENT '创建人ID',
  `create_time`   datetime      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`   datetime      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目画布节点表';

-- -------------------------------------------------------------
-- 11. 项目节点连线表 project_node_edge
-- 从模板连线表值拷贝生成，拷贝时需完成节点ID重映射
-- 删除节点时级联删除以该节点为 source 或 target 的全部连线
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `project_node_edge`;
CREATE TABLE `project_node_edge` (
  `id`             bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `project_id`     bigint       NOT NULL COMMENT '所属项目ID',
  `source_node_id` bigint       NOT NULL COMMENT '连线起始节点ID（关联 project_node.id）',
  `target_node_id` bigint       NOT NULL COMMENT '连线目标节点ID（关联 project_node.id）',
  `label`          varchar(128) DEFAULT NULL COMMENT '连线文字标签，可空',
  `create_time`    datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_source_target` (`source_node_id`, `target_node_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目节点连线表';

-- -------------------------------------------------------------
-- 12. 项目节点表单填写值表 project_node_form_value
-- 冗余字段保证模板修改不破坏历史数据；全量覆盖保存
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `project_node_form_value`;
CREATE TABLE `project_node_form_value` (
  `id`                   bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `project_node_id`      bigint       NOT NULL COMMENT '关联 project_node.id',
  `template_node_form_id` bigint      DEFAULT NULL COMMENT '来源模板表单ID，仅溯源用',
  `field_label`          varchar(128) NOT NULL COMMENT '冗余：表单显示名称',
  `field_type`           varchar(32)  NOT NULL COMMENT '冗余：字段类型',
  `select_options`       text         DEFAULT NULL COMMENT '冗余：下拉选项JSON数组（V1.3）',
  `field_value`          text         DEFAULT NULL COMMENT '用户填写内容',
  `create_user_id`       bigint       DEFAULT NULL COMMENT '填写人ID',
  `create_time`          datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`          datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_project_node_id` (`project_node_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目节点表单填写值表';

-- -------------------------------------------------------------
-- 13. 附件表 attachment
-- 存储路径：uploads/YYYYMMDD/UUID_原始文件名（日期隔离 + UUID 防重名）
-- 仅附件上传本人可删除；归档项目禁止上传和删除附件
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `attachment`;
CREATE TABLE `attachment` (
  `id`              bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `project_id`      bigint       NOT NULL COMMENT '所属项目ID',
  `project_node_id` bigint       NOT NULL COMMENT '所属节点ID',
  `file_name`       varchar(256) NOT NULL COMMENT '原始文件名',
  `file_path`       varchar(512) NOT NULL COMMENT '服务器本地磁盘完整路径',
  `file_size`       bigint       NOT NULL DEFAULT 0 COMMENT '文件大小（byte）',
  `upload_user_id`  bigint       NOT NULL COMMENT '上传人ID',
  `create_time`     datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_project_node_id` (`project_node_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='附件表';

-- -------------------------------------------------------------
-- 14. 评论表 comment
-- 项目级评论，全部角色可发表；仅评论发布本人可删除
-- 归档项目禁止新增和删除评论
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `comment`;
CREATE TABLE `comment` (
  `id`             bigint   NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `project_id`     bigint   NOT NULL COMMENT '项目ID',
  `content`        text     NOT NULL COMMENT '评论内容',
  `create_user_id` bigint   NOT NULL COMMENT '评论人ID',
  `create_time`    datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评论时间',
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评论表';

-- -------------------------------------------------------------
-- 15. 消息表 message
-- 推送范围：项目创建人 + 项目所有关联设计师（自动排除操作人自己）
-- msg_type：node_create / node_update / node_delete / form_update / comment_create
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `message`;
CREATE TABLE `message` (
  `id`              bigint      NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `receive_user_id` bigint      NOT NULL COMMENT '接收消息用户ID',
  `project_id`      bigint      DEFAULT NULL COMMENT '关联项目ID（用于前端点击跳转，可空）',
  `msg_type`        varchar(64) NOT NULL COMMENT '消息类型：node_create / node_update / node_delete / form_update / comment_create',
  `msg_content`     text        NOT NULL COMMENT '消息简要内容（人类可读文案）',
  `is_read`         tinyint     NOT NULL DEFAULT 0 COMMENT '0未读，1已读',
  `create_time`     datetime    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '消息生成时间',
  PRIMARY KEY (`id`),
  KEY `idx_receive_user_id` (`receive_user_id`),
  KEY `idx_project_id` (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息表';

-- -------------------------------------------------------------
-- 16. 节点模板表 node_template（V1.3 新增）
-- 管理员预设的可复用节点类型；画布只能通过节点模板库添加节点
-- form_fields 为 JSON 数组：[{fieldLabel, fieldType, selectOptions, sort}]
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `node_template`;
CREATE TABLE `node_template` (
  `id`          bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `node_title`  varchar(128) NOT NULL COMMENT '节点类型名称',
  `node_remark` text         DEFAULT NULL COMMENT '节点类型说明',
  `icon`        varchar(512) DEFAULT NULL COMMENT '节点图标：预设图标组件名或 uploads/ 自定义图标路径（V1.4.3）',
  `sort`        int          NOT NULL DEFAULT 0 COMMENT '面板展示排序',
  `form_fields` text         DEFAULT NULL COMMENT '建议表单字段JSON数组，可空',
  `create_time` datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='节点模板表';

-- -------------------------------------------------------------
-- 17. 系统操作日志表 sys_operation_log
-- 日志不可修改，不可删除；审计溯源；物理删除业务数据时日志永久留存
-- oper_type 枚举值清单见 Database.md 附录（user_login / project_create / node_template_create 等）
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `sys_operation_log`;
CREATE TABLE `sys_operation_log` (
  `id`                 bigint       NOT NULL AUTO_INCREMENT COMMENT '主键自增',
  `oper_user_id`       bigint       NOT NULL COMMENT '操作人ID',
  `oper_time`          datetime     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  `oper_type`          varchar(128) NOT NULL COMMENT '操作类型枚举（见 Database.md 清单）',
  `oper_desc`          text         DEFAULT NULL COMMENT '变更简要描述（人类可读）',
  `related_project_id` bigint       DEFAULT NULL COMMENT 'null=全局操作；不为空代表归属某个项目',
  PRIMARY KEY (`id`),
  KEY `idx_oper_user_id` (`oper_user_id`),
  KEY `idx_related_project_id` (`related_project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统操作日志表';

-- -------------------------------------------------------------
-- 初始数据：默认管理员账号 admin / admin123（明文密码，内网使用）
-- -------------------------------------------------------------
INSERT INTO `sys_user` (`username`, `password`, `real_name`, `role`, `is_enable`)
VALUES ('admin', 'admin123', '管理员', '管理员', 1);

SET FOREIGN_KEY_CHECKS = 1;
