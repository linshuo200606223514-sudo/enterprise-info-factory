const { getDb } = require('../db');

class ManualInterventionService {
  /**
   * 创建人工待办
   * @param {Object} params
   * @param {string} params.companyName - 企业名称
   * @param {string} params.source - 数据源（qichacha/tianyancha/aiqicha/qixin）
   * @param {string} params.reason - 原因（如 "requires_login", "captcha", "blocked"）
   * @param {string} params.rawData - 爬虫返回的原始数据（JSON字符串）
   * @param {Array} params.requiredFields - 需要人工补充的字段列表
   * @returns {Object} 创建的待办记录
   */
  createTask({ companyName, source, reason, rawData = null, requiredFields = [] }) {
    try {
      const db = getDb();
      db.run(
        `INSERT INTO manual_tasks (company_name, source, reason, raw_data, required_fields, status)
         VALUES (?, ?, ?, ?, ?, 'pending')`,
        [companyName, source, reason, rawData ? JSON.stringify(rawData) : null, JSON.stringify(requiredFields)]
      );
      const result = db.get('SELECT last_insert_rowid() as id');
      return { id: result.id, company_name: companyName, source, reason, status: 'pending' };
    } catch (e) {
      console.error('[ManualInterventionService] createTask error:', e.message);
      throw e;
    }
  }

  /**
   * 获取所有待处理人工任务
   * @param {Object} options
   * @param {string} options.status - pending/in_progress/completed
   * @param {string} options.assignedTo - 按负责人筛选
   * @returns {Array}
   */
  getTasks({ status = null, assignedTo = null } = {}) {
    const db = getDb();
    let sql = 'SELECT * FROM manual_tasks WHERE 1=1';
    const params = [];
    if (status) {
      sql += ' AND status = ?';
      params.push(status);
    }
    if (assignedTo) {
      sql += ' AND assigned_to = ?';
      params.push(assignedTo);
    }
    sql += ' ORDER BY created_at DESC';
    return db.all(sql, params);
  }

  /**
   * 获取单个任务详情
   * @param {number} id
   * @returns {Object|null}
   */
  getTaskById(id) {
    const db = getDb();
    const task = db.get('SELECT * FROM manual_tasks WHERE id = ?', [id]);
    if (task && task.raw_data) {
      try { task.raw_data = JSON.parse(task.raw_data); } catch (e) { console.warn('[ManualInterventionService] JSON.parse raw_data failed:', e.message); }
    }
    if (task && task.required_fields) {
      try { task.required_fields = JSON.parse(task.required_fields); } catch (e) { console.warn('[ManualInterventionService] JSON.parse required_fields failed:', e.message); }
    }
    return task;
  }

  /**
   * 完成任务并更新企业数据
   * @param {number} id
   * @param {Object} data - 人工录入的数据
   * @returns {Object}
   */
  completeTask(id, data) {
    if (!data) {
      throw new Error('[ManualInterventionService] completeTask requires data parameter');
    }
    console.log('[ManualInterventionService] Completing task', id, 'with data:', JSON.stringify(data));
    const db = getDb();
    db.run(
      `UPDATE manual_tasks SET status = 'completed', updated_at = datetime('now'), completed_at = datetime('now') WHERE id = ?`,
      [id]
    );
    return this.getTaskById(id);
  }

  /**
   * 更新任务状态
   * @param {number} id
   * @param {string} status - pending/in_progress/completed
   * @param {string} assignedTo - 负责人
   */
  updateTaskStatus(id, status, assignedTo = null) {
    const db = getDb();
    if (assignedTo) {
      db.run(
        `UPDATE manual_tasks SET status = ?, assigned_to = ?, updated_at = datetime('now') WHERE id = ?`,
        [status, assignedTo, id]
      );
    } else {
      db.run(
        `UPDATE manual_tasks SET status = ?, updated_at = datetime('now') WHERE id = ?`,
        [status, id]
      );
    }
  }

  /**
   * 删除任务
   * @param {number} id
   */
  deleteTask(id) {
    const db = getDb();
    db.run('DELETE FROM manual_tasks WHERE id = ?', [id]);
    return { success: true };
  }

  /**
   * 获取任务统计
   * @returns {Object}
   */
  getStats() {
    const db = getDb();
    const pending = db.get("SELECT COUNT(*) as count FROM manual_tasks WHERE status = 'pending'");
    const inProgress = db.get("SELECT COUNT(*) as count FROM manual_tasks WHERE status = 'in_progress'");
    const completed = db.get("SELECT COUNT(*) as count FROM manual_tasks WHERE status = 'completed'");
    return {
      pending: pending.count,
      in_progress: inProgress.count,
      completed: completed.count,
      total: pending.count + inProgress.count + completed.count
    };
  }
}

module.exports = new ManualInterventionService();