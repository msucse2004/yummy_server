const API_BASE = '/api';

async function fetchApi(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw { status: res.status, detail: data.detail || res.statusText };
  return data;
}

const api = {
  async login(username, password) {
    const res = await fetch(API_BASE + '/auth/login', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw { detail: data.detail || '로그인 실패' };
    return data;
  },
  async logout() {
    await fetch(API_BASE + '/auth/logout', { method: 'POST', credentials: 'include' });
  },
  async me() {
    try {
      return await fetchApi('/auth/me');
    } catch { return null; }
  },
  customers: {
    list: () => fetchApi('/customers'),
    create: (d) => fetchApi('/customers', { method: 'POST', body: JSON.stringify(d) }),
    update: (id, d) => fetchApi(`/customers/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
    delete: (id) => fetch(API_BASE + `/customers/${id}`, { method: 'DELETE', credentials: 'include' }),
  },
  items: {
    list: () => fetchApi('/items'),
    create: (d) => fetchApi('/items', { method: 'POST', body: JSON.stringify(d) }),
    update: (id, d) => fetchApi(`/items/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
    delete: (id) => fetch(API_BASE + `/items/${id}`, { method: 'DELETE', credentials: 'include' }),
  },
  plans: {
    list: (from, to) => {
      let url = '/plans';
      if (from || to) url += '?' + new URLSearchParams({ from_date: from || '', to_date: to || '' });
      return fetchApi(url);
    },
    create: (d) => fetchApi('/plans', { method: 'POST', body: JSON.stringify(d) }),
    get: (id) => fetchApi(`/plans/${id}`),
  },
  routes: {
    listByPlan: (planId) => fetchApi(`/routes/plan/${planId}`),
    create: (planId, d) => fetchApi(`/routes/plan/${planId}`, { method: 'POST', body: JSON.stringify(d) }),
    assign: (routeId, driverId) => fetch(API_BASE + `/routes/${routeId}/assign`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ driver_id: driverId }),
    }),
  },
  stops: {
    listByRoute: (routeId) => fetchApi(`/stops/route/${routeId}`),
    create: (routeId, d) => fetchApi(`/stops/route/${routeId}`, { method: 'POST', body: JSON.stringify(d) }),
  },
  completions: {
    complete: (stopId, memo) => {
      const fd = new FormData();
      if (memo) fd.append('memo', memo);
      return fetch(API_BASE + `/completions/stop/${stopId}`, {
        method: 'POST', credentials: 'include', body: fd,
      }).then(r => r.json());
    },
    uploadPhotos: (stopId, files) => {
      const fd = new FormData();
      for (const f of files) fd.append('files', f);
      return fetch(API_BASE + `/completions/stop/${stopId}/photos`, {
        method: 'POST', credentials: 'include', body: fd,
      }).then(r => r.json());
    },
  },
  users: { list: () => fetchApi('/users') },
};
