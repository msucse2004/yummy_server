(async () => {
  const user = await api.me();
  if (!user || user.role !== 'ADMIN') {
    location.href = '/';
    return;
  }
})();

async function doLogout() {
  await api.logout();
  location.href = '/';
}

document.querySelectorAll('.nav-tabs a').forEach(a => {
  a.onclick = (e) => {
    e.preventDefault();
    document.querySelectorAll('.nav-tabs a').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(x => { x.style.display = 'none'; });
    a.classList.add('active');
    const tab = a.dataset.tab;
    document.getElementById('tab-' + tab).style.display = 'block';
    if (tab === 'plans') loadPlans();
    if (tab === 'customers') loadCustomers();
    if (tab === 'items') loadItems();
    if (tab === 'users') loadUsers();
  };
});

async function loadPlans() {
  const from = new Date(); from.setMonth(from.getMonth() - 1);
  const to = new Date(); to.setMonth(to.getMonth() + 2);
  const plans = await api.plans.list(from.toISOString().slice(0,10), to.toISOString().slice(0,10));
  const tbody = document.getElementById('plansList');
  tbody.innerHTML = plans.map(p => `
    <tr>
      <td>${p.plan_date}</td>
      <td>${p.name}</td>
      <td><a href="#" onclick="openPlan(${p.id})">보기</a></td>
    </tr>
  `).join('');
}

function showPlanForm() {
  const d = prompt('날짜(YYYY-MM-DD), 이름 (쉼표로 구분)');
  if (!d) return;
  const [plan_date, name] = d.split(',').map(s => s.trim());
  if (!plan_date || !name) { alert('날짜와 이름을 입력하세요'); return; }
  api.plans.create({ plan_date, name, memo: null }).then(() => { loadPlans(); });
}

async function openPlan(planId) {
  const [plan, routes] = await Promise.all([
    api.plans.get(planId),
    api.routes.listByPlan(planId),
  ]);
  const users = await api.users.list();
  const html = `
    <h2>${plan.plan_date} - ${plan.name}</h2>
    <p><button class="btn btn-secondary" onclick="addRoute(${planId})">+ 루트 추가</button></p>
    ${routes.map(r => `
      <div class="card">
        <h3>${r.name}</h3>
        <p>기사 배정: <select onchange="assignDriver(${r.id}, this.value)">
          <option value="">-</option>
          ${users.filter(u => u.role === 'DRIVER').map(u => `<option value="${u.id}">${u.display_name || u.username}</option>`).join('')}
        </select></p>
        <p><a href="#" onclick="openRoute(${r.id}, ${planId})">스탑 관리</a></p>
      </div>
    `).join('')}
    <p><button onclick="document.getElementById('planDetail').style.display='none'; loadPlans();">닫기</button></p>
  `;
  document.getElementById('planDetail').innerHTML = html;
  document.getElementById('planDetail').style.display = 'block';
}

function addRoute(planId) {
  const name = prompt('루트 이름');
  if (!name) return;
  api.routes.create(planId, { name, sequence: 0 }).then(() => openPlan(planId));
}

function assignDriver(routeId, driverId) {
  if (!driverId) return;
  fetch('/api/routes/' + routeId + '/assign', {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ driver_id: parseInt(driverId) }),
  });
}

async function openRoute(routeId, planId) {
  const stops = await api.stops.listByRoute(routeId);
  const html = `
    <h3>스탑 목록</h3>
    <p><button class="btn btn-secondary" onclick="addStop(${routeId}, ${planId})">+ 스탑 추가</button></p>
    <table><thead><tr><th>순서</th><th>거래처</th><th>품목</th><th>완료</th></tr></thead>
    <tbody>
    ${stops.map(s => `
      <tr>
        <td>${s.sequence}</td>
        <td>${s.customer?.name || s.customer_id}</td>
        <td>${(s.order_items || []).map(oi => (oi.item?.name || oi.item_id) + ' x' + oi.quantity).join(', ') || '-'}</td>
        <td>${s.is_completed ? 'O' : '-'}</td>
      </tr>
    `).join('')}
    </tbody></table>
    <p><button onclick="openPlan(${planId})">뒤로</button></p>
  `;
  document.getElementById('planDetail').innerHTML = html;
}

function addStop(routeId, planId) {
  api.customers.list().then(customers => {
    const c = prompt('거래처 ID 입력 (목록: ' + customers.slice(0,5).map(x => x.id + ':' + x.name).join(', ') + '...)');
    if (!c) return;
    const customerId = parseInt(c);
    api.stops.create(routeId, { customer_id: customerId, sequence: 0, order_items: [] }).then(() => openRoute(routeId, planId));
  });
}

async function deleteAllCustomers() {
  const password = prompt('관리자 비밀번호를 입력하세요.\n모든 거래처, 플랜, 루트, 품목 데이터가 삭제됩니다.');
  if (password === null) return;
  if (!confirm('정말로 모든 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) return;
  try {
    const r = await fetch('/api/customers/delete-all', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw { detail: data.detail || '삭제 실패' };
    alert(data.message || '삭제 완료');
    loadCustomers();
    loadPlans();
    loadItems();
  } catch (e) {
    alert(e?.detail || e?.message || '삭제 실패');
  }
}

async function exportCustomersExcel() {
  try {
    const r = await fetch('/api/customers/export/excel', { credentials: 'include' });
    if (!r.ok) throw new Error('다운로드 실패');
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'customers.xlsx';
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    alert(e.message || '다운로드 실패');
  }
}

async function importCustomersExcel(ev) {
  const file = ev.target.files?.[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.xlsx')) {
    alert('xlsx 파일을 선택해주세요');
    ev.target.value = '';
    return;
  }
  try {
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch('/api/customers/import/excel', {
      method: 'POST',
      credentials: 'include',
      body: fd,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw { detail: data.detail || '가져오기 실패' };
    alert(data.message || '가져오기 완료');
    loadCustomers();
  } catch (e) {
    alert(e.detail || e.message || '가져오기 실패');
  }
  ev.target.value = '';
}

async function loadCustomers() {
  const list = await api.customers.list();
  document.getElementById('customersList').innerHTML = list.map(c => `
    <tr>
      <td>${c.code || '-'}</td>
      <td>${c.route || '-'}</td>
      <td>${c.name}</td>
      <td>${c.phone || '-'}</td>
      <td>${c.contract || '-'}</td>
      <td>${c.address || '-'}</td>
      <td>
        <button class="btn btn-secondary" onclick="showCustomerEditForm(${c.id})">수정</button>
        <button class="btn btn-secondary" onclick="deleteCustomer(${c.id})">삭제</button>
      </td>
    </tr>
  `).join('');
}

function showCustomerForm() {
  const modal = document.getElementById('customerModal');
  if (!modal) return;
  document.getElementById('customerModalTitle').textContent = '거래처 추가';
  document.getElementById('customerId').value = '';
  document.getElementById('customerName').value = '';
  document.getElementById('customerPhone').value = '';
  document.getElementById('customerAddress').value = '';
  document.getElementById('customerCode').value = '';
  document.getElementById('customerRoute').value = '';
  document.getElementById('customerContract').value = '';
  document.getElementById('customerCode').readOnly = false;
  document.getElementById('customerName').readOnly = false;
  modal.style.display = 'flex';
}

function showCustomerEditForm(id) {
  api.customers.list().then(list => {
    const c = list.find(x => x.id === id);
    if (!c) return;
    document.getElementById('customerModalTitle').textContent = '거래처 수정';
    document.getElementById('customerId').value = c.id;
    document.getElementById('customerName').value = c.name;
    document.getElementById('customerPhone').value = c.phone || '';
    document.getElementById('customerAddress').value = c.address || '';
    document.getElementById('customerCode').value = c.code || '';
    document.getElementById('customerRoute').value = c.route || '';
    document.getElementById('customerContract').value = c.contract || '';
    document.getElementById('customerCode').readOnly = true;
    document.getElementById('customerName').readOnly = true;
    document.getElementById('customerModal').style.display = 'flex';
  });
}

function closeCustomerModal() {
  document.getElementById('customerModal').style.display = 'none';
}

async function deleteCustomer(id) {
  if (!confirm('이 거래처를 삭제하시겠습니까?')) return;
  try {
    const r = await fetch('/api/customers/' + id, { method: 'DELETE', credentials: 'include' });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw { detail: data.detail || '삭제 실패' };
    }
    loadCustomers();
  } catch (e) {
    alert(e?.detail || '삭제 실패');
  }
}

const customerFormEl = document.getElementById('customerForm');
if (customerFormEl) customerFormEl.onsubmit = async (e) => {
  e.preventDefault();
  const id = document.getElementById('customerId').value;
  const name = document.getElementById('customerName').value.trim();
  const phone = document.getElementById('customerPhone').value.trim() || null;
  const address = document.getElementById('customerAddress').value.trim() || null;
  const code = document.getElementById('customerCode').value.trim() || null;
  const route = document.getElementById('customerRoute').value.trim() || null;
  const contract = document.getElementById('customerContract').value || null;
  if (!name) { alert('이름을 입력하세요'); return; }
  if (contract && !['계약', '해지'].includes(contract)) { alert('계약은 계약 또는 해지만 선택 가능합니다'); return; }
  const contractVal = contract && ['계약', '해지'].includes(contract) ? contract : null;
  try {
    if (id) {
      await api.customers.update(parseInt(id), { phone, address, route, contract: contractVal });
    } else {
      await api.customers.create({ name, phone, address, code, route, contract: contractVal, memo: null });
    }
    closeCustomerModal();
    loadCustomers();
  } catch (e) {
    alert(e.detail || '저장 실패');
  }
};

async function loadItems() {
  const list = await api.items.list();
  document.getElementById('itemsList').innerHTML = list.map(i => `
    <tr><td>${i.code || '-'}</td><td>${i.name}</td><td>${i.unit}</td><td>${i.price || '-'}</td><td></td></tr>
  `).join('');
}

function showItemForm() {
  const name = prompt('품목 이름');
  if (!name) return;
  api.items.create({ name, code: null, unit: 'EA', price: null }).then(() => loadItems());
}

async function loadUsers() {
  const list = await api.users.list();
  document.getElementById('usersList').innerHTML = list.map(u => `
    <tr><td>${u.username}</td><td>${u.role}</td><td>${u.display_name || '-'}</td></tr>
  `).join('');
}

function showUserForm() {
  const un = prompt('기사 아이디');
  const pw = prompt('비밀번호 (6자 이상)');
  if (!un || !pw || pw.length < 6) { alert('아이디와 비밀번호 6자 이상 필요'); return; }
  fetch('/api/users', {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: un, password: pw, role: 'DRIVER', display_name: null }),
  }).then(r => r.ok ? loadUsers() : r.json().then(d => alert(d.detail || '실패')));
}

function downloadReport() {
  const y = document.getElementById('reportYear').value;
  const m = document.getElementById('reportMonth').value;
  window.open('/api/reports/monthly/pdf?year=' + y + '&month=' + m, '_blank');
}

loadPlans();
