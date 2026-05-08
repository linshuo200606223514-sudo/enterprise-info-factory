/**
 * 定时任务入口
 */

const cron = require('node-cron');

let isRunning = false;

/**
 * 启动每日监控定时任务
 * 执行时间：每日 08:00
 */
function startDailyMonitor() {
  console.log('[定时任务] 每日监控已启动，执行时间：每天 08:00');

  cron.schedule('0 8 * * *', async () => {
    if (isRunning) {
      console.log('[定时任务] 上一次任务仍在执行中，跳过本次');
      return;
    }

    isRunning = true;
    try {
      const { runDailyMonitor } = require('../../api/services/changeMonitor');
      await runDailyMonitor();
    } catch (error) {
      console.error('[定时任务] 执行异常:', error.message);
    } finally {
      isRunning = false;
    }
  });
}

/**
 * 手动触发一次监控任务
 */
async function triggerMonitor() {
  if (isRunning) {
    console.log('[定时任务] 上一次任务仍在执行中');
    return { running: true };
  }

  isRunning = true;
  try {
    const { runDailyMonitor } = require('../../api/services/changeMonitor');
    const result = await runDailyMonitor();
    return { running: false, ...result };
  } catch (error) {
    console.error('[定时任务] 执行异常:', error.message);
    return { running: false, error: error.message };
  } finally {
    isRunning = false;
  }
}

module.exports = {
  startDailyMonitor,
  triggerMonitor
};