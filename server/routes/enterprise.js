const express = require('express');
const router = express.Router();
const enterpriseService = require('../services/enterpriseService');

// 响应格式化
function apiResponse(res, data, message = '操作成功', statusCode = 200) {
  res.status(statusCode).json({ success: true, data, message });
}

function apiError(res, error, statusCode = 400) {
  res.status(statusCode).json({ success: false, error: String(error) });
}

// 企业 CRUD
router.get('/enterprises', async (req, res) => {
  try {
    const enterprises = await enterpriseService.getAllEnterprises();
    apiResponse(res, enterprises);
  } catch (e) {
    apiError(res, e);
  }
});

router.get('/enterprises/:id', async (req, res) => {
  try {
    const enterprise = await enterpriseService.getEnterpriseById(req.params.id);
    if (!enterprise) {
      return apiError(res, '企业不存在', 404);
    }
    // 解析 meta_config JSON 字符串
    if (enterprise.meta_config && typeof enterprise.meta_config === 'string') {
      try {
        enterprise.meta_config = JSON.parse(enterprise.meta_config);
      } catch (e) {
        // ignore parse error
      }
    }
    apiResponse(res, enterprise);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises', async (req, res) => {
  try {
    const { name, industry, scale, meta_config } = req.body;
    if (!name) {
      return apiError(res, '企业名称不能为空', 400);
    }
    const enterprise = await enterpriseService.createEnterprise({ name, industry, scale, meta_config });
    apiResponse(res, enterprise, '创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id', async (req, res) => {
  try {
    const { name, industry, scale, meta_config } = req.body;
    const enterprise = await enterpriseService.updateEnterprise(req.params.id, { name, industry, scale, meta_config });
    apiResponse(res, enterprise, '更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id', async (req, res) => {
  try {
    await enterpriseService.deleteEnterprise(req.params.id);
    apiResponse(res, null, '删除成功');
  } catch (e) {
    apiError(res, e);
  }
});

module.exports = router;