const cors = require('cors');

function setupCors(app) {
  const origin = process.env.CORS_ORIGIN || 'http://localhost:3001';
  app.use(cors({
    origin,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
  }));
}

module.exports = { setupCors };