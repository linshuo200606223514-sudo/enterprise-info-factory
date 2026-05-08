const express = require('express');
const router = express.Router();

router.get('/enterprises', (req, res) => {
  res.status(404).json({ error: 'Not implemented yet' });
});

module.exports = router;