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
    if (tab === 'settings') loadSettings();
  };
});

async function loadPlans() {
  const from = new Date(); from.setMonth(from.getMonth() - 1);
  const to = new Date(); to.setMonth(to.getMonth() + 2);
  const plans = await api.plans.list(from.toISOString().slice(0,10), to.toISOString().slice(0,10));
  const tbody = document.getElementById('plansList');
  tbody.innerHTML = plans.map(p => `
    <tr>
      <td>${p.route || '-'}</td>
      <td>${p.name}</td>
      <td><a href="#" onclick="openPlan(${p.id})">보기</a></td>
    </tr>
  `).join('');
}

async function showPlanForm() {
  const sel = document.getElementById('planRoute');
  sel.innerHTML = '<option value="">선택</option>';
  try {
    const s = await api.settings.get();
    const n = s.delivery_route_count ?? 5;
    for (let i = 1; i <= n; i++) {
      const opt = document.createElement('option');
      opt.value = i + '호차';
      opt.textContent = i + '호차';
      sel.appendChild(opt);
    }
  } catch {
    for (let i = 1; i <= 5; i++) {
      const opt = document.createElement('option');
      opt.value = i + '호차';
      opt.textContent = i + '호차';
      sel.appendChild(opt);
    }
  }
  document.getElementById('planName').value = '';
  document.getElementById('planModal').style.display = 'flex';
}

function closePlanModal() {
  document.getElementById('planModal').style.display = 'none';
}

const planFormEl = document.getElementById('planForm');
if (planFormEl) planFormEl.onsubmit = async (e) => {
  e.preventDefault();
  const route = document.getElementById('planRoute').value;
  const name = document.getElementById('planName').value.trim();
  if (!route) { alert('루트를 선택하세요'); return; }
  if (!name) { alert('이름을 입력하세요'); return; }
  const today = new Date().toISOString().slice(0, 10);
  try {
    await api.plans.create({ plan_date: today, route, name, memo: null });
    closePlanModal();
    loadPlans();
  } catch (e) {
    alert(e?.detail || e?.message || '저장 실패');
  }
};

async function openPlan(planId) {
  const [plan, routes] = await Promise.all([
    api.plans.get(planId),
    api.routes.listByPlan(planId),
  ]);
  const users = await api.users.list();
  const html = `
    <h2>${plan.route || '-'} - ${plan.name}</h2>
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
        <td>${(s.order_items || []).map(oi => (oi.item?.product || oi.item_id) + ' x' + oi.quantity).join(', ') || '-'}</td>
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

let customerSortCol = 'name';
let customerSortAsc = true;
let customersData = [];

function bindCustomerSortHandlers() {
  document.querySelectorAll('#tab-customers th.sortable').forEach(th => {
    th.onclick = () => {
      const col = th.dataset.sort;
      if (customerSortCol === col) customerSortAsc = !customerSortAsc;
      else { customerSortCol = col; customerSortAsc = true; }
      renderCustomers();
      updateCustomerSortIcons();
    };
  });
}

async function loadCustomers() {
  customersData = await api.customers.list();
  renderCustomers();
  updateCustomerSortIcons();
  bindCustomerSortHandlers();
}

function updateCustomerSortIcons() {
  document.querySelectorAll('#tab-customers th.sortable').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.dataset.sort === customerSortCol) {
      th.classList.add(customerSortAsc ? 'sort-asc' : 'sort-desc');
    }
  });
}

function renderCustomers() {
  const numCols = ['latitude', 'longitude'];
  const sorted = [...customersData].sort((a, b) => {
    const av = a[customerSortCol];
    const bv = b[customerSortCol];
    let cmp;
    if (numCols.includes(customerSortCol)) {
      const an = av != null ? Number(av) : NaN;
      const bn = bv != null ? Number(bv) : NaN;
      cmp = (isNaN(an) ? -Infinity : an) - (isNaN(bn) ? -Infinity : bn);
    } else {
      cmp = (av || '').toString().localeCompare((bv || '').toString(), 'ko');
    }
    return customerSortAsc ? cmp : -cmp;
  });
  document.getElementById('customersList').innerHTML = sorted.map(c => `
    <tr>
      <td>${c.code || '-'}</td>
      <td>${c.route || '-'}</td>
      <td>${c.name}</td>
      <td>${c.phone || '-'}</td>
      <td>${c.contract || '-'}</td>
      <td>${c.address || '-'}</td>
      <td>${c.latitude != null ? Number(c.latitude).toFixed(5) : '-'}</td>
      <td>${c.longitude != null ? Number(c.longitude).toFixed(5) : '-'}</td>
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
  document.getElementById('customerLatitude').value = '';
  document.getElementById('customerLongitude').value = '';
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
    document.getElementById('customerLatitude').value = c.latitude != null ? c.latitude : '';
    document.getElementById('customerLongitude').value = c.longitude != null ? c.longitude : '';
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
  const latVal = document.getElementById('customerLatitude').value.trim();
  const lngVal = document.getElementById('customerLongitude').value.trim();
  const latitude = latVal ? parseFloat(latVal) : null;
  const longitude = lngVal ? parseFloat(lngVal) : null;
  if (!name) { alert('이름을 입력하세요'); return; }
  if (contract && !['계약', '해지'].includes(contract)) { alert('계약은 계약 또는 해지만 선택 가능합니다'); return; }
  const contractVal = contract && ['계약', '해지'].includes(contract) ? contract : null;
  if (latVal && (isNaN(latitude) || latitude < -90 || latitude > 90)) { alert('위도는 -90~90 사이로 입력하세요'); return; }
  if (lngVal && (isNaN(longitude) || longitude < -180 || longitude > 180)) { alert('경도는 -180~180 사이로 입력하세요'); return; }
  try {
    if (id) {
      await api.customers.update(parseInt(id), { phone, address, route, contract: contractVal, latitude, longitude });
    } else {
      await api.customers.create({ name, phone, address, code, route, contract: contractVal, latitude, longitude, memo: null });
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
    <tr>
      <td>${i.code || '-'}</td>
      <td>${i.product}</td>
      <td>${i.weight != null ? i.weight : '-'}</td>
      <td>${i.unit}</td>
      <td>${i.unit_price != null ? i.unit_price.toLocaleString('ko-KR') + '원' : '-'}</td>
      <td>
        <button class="btn btn-secondary" onclick="showItemEditForm(${i.id})">수정</button>
        <button class="btn btn-secondary" onclick="deleteItem(${i.id})">삭제</button>
      </td>
    </tr>
  `).join('');
}

function showItemForm() {
  document.getElementById('itemModalTitle').textContent = '품목 추가';
  document.getElementById('itemId').value = '';
  document.getElementById('itemProduct').value = '';
  document.getElementById('itemWeight').value = '';
  document.getElementById('itemUnit').value = 'EA';
  document.getElementById('itemUnitPrice').value = '';
  document.getElementById('itemModal').style.display = 'flex';
}

function showItemEditForm(id) {
  api.items.list().then(list => {
    const i = list.find(x => x.id === id);
    if (!i) return;
    document.getElementById('itemModalTitle').textContent = '품목 수정';
    document.getElementById('itemId').value = i.id;
    document.getElementById('itemProduct').value = i.product || '';
    document.getElementById('itemWeight').value = i.weight != null ? i.weight : '';
    document.getElementById('itemUnit').value = i.unit || 'EA';
    document.getElementById('itemUnitPrice').value = i.unit_price != null ? i.unit_price : '';
    document.getElementById('itemModal').style.display = 'flex';
  });
}

function closeItemModal() {
  document.getElementById('itemModal').style.display = 'none';
}

const itemFormEl = document.getElementById('itemForm');
if (itemFormEl) itemFormEl.onsubmit = async (e) => {
  e.preventDefault();
  const id = document.getElementById('itemId').value;
  const product = document.getElementById('itemProduct').value.trim();
  const weightVal = document.getElementById('itemWeight').value.trim();
  const unit = document.getElementById('itemUnit').value.trim() || 'EA';
  const priceVal = document.getElementById('itemUnitPrice').value.trim();
  if (!product) { alert('상품명을 입력하세요'); return; }
  const weight = weightVal ? parseFloat(weightVal) : null;
  const unit_price = priceVal ? parseFloat(priceVal) : null;
  if (weightVal && isNaN(weight)) { alert('무게는 숫자로 입력하세요'); return; }
  if (priceVal && isNaN(unit_price)) { alert('단가는 숫자로 입력하세요'); return; }
  try {
    if (id) {
      await api.items.update(parseInt(id), { product, weight, unit, unit_price });
    } else {
      await api.items.create({ product, weight, unit, unit_price });
    }
    closeItemModal();
    loadItems();
  } catch (e) {
    alert(e?.detail || '저장 실패');
  }
};

async function deleteItem(id) {
  if (!confirm('이 품목을 삭제하시겠습니까?')) return;
  try {
    const r = await fetch('/api/items/' + id, { method: 'DELETE', credentials: 'include' });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw { detail: data.detail || '삭제 실패' };
    }
    loadItems();
  } catch (e) {
    alert(e?.detail || '삭제 실패');
  }
}

async function exportItemsExcel() {
  try {
    const r = await fetch('/api/items/export/excel', { credentials: 'include' });
    if (!r.ok) throw new Error('다운로드 실패');
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'items.xlsx';
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    alert(e.message || '다운로드 실패');
  }
}

async function importItemsExcel(ev) {
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
    const r = await fetch('/api/items/import/excel', {
      method: 'POST',
      credentials: 'include',
      body: fd,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw { detail: data.detail || '가져오기 실패' };
    alert(data.message || '가져오기 완료');
    loadItems();
  } catch (e) {
    alert(e.detail || e.message || '가져오기 실패');
  }
  ev.target.value = '';
}

async function exportUsersExcel() {
  try {
    const r = await fetch('/api/users/export/excel', { credentials: 'include' });
    if (!r.ok) throw new Error('다운로드 실패');
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'users.xlsx';
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    alert(e.message || '다운로드 실패');
  }
}

async function importUsersExcel(ev) {
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
    const r = await fetch('/api/users/import/excel', {
      method: 'POST',
      credentials: 'include',
      body: fd,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw { detail: data.detail || '가져오기 실패' };
    alert(data.message || '가져오기 완료');
    loadUsers();
  } catch (e) {
    alert(e.detail || e.message || '가져오기 실패');
  }
  ev.target.value = '';
}

async function loadUsers() {
  const list = await api.users.list();
  document.getElementById('usersList').innerHTML = list.map(u => `
    <tr>
      <td>${u.username}</td>
      <td>${u.role === 'ADMIN' ? '관리자' : '기사'}</td>
      <td>${u.display_name || '-'}</td>
      <td>${u.ssn || '-'}</td>
      <td>${u.phone || '-'}</td>
      <td>${u.resume ? (u.resume.length > 20 ? u.resume.slice(0, 20) + '...' : u.resume) : '-'}</td>
      <td>${u.status || '-'}</td>
      <td>
        ${u.status === '승인요청중' ? `<button class="btn btn-primary" onclick="approveUser(${u.id})">승인하기</button> ` : ''}
        <button class="btn btn-secondary" onclick="showUserEditForm(${u.id})">수정</button>
        <button class="btn btn-secondary" onclick="deleteUser(${u.id})">삭제</button>
      </td>
    </tr>
  `).join('');
}

function showUserForm() {
  document.getElementById('userModalTitle').textContent = '사용자 추가';
  document.getElementById('userId').value = '';
  document.getElementById('userUsername').value = '';
  document.getElementById('userUsername').readOnly = false;
  document.getElementById('userPassword').value = '';
  document.getElementById('userPasswordGroup').style.display = 'block';
  document.getElementById('userDisplayName').value = '';
  document.getElementById('userRole').value = 'DRIVER';
  document.getElementById('userSsn').value = '';
  document.getElementById('userPhone').value = '';
  document.getElementById('userResume').value = '';
  document.getElementById('userStatus').value = '';
  document.getElementById('userModal').style.display = 'flex';
}

function showUserEditForm(id) {
  api.users.list().then(list => {
    const u = list.find(x => x.id === id);
    if (!u) return;
    document.getElementById('userModalTitle').textContent = '사용자 수정';
    document.getElementById('userId').value = u.id;
    document.getElementById('userUsername').value = u.username;
    document.getElementById('userUsername').readOnly = true;
    document.getElementById('userPassword').value = '';
    document.getElementById('userPasswordGroup').style.display = 'none';
    document.getElementById('userDisplayName').value = u.display_name || '';
    document.getElementById('userRole').value = u.role || 'DRIVER';
    document.getElementById('userSsn').value = u.ssn || '';
    document.getElementById('userPhone').value = u.phone || '';
    document.getElementById('userResume').value = u.resume || '';
    document.getElementById('userStatus').value = u.status || '';
    document.getElementById('userModal').style.display = 'flex';
  });
}

function closeUserModal() {
  document.getElementById('userModal').style.display = 'none';
}

async function approveUser(id) {
  try {
    await api.users.update(id, { status: '재직' });
    loadUsers();
  } catch (e) {
    const msg = e?.detail || e?.message || '승인 실패';
    alert(Array.isArray(msg) ? msg.join('; ') : msg);
  }
}

async function deleteUser(id) {
  const list = await api.users.list();
  const u = list.find(x => x.id === id);
  const name = u ? (u.display_name || u.username) : id;
  if (!confirm(`사용자 '${name}'를 삭제하시겠습니까?`)) return;
  try {
    const r = await api.users.delete(id);
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw { detail: data.detail || '삭제 실패' };
    }
    loadUsers();
  } catch (e) {
    const msg = e?.detail || e?.message || '삭제 실패';
    alert(msg);
  }
}

const userFormEl = document.getElementById('userForm');
if (userFormEl) userFormEl.onsubmit = async (e) => {
  e.preventDefault();
  const id = document.getElementById('userId').value;
  const username = document.getElementById('userUsername').value.trim();
  const password = document.getElementById('userPassword').value;
  const display_name = document.getElementById('userDisplayName').value.trim() || null;
  const role = document.getElementById('userRole').value;
  const ssn = document.getElementById('userSsn').value.trim() || null;
  const phone = document.getElementById('userPhone').value.trim() || null;
  const resume = document.getElementById('userResume').value.trim() || null;
  const status = document.getElementById('userStatus').value.trim() || null;
  if (!username) { alert('아이디를 입력하세요'); return; }
  try {
    if (id) {
      await api.users.update(parseInt(id), { display_name, role, ssn, phone, resume, status });
    } else {
      if (!password || password.length < 6) { alert('비밀번호 6자 이상 필요'); return; }
      await api.users.create({ username, password, role, display_name, ssn, phone, resume, status });
    }
    closeUserModal();
    loadUsers();
  } catch (e) {
    let msg = '저장 실패';
    if (e?.detail) {
      msg = Array.isArray(e.detail)
        ? e.detail.map(x => x.msg || (x.loc && x.loc.join('.')) || '').filter(Boolean).join('; ') || e.detail[0]?.msg
        : String(e.detail);
    } else if (e?.message) msg = e.message;
    alert(msg);
  }
};

function downloadReport() {
  const y = document.getElementById('reportYear').value;
  const m = document.getElementById('reportMonth').value;
  window.open('/api/reports/monthly/pdf?year=' + y + '&month=' + m, '_blank');
}

async function loadSettings() {
  try {
    const s = await api.settings.get();
    document.getElementById('settingCompanyName').value = s.company_name || '';
    document.getElementById('settingCompanyAddress').value = s.company_address || '';
    document.getElementById('settingCompanyPhone').value = s.company_phone || '';
    document.getElementById('settingDeliveryRouteCount').value = s.delivery_route_count ?? 5;
  } catch (e) {
    document.getElementById('settingDeliveryRouteCount').value = 5;
  }
}

const settingsFormEl = document.getElementById('settingsForm');
if (settingsFormEl) settingsFormEl.onsubmit = async (e) => {
  e.preventDefault();
  const company_name = document.getElementById('settingCompanyName').value.trim() || null;
  const company_address = document.getElementById('settingCompanyAddress').value.trim() || null;
  const company_phone = document.getElementById('settingCompanyPhone').value.trim() || null;
  const val = parseInt(document.getElementById('settingDeliveryRouteCount').value, 10);
  if (isNaN(val) || val < 1 || val > 99) {
    alert('배달 루트 개수는 1~99 사이로 입력하세요');
    return;
  }
  try {
    await api.settings.update({
      company_name,
      company_address,
      company_phone,
      delivery_route_count: val,
    });
    alert('저장되었습니다');
  } catch (e) {
    alert(e?.detail || e?.message || '저장 실패');
  }
};

loadPlans();
