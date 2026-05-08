// frontend/assets/js/api.js
const API_BASE = '/api';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options
  };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }
  const res = await fetch(url, config);
  const json = await res.json();
  if (!json.success) {
    throw new Error(json.error || '请求失败');
  }
  return json.data;
}

// 企业 API
const enterpriseApi = {
  list: () => request('/enterprises'),
  get: (id) => request(`/enterprises/${id}`),
  create: (data) => request('/enterprises', { method: 'POST', body: data }),
  update: (id, data) => request(`/enterprises/${id}`, { method: 'PUT', body: data }),
  delete: (id) => request(`/enterprises/${id}`, { method: 'DELETE' }),
  getOrders: (id) => request(`/enterprises/${id}/orders`),
  createOrder: (id, data) => request(`/enterprises/${id}/orders`, { method: 'POST', body: data }),
  updateOrder: (id, orderId, data) => request(`/enterprises/${id}/orders/${orderId}`, { method: 'PUT', body: data }),
  deleteOrder: (id, orderId) => request(`/enterprises/${id}/orders/${orderId}`, { method: 'DELETE' }),
  getInventory: (id) => request(`/enterprises/${id}/inventory`),
  createInventory: (id, data) => request(`/enterprises/${id}/inventory`, { method: 'POST', body: data }),
  updateInventory: (id, itemId, data) => request(`/enterprises/${id}/inventory/${itemId}`, { method: 'PUT', body: data }),
  deleteInventory: (id, itemId) => request(`/enterprises/${id}/inventory/${itemId}`, { method: 'DELETE' }),
  getAccounts: (id) => request(`/enterprises/${id}/accounts`),
  createAccount: (id, data) => request(`/enterprises/${id}/accounts`, { method: 'POST', body: data }),
  updateAccount: (id, accountId, data) => request(`/enterprises/${id}/accounts/${accountId}`, { method: 'PUT', body: data }),
  deleteAccount: (id, accountId) => request(`/enterprises/${id}/accounts/${accountId}`, { method: 'DELETE' })
};