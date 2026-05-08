/**
 * AI 增强分析模块
 * 使用 Claude API 进行企业痛点分析
 */

const ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages';
const MODEL = 'claude-sonnet-4-20250514';

/**
 * 检查 API Key 是否配置
 * @returns {string|null} API key 或 null
 */
function getApiKey() {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.log('提示: 未设置 ANTHROPIC_API_KEY 环境变量，AI 增强分析已跳过');
    return null;
  }
  return apiKey;
}

/**
 * 构建发送给 AI 的分析提示
 * @param {Object} companyData - 企业数据
 * @returns {string} 构建好的提示文本
 */
function buildPrompt(companyData) {
  const {
    companyName = '未知',
    industry = '造纸箱',
    scale = '未知',
    products = [],
    customerCount = 0,
    revenue = '',
    employees = '',
    location = '',
    ...rest
  } = companyData;

  const productList = Array.isArray(products) ? products.join('、') : products;
  const additionalInfo = Object.keys(rest).length > 0
    ? `\n其他信息: ${JSON.stringify(rest, null, 2)}`
    : '';

  return `你是一位企业战略咨询专家，专注于制造业数字化转型。

这是一个造纸箱制造企业，基本信息如下：
- 企业名称: ${companyName}
- 行业: ${industry}
- 企业规模: ${scale}
- 主要产品: ${productList || '未知'}
- 客户数量: ${customerCount || 0}
- 年营收: ${revenue || '未知'}
- 员工人数: ${employees || '未知'}
- 所在地: ${location || '未知'}${additionalInfo}

请分析这家企业的痛点，并输出 JSON 格式的分析结果。

输出格式要求：
{
  "painPoints": [
    {
      "category": "痛点类别",
      "description": "痛点描述",
      "severity": "high|medium|low",
      "suggestion": "建议方案"
    }
  ],
  "opportunities": [
    {
      "area": "机会领域",
      "description": "机会描述",
      "potential": "high|medium|low"
    }
  ],
  "summary": "总体分析摘要"
}`;
}

/**
 * 使用 AI 分析企业数据
 * @param {Object} companyData - 企业数据
 * @returns {Promise<Object|null>} 分析结果或 null
 */
async function analyzeWithAI(companyData) {
  const apiKey = getApiKey();
  if (!apiKey) {
    return null;
  }

  const prompt = buildPrompt(companyData);

  try {
    const response = await fetch(ANTHROPIC_API_URL, {
      method: 'POST',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 4096,
        messages: [
          {
            role: 'user',
            content: prompt
          }
        ]
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`AI API 调用失败: ${response.status} - ${errorText}`);
      return null;
    }

    const result = await response.json();

    // 解析 AI 返回的文本内容
    const aiContent = result.content?.[0]?.text;
    if (!aiContent) {
      console.error('AI 返回内容为空');
      return null;
    }

    // 尝试提取 JSON 部分
    try {
      // 查找 JSON 块或直接解析
      const jsonMatch = aiContent.match(/```json\n?([\s\S]*?)\n?```/) || aiContent.match(/\{[\s\S]*\}/);
      const jsonStr = jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : aiContent;
      return JSON.parse(jsonStr);
    } catch (parseError) {
      console.error('解析 AI 返回的 JSON 失败:', parseError.message);
      // 返回原始内容作为 fallback
      return {
        rawContent: aiContent,
        summary: 'AI 分析结果（JSON 解析失败，请查看 rawContent）'
      };
    }
  } catch (error) {
    console.error('AI 分析失败:', error.message);
    return null;
  }
}

module.exports = {
  analyzeWithAI,
  buildPrompt,
  getApiKey
};