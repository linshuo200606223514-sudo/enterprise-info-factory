const express = require('express');
const router = express.Router();
const manualIntervention = require('../services/manualIntervention');

// GET /api/manual-tasks - 获取所有任务
router.get('/', (req, res) => {
  try {
    const { status, assigned_to } = req.query;
    const tasks = manualIntervention.getTasks({ status, assignedTo: assigned_to });
    res.json({ success: true, data: tasks });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// GET /api/manual-tasks/stats - 获取统计
router.get('/stats', (req, res) => {
  try {
    const stats = manualIntervention.getStats();
    res.json({ success: true, data: stats });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// GET /api/manual-tasks/:id - 获取单个任务
router.get('/:id', (req, res) => {
  try {
    const task = manualIntervention.getTaskById(req.params.id);
    if (!task) {
      return res.status(404).json({ success: false, error: '任务不存在' });
    }
    res.json({ success: true, data: task });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// PATCH /api/manual-tasks/:id/status - 更新任务状态
router.patch('/:id/status', (req, res) => {
  try {
    const { status, assigned_to } = req.body;
    if (!['pending', 'in_progress', 'completed'].includes(status)) {
      return res.status(400).json({ success: false, error: '无效的状态' });
    }
    manualIntervention.updateTaskStatus(req.params.id, status, assigned_to);
    res.json({ success: true, data: manualIntervention.getTaskById(req.params.id) });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// POST /api/manual-tasks/:id/complete - 完成任务并录入数据
router.post('/:id/complete', (req, res) => {
  try {
    const { data } = req.body;
    if (!data) {
      return res.status(400).json({ success: false, error: '缺少 data 参数' });
    }
    const task = manualIntervention.completeTask(req.params.id, data);
    res.json({ success: true, data: task, message: '任务已完成' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// DELETE /api/manual-tasks/:id - 删除任务
router.delete('/:id', (req, res) => {
  try {
    manualIntervention.deleteTask(req.params.id);
    res.json({ success: true, message: '任务已删除' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;