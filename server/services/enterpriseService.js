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

  // 订单 CRUD
  async getOrders(enterpriseId) {
    const db = await getDb();
    return db.all('SELECT * FROM orders WHERE enterprise_id = ? ORDER BY created_at DESC', [enterpriseId]);
  }

  async createOrder(enterpriseId, data) {
    const db = await getDb();
    const { order_no, customer_name, product_name, quantity, price, status, delivery_date } = data;
    db.run(
      'INSERT INTO orders (enterprise_id, order_no, customer_name, product_name, quantity, price, status, delivery_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
      [enterpriseId, order_no || null, customer_name || null, product_name || null, quantity || 0, price || 0, status || 'pending', delivery_date || null]
    );
    const result = db.get('SELECT last_insert_rowid() as id');
    return { id: result.id, enterprise_id: enterpriseId, order_no, customer_name, product_name, quantity, price, status, delivery_date };
  }

  async updateOrder(enterpriseId, orderId, data) {
    const db = await getDb();
    const { order_no, customer_name, product_name, quantity, price, status, delivery_date } = data;
    db.run(
      'UPDATE orders SET order_no = ?, customer_name = ?, product_name = ?, quantity = ?, price = ?, status = ?, delivery_date = ? WHERE id = ? AND enterprise_id = ?',
      [order_no, customer_name, product_name, quantity, price, status, delivery_date, orderId, enterpriseId]
    );
    return db.get('SELECT * FROM orders WHERE id = ?', [orderId]);
  }

  async deleteOrder(enterpriseId, orderId) {
    const db = await getDb();
    db.run('DELETE FROM orders WHERE id = ? AND enterprise_id = ?', [orderId, enterpriseId]);
    return { success: true };
  }

  // 库存 CRUD
  async getInventory(enterpriseId) {
    const db = await getDb();
    return db.all('SELECT * FROM inventory WHERE enterprise_id = ? ORDER BY updated_at DESC', [enterpriseId]);
  }

  async createInventoryItem(enterpriseId, data) {
    const db = await getDb();
    const { item_name, category, quantity, unit, min_stock } = data;
    db.run(
      'INSERT INTO inventory (enterprise_id, item_name, category, quantity, unit, min_stock) VALUES (?, ?, ?, ?, ?, ?)',
      [enterpriseId, item_name, category || null, quantity || 0, unit || null, min_stock || 0]
    );
    const result = db.get('SELECT last_insert_rowid() as id');
    return { id: result.id, enterprise_id: enterpriseId, item_name, category, quantity, unit, min_stock };
  }

  async updateInventoryItem(enterpriseId, itemId, data) {
    const db = await getDb();
    const { item_name, category, quantity, unit, min_stock } = data;
    db.run(
      'UPDATE inventory SET item_name = ?, category = ?, quantity = ?, unit = ?, min_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND enterprise_id = ?',
      [item_name, category, quantity, unit, min_stock, itemId, enterpriseId]
    );
    return db.get('SELECT * FROM inventory WHERE id = ?', [itemId]);
  }

  async deleteInventoryItem(enterpriseId, itemId) {
    const db = await getDb();
    db.run('DELETE FROM inventory WHERE id = ? AND enterprise_id = ?', [itemId, enterpriseId]);
    return { success: true };
  }

  // 账款 CRUD
  async getAccounts(enterpriseId) {
    const db = await getDb();
    return db.all('SELECT * FROM accounts WHERE enterprise_id = ? ORDER BY created_at DESC', [enterpriseId]);
  }

  async createAccount(enterpriseId, data) {
    const db = await getDb();
    const { type, customer_name, amount, due_date, status } = data;
    db.run(
      'INSERT INTO accounts (enterprise_id, type, customer_name, amount, due_date, status) VALUES (?, ?, ?, ?, ?, ?)',
      [enterpriseId, type, customer_name || null, amount || 0, due_date || null, status || 'unpaid']
    );
    const result = db.get('SELECT last_insert_rowid() as id');
    return { id: result.id, enterprise_id: enterpriseId, type, customer_name, amount, due_date, status };
  }

  async updateAccount(enterpriseId, accountId, data) {
    const db = await getDb();
    const { type, customer_name, amount, due_date, status } = data;
    db.run(
      'UPDATE accounts SET type = ?, customer_name = ?, amount = ?, due_date = ?, status = ? WHERE id = ? AND enterprise_id = ?',
      [type, customer_name, amount, due_date, status, accountId, enterpriseId]
    );
    return db.get('SELECT * FROM accounts WHERE id = ?', [accountId]);
  }

  async deleteAccount(enterpriseId, accountId) {
    const db = await getDb();
    db.run('DELETE FROM accounts WHERE id = ? AND enterprise_id = ?', [accountId, enterpriseId]);
    return { success: true };
  }
}

module.exports = new EnterpriseService();