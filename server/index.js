require('dotenv').config();
const express = require('express');
const path = require('path');
const { setupCors } = require('./middleware/cors');
const enterpriseRoutes = require('./routes/enterprise');
const alertsRoutes = require('./routes/alerts');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
setupCors(app);

// 静态文件服务（前端）
app.use(express.static(path.join(__dirname, '../frontend')));

// API 路由
app.use('/api', enterpriseRoutes);
app.use('/api/alerts', alertsRoutes);

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
  console.log(`环境: ${process.env.NODE_ENV || 'development'}`);
  console.log(`数据库: ${process.env.DATABASE_URL || 'sqlite:./data/enterprise.db'}`);
});

module.exports = app;