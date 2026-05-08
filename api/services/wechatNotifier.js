/**
 * 企业微信通知服务
 */

const https = require('https');
const http = require('http');

/**
 * 发送企业微信消息
 * @param {Object} message - 消息内容
 * @returns {Promise<boolean>} 发送是否成功
 */
async function sendWechatMessage(message) {
  const webhookUrl = process.env.WECHAT_WEBHOOK_URL;

  if (!webhookUrl) {
    console.error('WECHAT_WEBHOOK_URL 环境变量未配置');
    return false;
  }

  return new Promise((resolve, reject) => {
    const url = new URL(webhookUrl);
    const options = {
      hostname: url.hostname,
      port: 443,
      path: url.pathname + url.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          if (result.errcode === 0) {
            console.log('企业微信消息发送成功');
            resolve(true);
          } else {
            console.error('企业微信消息发送失败:', result.errmsg);
            resolve(false);
          }
        } catch (e) {
          reject(e);
        }
      });
    });

    req.on('error', (e) => {
      console.error('企业微信消息发送异常:', e.message);
      resolve(false);
    });

    req.write(JSON.stringify(message));
    req.end();
  });
}

/**
 * 构建风险预警消息
 * @param {Object} alert - 预警数据
 * @returns {Object} 企业微信消息格式
 */
function buildAlertMessage(alert) {
  const { company_name, change_type, old_value, new_value, old_score, new_score, old_grade, new_grade, created_at } = alert;

  const levelEmoji = {
    '紧急': '🔴',
    '高': '🟠'
  };

  const emoji = levelEmoji[alert.level] || '⚠️';

  let scoreChange = '';
  if (old_score && new_score) {
    scoreChange = `信用评分从 ${old_score} → ${new_score}，等级 ${old_grade} → ${new_grade}`;
  }

  return {
    msgtype: 'markdown',
    markdown: {
      content: `${emoji} **客户风险预警**\n\n**公司**：${company_name}\n**变更类型**：${change_type}\n${old_value ? `**原值**：${old_value}` : ''}\n${new_value ? `**新值**：${new_value}` : ''}\n${scoreChange ? `**影响**：${scoreChange}` : ''}\n**时间**：${new Date(created_at).toLocaleString('zh-CN')}`
    }
  };
}

/**
 * 发送测试消息
 * @returns {Promise<boolean>}
 */
async function sendTestMessage() {
  const message = {
    msgtype: 'markdown',
    markdown: {
      content: '🟢 **测试消息**\n\n这是一条来自 AI 企业信息工厂的测试消息，监控系统运行正常。\n**时间**：' + new Date().toLocaleString('zh-CN')
    }
  };

  return sendWechatMessage(message);
}

module.exports = {
  sendWechatMessage,
  buildAlertMessage,
  sendTestMessage
};