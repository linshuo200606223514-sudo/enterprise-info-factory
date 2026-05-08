const express = require('express');
const router = express.Router();
const enterpriseService = require('../services/enterpriseService');
const { runPythonScraper } = require('../../api/services/aggregator');

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
router.get('/enterprises/:id/orders', async (req, res) => {
  try {
    const orders = await enterpriseService.getOrders(req.params.id);
    apiResponse(res, orders);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises/:id/orders', async (req, res) => {
  try {
    const order = await enterpriseService.createOrder(req.params.id, req.body);
    apiResponse(res, order, '订单创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id/orders/:orderId', async (req, res) => {
  try {
    const order = await enterpriseService.updateOrder(req.params.id, req.params.orderId, req.body);
    apiResponse(res, order, '订单更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id/orders/:orderId', async (req, res) => {
  try {
    await enterpriseService.deleteOrder(req.params.id, req.params.orderId);
    apiResponse(res, null, '订单删除成功');
  } catch (e) {
    apiError(res, e);
  }
});

// 库存路由
router.get('/enterprises/:id/inventory', async (req, res) => {
  try {
    const items = await enterpriseService.getInventory(req.params.id);
    apiResponse(res, items);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises/:id/inventory', async (req, res) => {
  try {
    const item = await enterpriseService.createInventoryItem(req.params.id, req.body);
    apiResponse(res, item, '库存记录创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id/inventory/:itemId', async (req, res) => {
  try {
    const item = await enterpriseService.updateInventoryItem(req.params.id, req.params.itemId, req.body);
    apiResponse(res, item, '库存记录更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id/inventory/:itemId', async (req, res) => {
  try {
    await enterpriseService.deleteInventoryItem(req.params.id, req.params.itemId);
    apiResponse(res, null, '库存记录删除成功');
  } catch (e) {
    apiError(res, e);
  }
});

// 账款路由
router.get('/enterprises/:id/accounts', async (req, res) => {
  try {
    const accounts = await enterpriseService.getAccounts(req.params.id);
    apiResponse(res, accounts);
  } catch (e) {
    apiError(res, e);
  }
});

router.post('/enterprises/:id/accounts', async (req, res) => {
  try {
    const account = await enterpriseService.createAccount(req.params.id, req.body);
    apiResponse(res, account, '账款记录创建成功', 201);
  } catch (e) {
    apiError(res, e);
  }
});

router.put('/enterprises/:id/accounts/:accountId', async (req, res) => {
  try {
    const account = await enterpriseService.updateAccount(req.params.id, req.params.accountId, req.body);
    apiResponse(res, account, '账款记录更新成功');
  } catch (e) {
    apiError(res, e);
  }
});

router.delete('/enterprises/:id/accounts/:accountId', async (req, res) => {
  try {
    await enterpriseService.deleteAccount(req.params.id, req.params.accountId);
    apiResponse(res, null, '账款记录删除成功');
  } catch (e) {
    apiError(res, e);
  }
});

// 多源工商数据采集
router.get('/collect/:companyName/all', async (req, res) => {
  const { companyName } = req.params;

  try {
    // 并行调用所有工商数据源
    const scrapers = [
      { name: 'qichacha', args: [companyName] },
      { name: 'aiqicha', args: [companyName] },
      { name: 'qixin', args: [companyName] },
      { name: 'tianyancha', args: [companyName] }
    ];

    const results = await Promise.allSettled(
      scrapers.map(scraper => runPythonScraper(scraper.name, scraper.args))
    );

    // 提取成功的结果
    const successResults = [];
    const errors = [];

    results.forEach((result, index) => {
      const scraperName = scrapers[index].name;
      if (result.status === 'fulfilled' && result.value && !result.value.error) {
        successResults.push(result.value);
      } else {
        errors.push({
          source: scraperName,
          error: result.reason?.message || result.value?.error || 'Unknown error'
        });
      }
    });

    // 合并数据
    const { mergeCompanyData, generateDataQualityReport } = require('../../api/services/dataMerger');
    const mergedData = mergeCompanyData(successResults);
    const qualityReport = generateDataQualityReport(mergedData, successResults);

    res.json({
      success: true,
      data: {
        merged: mergedData,
        sources: successResults.map(r => r.source),
        source_count: successResults.length,
        errors: errors,
        quality_report: qualityReport
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// 信用评分查询
router.get('/credit-score/:companyName', async (req, res) => {
  const { companyName } = req.params;

  try {
    // 先采集多源数据
    const scrapers = [
      { name: 'qichacha', args: [companyName] },
      { name: 'aiqicha', args: [companyName] },
      { name: 'qixin', args: [companyName] },
      { name: 'tianyancha', args: [companyName] }
    ];

    const results = await Promise.allSettled(
      scrapers.map(scraper => runPythonScraper(scraper.name, scraper.args))
    );

    // 提取成功的结果
    const successResults = [];
    for (const result of results) {
      if (result.status === 'fulfilled' && result.value && !result.value.error) {
        successResults.push(result.value);
      }
    }

    if (successResults.length === 0) {
      return res.json({
        success: false,
        error: '未找到企业数据，请先执行采集'
      });
    }

    // 合并数据
    const { mergeCompanyData } = require('../../api/services/dataMerger');
    const { generateCreditScore } = require('../../api/services/creditScorer');
    const mergedData = mergeCompanyData(successResults);
    const creditScore = generateCreditScore(mergedData);

    res.json({
      success: true,
      data: creditScore
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// 批量信用评分
router.post('/credit-score/batch', async (req, res) => {
  const { companies } = req.body;

  if (!companies || !Array.isArray(companies) || companies.length === 0) {
    return res.status(400).json({
      success: false,
      error: 'companies 参数无效'
    });
  }

  try {
    const { generateCreditScore } = require('../../api/services/creditScorer');
    const { mergeCompanyData } = require('../../api/services/dataMerger');
    const { runPythonScraper } = require('../../api/services/aggregator');

    const results = [];

    for (const companyName of companies) {
      try {
        // 并行采集
        const scrapers = [
          { name: 'qichacha', args: [companyName] },
          { name: 'aiqicha', args: [companyName] },
          { name: 'qixin', args: [companyName] },
          { name: 'tianyancha', args: [companyName] }
        ];

        const scrapeResults = await Promise.allSettled(
          scrapers.map(scraper => runPythonScraper(scraper.name, scraper.args))
        );

        const successResults = scrapeResults
          .filter(r => r.status === 'fulfilled' && r.value && !r.value.error)
          .map(r => r.value);

        if (successResults.length === 0) {
          results.push({
            company_name: companyName,
            credit_score: null,
            credit_grade: null,
            error: '采集失败'
          });
          continue;
        }

        const merged = mergeCompanyData(successResults);
        const score = generateCreditScore(merged);

        results.push({
          company_name: companyName,
          credit_score: score.credit_score,
          credit_grade: score.credit_grade,
          risk_tags: score.risk_tags
        });
      } catch (e) {
        results.push({
          company_name: companyName,
          credit_score: null,
          credit_grade: null,
          error: e.message
        });
      }
    }

    res.json({
      success: true,
      data: {
        results: results,
        total: results.length,
        generated_at: new Date().toISOString()
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;