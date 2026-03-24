-- ================================================
-- 数据库初始化脚本
-- ================================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS nlqdb DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE nlqdb;

-- 注意：表结构由 Alembic 迁移自动创建
-- 这里只创建数据库，具体表结构通过后端迁移自动生成

SET FOREIGN_KEY_CHECKS = 1;

-- 显示数据库信息
SELECT 'Database nlqdb created successfully' AS status;
SHOW DATABASES;
