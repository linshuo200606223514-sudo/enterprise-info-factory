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

// 订单路由
router.get('/enterprises/:id/orders', (req, res) => {
  try {
    const orders = enterpriseService.getOrders(req.params.id);
    apiResponse(res, orders);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises/:id/orders', (req, res) => {
  try {
    const order = enterpriseService.createOrder(req.params.id, req.body);
    apiResponse(res, order, '订单创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id/orders/:orderId', (req, res) => {
  try {
    const order = enterpriseService.updateOrder(req.params.id, req.params.orderId, req.body);
    apiResponse(res, order, '订单更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id/orders/:orderId', (req, res) => {
  try {
    enterpriseService.deleteOrder(req.params.id, req.params.orderId);
    apiResponse(res, null, '订单删除成功');
  } catch (e) {
    apiError(res, e);
  }
});

// 库存路由
router.get('/enterprises/:id/inventory', (req, res) => {
  try {
    const items = enterpriseService.getInventory(req.params.id);
    apiResponse(res, items);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises/:id/inventory', (req, res) => {
  try {
    const item = enterpriseService.createInventoryItem(req.params.id, req.body);
    apiResponse(res, item, '库存记录创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id/inventory/:itemId', (req, res) => {
  try {
    const item = enterpriseService.updateInventoryItem(req.params.id, req.params.itemId, req.body);
    apiResponse(res, item, '库存记录更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id/inventory/:itemId', (req, res) => {
  try {
    enterpriseService.deleteInventoryItem(req.params.id, req.params.itemId);
    apiResponse(res, null, '库存记录删除成功');
  } catch (e) {
    apiError(res, e);
  }
});

// 账款路由
router.get('/enterprises/:id/accounts', (req, res) => {
  try {
    const accounts = enterpriseService.getAccounts(req.params.id);
    apiResponse(res, accounts);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises/:id/accounts', (req, res) => {
  try {
    const account = enterpriseService.createAccount(req.params.id, req.body);
    apiResponse(res, account, '账款记录创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id/accounts/:accountId', (req, res) => {
  try {
    const account = enterpriseService.updateAccount(req.params.id, req.params.accountId, req.body);
    apiResponse(res, account, '账款记录更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id/accounts/:accountId', (req, res) => {
  try {
    enterpriseService.deleteAccount(req.params.id, req.params.accountId);
    apiResponse(res, null, '账款记录删除成功');
  } catch (e) {
    apiError(res, e);
  }
});

module.exports = router;