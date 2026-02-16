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
  config: {
    client: () => fetchApi('/config/client'),
  },
  async checkUsername(username) {
    const res = await fetch(API_BASE + '/auth/check-username?' + new URLSearchParams({ username: (username || '').trim() }), {
      credentials: 'include',
    });
    const data = await res.json().catch(() => ({}));
    return data?.available ?? false;
  },
  async signup(username, password, displayName, phone, preferredLocale = null) {
    const body = {
      username: username.trim(),
      password,
      display_name: displayName?.trim() || '',
      phone: phone?.trim() || '',
    };
    if (preferredLocale && String(preferredLocale).trim()) body.preferred_locale = String(preferredLocale).trim();
    const res = await fetch(API_BASE + '/auth/signup', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw { detail: data.detail || '회원가입 실패' };
    return data;
  },
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
  async changePassword(currentPassword, newPassword) {
    const res = await fetch(API_BASE + '/auth/change-password', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw { detail: data.detail || '비밀번호 변경 실패' };
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
    createFromList: (d) => fetchApi('/plans/create-from-list', { method: 'POST', body: JSON.stringify(d) }),
    getNewPlanDefaults: () => fetchApi('/plans/new-plan-defaults'),
    get: (id) => fetchApi(`/plans/${id}`),
    getPlanDetail: (id) => fetchApi(`/plans/${id}/plan-detail`),
    getEditData: (id) => fetchApi(`/plans/${id}/edit-data`),
    updateFromList: (id, d) => fetchApi(`/plans/${id}/update-from-list`, { method: 'PUT', body: JSON.stringify(d) }),
    update: (id, d) => fetchApi(`/plans/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
    delete: (id) => fetch(API_BASE + `/plans/${id}`, { method: 'DELETE', credentials: 'include' }).then(r => {
      if (!r.ok) return r.json().then(d => { throw { detail: d.detail || r.statusText }; });
    }),
  },
  routes: {
    listByPlan: (planId) => fetchApi(`/routes/plan/${planId}`),
    get: (routeId) => fetchApi(`/routes/${routeId}`),
    start: (routeId) => fetch(API_BASE + `/routes/${routeId}/start`, {
      method: 'POST',
      credentials: 'include',
    }).then(r => {
      if (!r.ok) return r.json().then(d => { throw { detail: d.detail || r.statusText }; });
    }),
    create: (planId, d) => fetchApi(`/routes/plan/${planId}`, { method: 'POST', body: JSON.stringify(d) }),
    assign: (routeId, driverId) => fetch(API_BASE + `/routes/${routeId}/assign`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ driver_id: driverId }),
    }),
    setAssign: (routeId, driverId) => fetch(API_BASE + `/routes/${routeId}/assign`, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ driver_id: driverId ?? null }),
    }).then(r => {
      if (!r.ok) return r.json().then(d => { throw { detail: d.detail || r.statusText }; });
    }),
  },
  stops: {
    listByRoute: (routeId) => fetchApi(`/stops/route/${routeId}`),
    getReceipt: (stopId) => fetchApi(`/stops/${stopId}/receipt`),
    create: (routeId, d) => fetchApi(`/stops/route/${routeId}`, { method: 'POST', body: JSON.stringify(d) }),
    reorder: (routeId, stopIds) => fetch(API_BASE + `/stops/route/${routeId}/reorder`, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stop_ids: stopIds }),
    }).then(r => { if (!r.ok) return r.json().then(d => { throw { detail: d.detail || r.statusText }; }); }),
  },
  completions: {
    complete: (stopId, memo) => {
      const fd = new FormData();
      fd.append('memo', memo ?? '');
      return fetch(API_BASE + `/completions/stop/${stopId}`, {
        method: 'POST', credentials: 'include', body: fd,
      }).then(async (r) => {
        const text = await r.text();
        const data = text ? (() => { try { return JSON.parse(text); } catch { return {}; } })() : {};
        if (!r.ok) throw { detail: data?.detail || r.statusText };
        return data;
      });
    },
    uploadPhotos: (stopId, files) => {
      const fd = new FormData();
      for (const f of files) fd.append('files', f);
      return fetch(API_BASE + `/completions/stop/${stopId}/photos`, {
        method: 'POST', credentials: 'include', body: fd,
      }).then(r => r.json());
    },
  },
  settings: {
    get: () => fetchApi('/settings'),
    getCompanyLocation: () => fetchApi('/settings/company-location'),
    geocodeAddress: (addr) => fetchApi('/settings/geocode?' + new URLSearchParams({ address: addr || '' })),
    update: (d) => fetchApi('/settings', { method: 'PATCH', body: JSON.stringify(d) }),
  },
  users: {
    list: () => fetchApi('/users'),
    create: (d) => fetchApi('/users', { method: 'POST', body: JSON.stringify(d) }),
    update: (id, d) => fetchApi(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
    delete: (id) => fetch(API_BASE + `/users/${id}`, { method: 'DELETE', credentials: 'include' }),
    setPassword: (id, password) => fetch(API_BASE + `/users/${id}/set-password`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    }).then(r => { if (!r.ok) return r.json().then(d => { throw { detail: d.detail || '비밀번호 설정 실패' }; }); }),
    setTemporaryPassword: (id, password) => fetch(API_BASE + `/users/${id}/set-temporary-password`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    }).then(r => { if (!r.ok) return r.json().then(d => { throw { detail: d.detail || '임시 비밀번호 설정 실패' }; }); }),
  },
};
