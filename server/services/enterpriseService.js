const { getDb } = require('../db');

class EnterpriseService {
  // 企业列表
  async getAllEnterprises() {
    const db = await getDb();
    return db.all('SELECT * FROM enterprises ORDER BY created_at DESC');
  }

  // 获取企业详情
  async getEnterpriseById(id) {
    const db = await getDb();
    return db.get('SELECT * FROM enterprises WHERE id = ?', [id]);
  }

  // 创建企业
  async createEnterprise(data) {
    const db = await getDb();
    const { name, industry, scale, meta_config } = data;
    db.run(
      'INSERT INTO enterprises (name, industry, scale, meta_config) VALUES (?, ?, ?, ?)',
      [name, industry || null, scale || null, meta_config ? JSON.stringify(meta_config) : null]
    );
    // sql.js 没有 lastInsertRowid 属性，需要用 SELECT 获取
    const result = db.get('SELECT last_insert_rowid() as id');
    return { id: result.id, name, industry, scale };
  }

  // 更新企业
  async updateEnterprise(id, data) {
    const db = await getDb();
    const { name, industry, scale, meta_config } = data;
    // sql.js 不接受 undefined，需要转为 null
    const scaleValue = scale === undefined ? null : scale;
    const metaConfigValue = meta_config ? JSON.stringify(meta_config) : null;
    db.run(
      'UPDATE enterprises SET name = ?, industry = ?, scale = ?, meta_config = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
      [name, industry, scaleValue, metaConfigValue, id]
    );
    return this.getEnterpriseById(id);
  }

  // 删除企业
  async deleteEnterprise(id) {
    const db = await getDb();
    db.run('DELETE FROM enterprises WHERE id = ?', [id]);
    return { success: true };
  }
}

module.exports = new EnterpriseService();