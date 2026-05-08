#!/usr/bin/env node
/**
 * 导入已有企业数据到系统
 * 用法: node bin/import-enterprise.js "企业名称" --meta-config ./output/企业_meta_config.json
 */

const fs = require('fs');
const path = require('path');
require('dotenv').config();
const { getDb, closeDb } = require('../server/db');

async function importEnterprise(companyName, metaConfigPath) {
  const db = await getDb();

  // 读取 meta_config 文件
  let metaConfig = null;
  if (metaConfigPath && fs.existsSync(metaConfigPath)) {
    const content = fs.readFileSync(metaConfigPath, 'utf8');
    metaConfig = JSON.parse(content);
  }

  // 构建企业数据
  const enterprise = {
    name: metaConfig?.company?.name || companyName,
    industry: metaConfig?.company?.industry || '',
    scale: metaConfig?.company?.scale || 'unknown',
    meta_config: metaConfig
  };

  // 插入数据库
  db.run(
    'INSERT INTO enterprises (name, industry, scale, meta_config) VALUES (?, ?, ?, ?)',
    [enterprise.name, enterprise.industry, enterprise.scale, JSON.stringify(enterprise.meta_config)]
  );

  const result = db.get('SELECT last_insert_rowid() as id');

  console.log(`企业导入成功！`);
  console.log(`企业ID: ${result.id}`);
  console.log(`企业名称: ${enterprise.name}`);
  console.log(`行业: ${enterprise.industry}`);
  console.log(`规模: ${enterprise.scale}`);

  closeDb();
  return result.id;
}

// 命令行解析
const args = process.argv.slice(2);
if (args.length < 1) {
  console.log('用法: node bin/import-enterprise.js "企业名称" [--meta-config <文件路径>]');
  process.exit(1);
}

const companyName = args[0];
let metaConfigPath = null;

for (let i = 1; i < args.length; i++) {
  if (args[i] === '--meta-config' && args[i + 1]) {
    metaConfigPath = args[i + 1];
    break;
  }
}

importEnterprise(companyName, metaConfigPath)
  .then(() => process.exit(0))
  .catch(err => {
    console.error('导入失败:', err);
    process.exit(1);
  });