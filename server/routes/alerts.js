const express = require('express');
const router = express.Router();

/**
 * GET /api/alerts - 查询预警历史
 */
router.get('/', (req, res) => {
  try {
    const { page = 1, limit = 20 } = req.query;
    const offset = (parseInt(page) - 1) * parseInt(limit);

    const db = require('../db').getDb();

    // 查询总数
    const countResult = db.exec('SELECT COUNT(*) as total FROM alerts');
    const total = countResult[0].values[0][0];

    // 查询列表
    const rows = db.exec(`
      SELECT id, company_name, change_type, old_value, new_value,
             old_score, new_score, old_grade, new_grade, alert_sent, created_at
      FROM alerts
      ORDER BY created_at DESC
      LIMIT ? OFFSET ?
    `, [parseInt(limit), offset]);

    const alerts = rows[0].values.map(row => ({
      id: row[0],
      company_name: row[1],
      change_type: row[2],
      old_value: row[3],
      new_value: row[4],
      old_score: row[5],
      new_score: row[6],
      old_grade: row[7],
      new_grade: row[8],
      alert_sent: row[9] === 1,
      created_at: row[10]
    }));

    res.json({
      success: true,
      data: {
        alerts,
        total,
        page: parseInt(page),
        limit: parseInt(limit)
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/alerts/:companyName - 查询指定客户的预警历史
 */
router.get('/:companyName', (req, res) => {
  try {
    const { companyName } = req.params;
    const db = require('../db').getDb();

    const rows = db.exec(`
      SELECT id, company_name, change_type, old_value, new_value,
             old_score, new_score, old_grade, new_grade, alert_sent, created_at
      FROM alerts
      WHERE company_name = ?
      ORDER BY created_at DESC
    `, [companyName]);

    const alerts = rows[0].values.map(row => ({
      id: row[0],
      company_name: row[1],
      change_type: row[2],
      old_value: row[3],
      new_value: row[4],
      old_score: row[5],
      new_score: row[6],
      old_grade: row[7],
      new_grade: row[8],
      alert_sent: row[9] === 1,
      created_at: row[10]
    }));

    res.json({
      success: true,
      data: {
        alerts,
        total: alerts.length
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * POST /api/alerts/test - 测试预警推送
 */
router.post('/test', async (req, res) => {
  try {
    const { sendTestMessage } = require('../../api/services/wechatNotifier');
    const sent = await sendTestMessage();

    if (sent) {
      res.json({ success: true, message: '测试预警推送成功' });
    } else {
      res.status(500).json({ success: false, error: '测试预警推送失败，请检查 WECHAT_WEBHOOK_URL 配置' });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;