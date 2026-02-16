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
    if (tab === 'arrears') loadArrears();
    if (tab === 'items') loadItems();
    if (tab === 'users') loadUsers();
    if (tab === 'settings') loadSettings();
  };
});

let plansData = [];
let planSortCol = 'plan_date';
let planSortAsc = false;

function bindPlanSortHandlers() {
  document.querySelectorAll('#tab-plans th.sortable').forEach(th => {
    th.onclick = () => {
      const col = th.dataset.sort;
      if (planSortCol === col) planSortAsc = !planSortAsc;
      else { planSortCol = col; planSortAsc = true; }
      renderPlans();
      updatePlanSortIcons();
    };
  });
}

function updatePlanSortIcons() {
  document.querySelectorAll('#tab-plans th.sortable').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.dataset.sort === planSortCol) {
      th.classList.add(planSortAsc ? 'sort-asc' : 'sort-desc');
    }
  });
}

function renderPlans() {
  const sorted = [...plansData].sort((a, b) => {
    const av = a[planSortCol];
    const bv = b[planSortCol];
    let cmp;
    if (planSortCol === 'plan_date') {
      cmp = (av || '').localeCompare(bv || '');
    } else if (planSortCol === 'daily_sales') {
      const an = av != null ? Number(av) : 0;
      const bn = bv != null ? Number(bv) : 0;
      cmp = an - bn;
    } else {
      cmp = (av || '').toString().localeCompare((bv || '').toString(), 'ko');
    }
    return planSortAsc ? cmp : -cmp;
  });
  const tbody = document.getElementById('plansList');
  tbody.innerHTML = sorted.map(p => `
    <tr class="plan-row-clickable" onclick="openPlan(${p.id})">
      <td>${p.plan_date || '-'}</td>
      <td>${p.delivery_quantity || '-'}</td>
      <td>${p.daily_sales != null && p.daily_sales > 0 ? p.daily_sales.toLocaleString('ko-KR') + '원' : '-'}</td>
      <td class="plan-actions" onclick="event.stopPropagation()">
        <button type="button" class="btn btn-secondary" onclick="showPlanEditModal(${p.id})">수정</button>
        <button type="button" class="btn btn-secondary" onclick="deletePlan(${p.id})">삭제</button>
      </td>
    </tr>
  `).join('');
}

async function loadPlans() {
  const from = new Date(); from.setMonth(from.getMonth() - 1);
  const to = new Date(); to.setMonth(to.getMonth() + 2);
  plansData = await api.plans.list(from.toISOString().slice(0,10), to.toISOString().slice(0,10));
  bindPlanSortHandlers();
  renderPlans();
  updatePlanSortIcons();
}

let newPlanFormData = null;

function updateNewPlanTitleFromDate() {
  const inp = document.getElementById('newPlanDate');
  if (!inp || !inp.value) return;
  const d = new Date(inp.value + 'T12:00:00');
  document.getElementById('newPlanTitle').textContent = `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 배달 플랜`;
  if (newPlanFormData) newPlanFormData.plan_date = inp.value;
}

async function showPlanForm(planId) {
  try {
    const data = planId
      ? await api.plans.getEditData(planId)
      : await api.plans.getNewPlanDefaults();
    newPlanFormData = data;
    const d = new Date(data.plan_date + 'T12:00:00');
    const title = `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 배달 플랜`;
    document.getElementById('newPlanTitle').textContent = title;
    const dateInp = document.getElementById('newPlanDate');
    if (dateInp) dateInp.value = data.plan_date || '';
    const tbody = document.getElementById('newPlanTableBody');
    tbody.innerHTML = (data.rows || []).map((r, i) => `
      <tr data-customer-id="${r.customer_id}">
        <td>${(r.code || '-').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}</td>
        <td>${(r.route || '-').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}</td>
        <td>${(r.name || '-').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}</td>
        <td><input type="text" class="new-plan-delivery-input" data-idx="${i}" placeholder="예: 곱슬이 2박스, 일자 3박스"></td>
      </tr>
    `).join('');
    (data.rows || []).forEach((r, i) => {
      const inp = document.querySelector(`.new-plan-delivery-input[data-idx="${i}"]`);
      if (inp) inp.value = r.delivery_items || '';
    });
    document.getElementById('planListPanel').style.display = 'none';
    document.getElementById('newPlanFullScreen').style.display = 'block';
  } catch (e) {
    alert(e?.detail || e?.message || '데이터 로드 실패');
  }
}

function closeNewPlanForm() {
  document.getElementById('planListPanel').style.display = 'block';
  document.getElementById('newPlanFullScreen').style.display = 'none';
  newPlanFormData = null;
}

async function saveNewPlanFromList() {
  if (!newPlanFormData || !newPlanFormData.rows) return;
  const rows = newPlanFormData.rows.map((r, i) => {
    const inp = document.querySelector(`.new-plan-delivery-input[data-idx="${i}"]`);
    return {
      customer_id: r.customer_id,
      code: r.code,
      route: r.route || '',
      name: r.name,
      delivery_items: inp ? inp.value.trim() : (r.delivery_items || ''),
    };
  });
  const planDate = document.getElementById('newPlanDate')?.value || newPlanFormData.plan_date;
  if (!planDate) { alert('날짜를 선택하세요'); return; }
  const planId = newPlanFormData.plan_id;
  try {
    if (planId) {
      await api.plans.updateFromList(planId, { plan_date: planDate, rows });
    } else {
      await api.plans.createFromList({ plan_date: planDate, rows });
    }
    closeNewPlanForm();
    loadPlans();
  } catch (e) {
    alert(e?.detail || e?.message || '저장 실패');
  }
}

function showPlanEditModal(planId) {
  showPlanForm(planId);
}

function closePlanModal() {
  document.getElementById('planModal').style.display = 'none';
}

document.getElementById('planForm')?.addEventListener('submit', (e) => {
  e.preventDefault();
});

async function deletePlan(planId) {
  if (!confirm('이 플랜을 삭제하시겠습니까? 루트, 정차지 등 관련 데이터가 모두 삭제됩니다.')) return;
  try {
    await api.plans.delete(planId);
    loadPlans();
    const detail = document.getElementById('planDetail');
    if (detail && detail.style.display !== 'none' && parseInt(detail.dataset.planId) === parseInt(planId)) {
      detail.style.display = 'none';
      detail.innerHTML = '';
    }
  } catch (e) {
    alert(e?.detail || e?.message || '삭제 실패');
  }
}

async function openPlan(planId) {
  const [detail, users] = await Promise.all([
    api.plans.getPlanDetail(planId),
    api.users.list(),
  ]);
  const { plan, routes, previous_day_drivers } = detail;
  const drivers = users.filter(u => u.role === 'DRIVER');
  const html = `
    <h2>${plan.route || '-'} - ${plan.name}</h2>
    ${routes.map(r => {
      const currentDriver = r.assignments?.[0];
      const prevDriver = previous_day_drivers?.[r.name];
      const defaultId = (currentDriver?.driver_id) || (prevDriver?.driver_id) || '';
      return `
      <div class="card">
        <h3>${r.name}</h3>
        <p>기사 배정: <select onchange="assignDriver(${r.id}, this.value, ${planId})">
          <option value="">-</option>
          ${drivers.map(u => `<option value="${u.id}" ${defaultId === u.id ? 'selected' : ''}>${u.display_name || u.username}</option>`).join('')}
        </select></p>
        <p><a href="#" onclick="event.preventDefault();openRoute(${r.id}, ${planId})">스탑 목록</a></p>
      </div>
    `}).join('')}
    <p><button onclick="document.getElementById('planDetail').style.display='none'; loadPlans();">닫기</button></p>
  `;
  document.getElementById('planDetail').innerHTML = html;
  document.getElementById('planDetail').dataset.planId = planId;
  document.getElementById('planDetail').style.display = 'block';
}

function addRoute(planId) {
  const name = prompt('루트 이름');
  if (!name) return;
  api.routes.create(planId, { name, sequence: 0 }).then(() => openPlan(planId));
}

async function assignDriver(routeId, driverId, planId) {
  try {
    const id = (driverId && driverId !== '') ? parseInt(driverId) : null;
    await api.routes.setAssign(routeId, id);
    if (planId) openPlan(planId);
  } catch (e) {
    alert(e?.detail || e?.message || '배정 실패');
  }
}

function formatOrderItem(oi) {
  if (!oi) return '';
  const q = parseFloat(oi.quantity);
  const u = oi.item?.unit || '박스';
  const qStr = (Number.isInteger(q) || q === Math.floor(q)) ? String(Math.floor(q)) : String(Math.round(q * 100) / 100);
  return `${oi.item?.product || ''} ${qStr}${u}`;
}

async function openRoute(routeId, planId) {
  const [stops, companyLoc, settings] = await Promise.all([
    api.stops.listByRoute(routeId),
    api.settings.getCompanyLocation().catch(() => ({ latitude: null, longitude: null })),
    api.settings.get().catch(() => ({ company_address: '' })),
  ]);
  const companyAddr = settings?.company_address || '(회사 주소 미설정)';
  const pointsWithCoords = stops
    .map((s, i) => ({ ...s, displayOrder: i + 1, lat: s.customer?.latitude, lng: s.customer?.longitude }))
    .filter(s => s.lat != null && s.lng != null);
  const hasMap = pointsWithCoords.length > 0 || (companyLoc?.latitude && companyLoc?.longitude);
  const mapHtml = hasMap
    ? `<div id="routeMap" class="route-map" style="height:280px; width:100%; margin-bottom:1rem;"></div>`
    : `<p class="route-map-placeholder">배송지 좌표가 있는 곳만 경로에 표시됩니다.</p>`;
  window._routeCompanyLoc = companyLoc;
  window._routeStopsData = { stops, routeId, planId };
  const html = `
    <h3>스탑 목록</h3>
    <p>${mapHtml}</p>
    <table class="stops-draggable-table"><thead><tr><th>순서</th><th>거래처</th><th>품목</th><th>영수증 보기</th><th>배송상태</th></tr></thead>
    <tbody>
    <tr class="stop-row-origin"><td>출발</td><td>출발지 (회사)<br><small>${companyAddr}</small></td><td>-</td><td>-</td><td>-</td></tr>
    ${stops.map((s, i) => {
      const order = i + 1;
      const customerName = s.customer?.name || s.customer_id || '-';
      const itemsStr = (s.order_items || []).map(oi => formatOrderItem(oi)).filter(Boolean).join(', ') || '-';
      const photos = (s.completions || [])[0]?.photos || [];
      const receiptUrl = `/receipt.html?stop_id=${s.id}`;
      const receiptLinks = [
        `<a href="${receiptUrl}" target="_blank">거래명세표</a>`,
        ...photos.map(p => `<a href="/api/uploads/photo/${p.id}" target="_blank">사진</a>`)
      ].join(' ');
      const statusText = s.is_completed ? '배송완료' : '배송전';
      return `
      <tr class="stop-row-draggable" draggable="true" data-stop-id="${s.id}">
        <td>${order}</td>
        <td>${customerName}</td>
        <td>${itemsStr}</td>
        <td>${receiptLinks}</td>
        <td>${statusText}</td>
      </tr>
    `}).join('')}
    </tbody></table>
    <p><small style="color:var(--muted)">드래그하여 순서 변경</small></p>
    <p><button onclick="openPlan(${planId})">뒤로</button></p>
  `;
  document.getElementById('planDetail').innerHTML = html;
  bindStopRowDragDrop(routeId, planId);
  if (hasMap && typeof L !== 'undefined') {
    setTimeout(() => initRouteMap(pointsWithCoords, window._routeCompanyLoc), 50);
  }
}

function initRouteMap(stops, companyLoc) {
  const mapEl = document.getElementById('routeMap');
  if (!mapEl) return;
  if (window._routeMap) {
    window._routeMap.remove();
    window._routeMap = null;
  }
  const pts = stops.map(s => [parseFloat(s.lat), parseFloat(s.lng)]);
  const origin = (companyLoc?.latitude != null && companyLoc?.longitude != null)
    ? [parseFloat(companyLoc.latitude), parseFloat(companyLoc.longitude)] : null;
  const allPts = origin ? [origin, ...pts] : pts;
  const center = allPts.length ? allPts[Math.floor(allPts.length / 2)] : [37.5665, 126.978];
  const map = L.map('routeMap').setView(center, 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);
  if (origin) {
    L.marker(origin, {
      icon: L.divIcon({
        className: 'route-marker-origin',
        html: '<span style="background:#e74c3c;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold;">출발</span>',
        iconSize: [36, 20],
        iconAnchor: [18, 10],
      }),
    }).addTo(map).bindPopup('<b>출발지</b> (회사)');
  }
  pts.forEach((p, i) => {
    const s = stops[i];
    const ord = s.displayOrder || (i + 1);
    const itemsStr = (s.order_items || []).map(oi => formatOrderItem(oi)).filter(Boolean).join(', ') || '-';
    const popupHtml = `<b>${ord}. ${s.customer?.name || ''}</b><br>${itemsStr ? `배달 품목: ${itemsStr}` : '배달 품목 없음'}`;
    L.marker(p, {
      icon: L.divIcon({
        className: 'route-marker-number',
        html: `<span class="route-marker-num-badge">${ord}</span>`,
        iconSize: [28, 28],
        iconAnchor: [14, 28],
      }),
    }).addTo(map).bindPopup(popupHtml);
  });
  if (allPts.length > 1) {
    L.polyline(allPts, { color: '#4a90d9', weight: 3 }).addTo(map);
    map.fitBounds(allPts);
  }
  window._routeMap = map;
}

function bindStopRowDragDrop(routeId, planId) {
  const tbody = document.querySelector('.stops-draggable-table tbody');
  if (!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('.stop-row-draggable'));
  let draggedEl = null;
  rows.forEach(tr => {
    tr.addEventListener('dragstart', (e) => {
      draggedEl = tr;
      tr.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', tr.dataset.stopId);
      e.dataTransfer.setData('text/html', tr.outerHTML);
    });
    tr.addEventListener('dragend', () => {
      tr.classList.remove('dragging');
      rows.forEach(r => r.classList.remove('drag-over'));
      draggedEl = null;
    });
    tr.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      if (tr !== draggedEl) tr.classList.add('drag-over');
    });
    tr.addEventListener('dragleave', () => tr.classList.remove('drag-over'));
    tr.addEventListener('drop', async (e) => {
      e.preventDefault();
      tr.classList.remove('drag-over');
      if (!draggedEl || draggedEl === tr) return;
      const targetIdx = rows.indexOf(tr);
      const sourceIdx = rows.indexOf(draggedEl);
      if (targetIdx < 0 || sourceIdx < 0) return;
      const stopIds = rows.map(r => parseInt(r.dataset.stopId));
      const [moved] = stopIds.splice(sourceIdx, 1);
      stopIds.splice(targetIdx, 0, moved);
      try {
        await api.stops.reorder(routeId, stopIds);
        openRoute(routeId, planId);
      } catch (err) {
        alert(err?.detail || err?.message || '순서 변경 실패');
      }
    });
  });
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
let contractContentItemsData = [];
let contractContentItemsList = [];

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

let arrearsSortCol = 'arrears';
let arrearsSortAsc = false;

let _partialRepayCustomerId = null;
let _partialRepayCurrentArrears = 0;

async function loadArrears() {
  const list = await api.customers.list();
  const filtered = list.filter(c => {
    const amt = c.arrears != null && c.arrears !== '' ? Number(c.arrears) : 0;
    return amt > 0;
  });
  const sorted = [...filtered].sort((a, b) => {
    const av = a[arrearsSortCol];
    const bv = b[arrearsSortCol];
    const cmp = arrearsSortCol === 'arrears' || arrearsSortCol === 'code'
      ? (arrearsSortCol === 'arrears' ? (Number(av) || 0) - (Number(bv) || 0) : (av || '').toString().localeCompare((bv || '').toString(), 'ko'))
      : (av || '').toString().localeCompare((bv || '').toString(), 'ko');
    return arrearsSortAsc ? cmp : -cmp;
  });
  document.getElementById('arrearsList').innerHTML = sorted.map(c => {
    const amt = (c.arrears != null && c.arrears !== '' ? Number(c.arrears) : 0);
    return `
    <tr>
      <td>${c.code || '-'}</td>
      <td>${c.name || '-'}</td>
      <td>${amt.toLocaleString('ko-KR')}원</td>
      <td>
        <button class="btn btn-secondary" onclick="fullRepayment(${c.id})" ${amt <= 0 ? 'disabled' : ''}>전액변제</button>
        <button class="btn btn-secondary" onclick="showPartialRepayModal(${c.id}, ${amt}, ${JSON.stringify(c.name || '')})" ${amt <= 0 ? 'disabled' : ''}>부분변제</button>
      </td>
    </tr>
  `}).join('');
  updateArrearsSortIcons();
  bindArrearsSortHandlers();
}

async function fullRepayment(customerId) {
  if (!confirm('미수금액을 0원으로 초기화하시겠습니까?')) return;
  try {
    await api.customers.update(customerId, { arrears: 0 });
    loadArrears();
  } catch (e) {
    alert(e?.detail || '변제 처리 실패');
  }
}

function showPartialRepayModal(customerId, currentArrears, customerName) {
  _partialRepayCustomerId = customerId;
  _partialRepayCurrentArrears = Number(currentArrears) || 0;
  document.getElementById('partialRepayCustomerName').textContent = `${customerName} (현재 미수금: ${_partialRepayCurrentArrears.toLocaleString('ko-KR')}원)`;
  document.getElementById('partialRepayAmount').value = '';
  document.getElementById('partialRepayCurrentArrears').textContent = `변제 후 잔액: 최대 ${_partialRepayCurrentArrears.toLocaleString('ko-KR')}원까지 변제 가능`;
  document.getElementById('partialRepayModal').style.display = 'flex';
}

function closePartialRepayModal() {
  document.getElementById('partialRepayModal').style.display = 'none';
  _partialRepayCustomerId = null;
}

async function submitPartialRepay() {
  const inp = document.getElementById('partialRepayAmount');
  const raw = inp?.value?.trim();
  const amount = raw ? parseInt(raw, 10) : 0;
  if (!amount || amount <= 0) {
    alert('변제 금액을 입력하세요.');
    return;
  }
  if (amount > _partialRepayCurrentArrears) {
    alert(`변제 금액은 미수금액(${_partialRepayCurrentArrears.toLocaleString('ko-KR')}원)을 초과할 수 없습니다.`);
    return;
  }
  const newArrears = _partialRepayCurrentArrears - amount;
  try {
    await api.customers.update(_partialRepayCustomerId, { arrears: newArrears });
    closePartialRepayModal();
    loadArrears();
  } catch (e) {
    alert(e?.detail || '변제 처리 실패');
  }
}

function updateArrearsSortIcons() {
  document.querySelectorAll('#tab-arrears th.sortable').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.dataset.sort === arrearsSortCol) {
      th.classList.add(arrearsSortAsc ? 'sort-asc' : 'sort-desc');
    }
  });
}

function bindArrearsSortHandlers() {
  document.querySelectorAll('#tab-arrears th.sortable').forEach(th => {
    th.onclick = () => {
      arrearsSortCol = th.dataset.sort;
      arrearsSortAsc = !arrearsSortAsc;
      loadArrears();
    };
  });
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
  const numCols = ['latitude', 'longitude', 'arrears'];
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
      <td>${c.business_registration_number || '-'}</td>
      <td>${c.representative_name || '-'}</td>
      <td>${c.contract || '-'}</td>
      <td>${c.business_type || '-'}</td>
      <td>${c.business_category || '-'}</td>
      <td>${(c.arrears != null && c.arrears !== '' ? Number(c.arrears) : 0).toLocaleString('ko-KR')}원</td>
      <td>${c.contract_content || '-'}</td>
      <td>${(() => {
        const addr = c.address || '-';
        if (!c.address || !c.address.trim()) return addr;
        const hasCoords = c.latitude != null && c.longitude != null;
        const icon = hasCoords ? '<span class="addr-status ok">✓</span>' : '<span class="addr-status fail">✗</span>';
        return addr + ' ' + icon;
      })()}</td>
      <td>
        <button class="btn btn-secondary" onclick="showCustomerEditForm(${c.id})">수정</button>
        <button class="btn btn-secondary" onclick="deleteCustomer(${c.id})">삭제</button>
      </td>
    </tr>
  `).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[name="contractInputMode"]').forEach(r => {
    r.onchange = () => {
      const checked = document.querySelector('input[name="contractInputMode"]:checked');
      if (!checked) return;
      const isSelect = checked.value === 'select';
      const sel = document.getElementById('contractContentSelectMode');
      const txt = document.getElementById('contractContentTextMode');
      if (sel) sel.style.display = isSelect ? 'block' : 'none';
      if (txt) txt.style.display = isSelect ? 'none' : 'block';
    };
  });
});

async function loadItemsForContract() {
  if (contractContentItemsList.length) return;
  contractContentItemsList = await api.items.list();
}

function renderContractContentItems() {
  const div = document.getElementById('contractContentItems');
  div.innerHTML = contractContentItemsData.map((row, idx) => `
    <div class="contract-item-row" data-idx="${idx}">
      <select class="contract-item-select">
        <option value="">품목 선택</option>
        ${contractContentItemsList.map(i => `
          <option value="${i.id}" data-product="${(i.product || '').replace(/"/g, '&quot;')}" data-unit="${i.unit || '박스'}" ${row.item_id === i.id ? 'selected' : ''}>${i.code || ''} ${i.product}</option>
        `).join('')}
      </select>
      <input type="number" class="contract-item-qty" value="${row.quantity}" min="0.5" step="0.5" placeholder="수량" style="width:60px">
      <span class="contract-item-unit">${row.unit || '박스'}</span>
      <button type="button" class="btn btn-secondary" onclick="removeContractItemRow(${idx})">삭제</button>
    </div>
  `).join('');
  div.querySelectorAll('.contract-item-select').forEach((sel, i) => {
    sel.onchange = () => {
      const opt = sel.options[sel.selectedIndex];
      const itemId = opt.value ? parseInt(opt.value) : null;
      if (itemId && contractContentItemsData.filter((r, j) => j !== i && r.item_id === itemId).length) {
        alert('이미 추가된 품목입니다. 중복되지 않게 선택하세요.');
        return;
      }
      contractContentItemsData[i].item_id = itemId;
      contractContentItemsData[i].product = opt.dataset.product || '';
      contractContentItemsData[i].unit = opt.dataset.unit || '박스';
      const unitSpan = sel.closest('.contract-item-row').querySelector('.contract-item-unit');
      if (unitSpan) unitSpan.textContent = contractContentItemsData[i].unit;
    };
  });
  div.querySelectorAll('.contract-item-qty').forEach((inp, i) => {
    inp.onchange = () => { contractContentItemsData[i].quantity = parseFloat(inp.value) || 1; };
  });
}

function addContractItemRow() {
  contractContentItemsData.push({ item_id: null, product: '', quantity: 1, unit: '박스' });
  renderContractContentItems();
}

function removeContractItemRow(idx) {
  contractContentItemsData.splice(idx, 1);
  renderContractContentItems();
}

function getContractContentFromSelect() {
  return contractContentItemsData
    .filter(r => r.item_id && r.product)
    .map(r => `${r.product} ${r.quantity === Math.floor(r.quantity) ? r.quantity : r.quantity}${r.unit}`)
    .join(', ');
}

async function matchContractContent() {
  const text = document.getElementById('customerContractContentText').value.trim();
  if (!text) { document.getElementById('contractMatchResult').textContent = '텍스트를 입력하세요.'; return; }
  try {
    const r = await fetch('/api/customers/match-contract-content', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const data = await r.json().catch(() => ({}));
    if (data.display_string) {
      document.getElementById('customerContractContentText').value = data.display_string;
      document.getElementById('contractMatchResult').textContent = '맵핑 완료: ' + data.display_string;
      document.getElementById('contractMatchResult').className = 'contract-match-result ok';
    } else {
      document.getElementById('contractMatchResult').textContent = '맵핑된 품목이 없습니다.';
      document.getElementById('contractMatchResult').className = 'contract-match-result err';
    }
  } catch (e) {
    document.getElementById('contractMatchResult').textContent = '맵핑 실패';
    document.getElementById('contractMatchResult').className = 'contract-match-result err';
  }
}

function normalizeRouteForSelect(route) {
  if (!route || !route.trim()) return '';
  const m = route.trim().match(/^(\d+)/);
  return m ? m[1] + '호차' : '';
}

async function populateCustomerRouteSelect() {
  const sel = document.getElementById('customerRoute');
  if (!sel) return;
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
}

function showCustomerForm() {
  const modal = document.getElementById('customerModal');
  if (!modal) return;
  loadItemsForContract().then(() => renderContractContentItems());
  populateCustomerRouteSelect();
  document.getElementById('customerModalTitle').textContent = '거래처 추가';
  document.getElementById('customerId').value = '';
  document.getElementById('customerName').value = '';
  document.getElementById('customerBusinessRegNum').value = '';
  document.getElementById('customerRepresentative').value = '';
  document.getElementById('customerPhone').value = '';
  document.getElementById('customerBusinessType').value = '';
  document.getElementById('customerBusinessCategory').value = '';
  document.getElementById('customerArrears').value = '0';
  document.getElementById('customerAddress').value = '';
  document.getElementById('customerLatitude').value = '';
  document.getElementById('customerLongitude').value = '';
  document.getElementById('customerCode').value = '';
  document.getElementById('customerRoute').value = '';
  document.getElementById('customerContract').value = '';
  document.getElementById('customerContractContentText').value = '';
  document.querySelector('input[name="contractInputMode"][value="select"]').checked = true;
  document.getElementById('contractContentSelectMode').style.display = 'block';
  document.getElementById('contractContentTextMode').style.display = 'none';
  document.getElementById('contractContentItems').innerHTML = '';
  document.getElementById('contractMatchResult').textContent = '';
  contractContentItemsData = [];
  document.getElementById('customerCode').readOnly = false;
  document.getElementById('customerName').readOnly = false;
  modal.style.display = 'flex';
}

function showCustomerEditForm(id) {
  api.customers.list().then(async list => {
    const c = list.find(x => x.id === id);
    if (!c) return;
    await populateCustomerRouteSelect();
    document.getElementById('customerModalTitle').textContent = '거래처 수정';
    document.getElementById('customerId').value = c.id;
    document.getElementById('customerName').value = c.name;
    document.getElementById('customerBusinessRegNum').value = c.business_registration_number || '';
    document.getElementById('customerRepresentative').value = c.representative_name || '';
    document.getElementById('customerPhone').value = c.phone || '';
    document.getElementById('customerBusinessType').value = c.business_type || '';
    document.getElementById('customerBusinessCategory').value = c.business_category || '';
    document.getElementById('customerArrears').value = c.arrears != null && c.arrears !== '' ? c.arrears : '0';
    document.getElementById('customerAddress').value = c.address || '';
    document.getElementById('customerLatitude').value = c.latitude != null ? c.latitude : '';
    document.getElementById('customerLongitude').value = c.longitude != null ? c.longitude : '';
    document.getElementById('customerCode').value = c.code || '';
    const routeVal = normalizeRouteForSelect(c.route);
    document.getElementById('customerRoute').value = routeVal || '';

    document.getElementById('customerContract').value = c.contract || '';
    document.getElementById('customerContractContentText').value = c.contract_content || '';
    document.querySelector('input[name="contractInputMode"][value="select"]').checked = true;
    document.getElementById('contractContentSelectMode').style.display = 'block';
    document.getElementById('contractContentTextMode').style.display = 'none';
    contractContentItemsData = [];
    if (c.contract_content) {
      try {
        const r = await fetch('/api/customers/match-contract-content', {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: c.contract_content }),
        });
        const data = await r.json().catch(() => ({}));
        if (data.matches && data.matches.length) {
          contractContentItemsData = data.matches.map(m => ({ item_id: m.item_id, product: m.product, quantity: m.quantity, unit: m.unit }));
        }
      } catch (_) {}
    }
    renderContractContentItems();
  document.getElementById('contractMatchResult').textContent = '';
  loadItemsForContract().then(() => renderContractContentItems());
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
  const business_registration_number = document.getElementById('customerBusinessRegNum').value.trim() || null;
  const representative_name = document.getElementById('customerRepresentative').value.trim() || null;
  const phone = document.getElementById('customerPhone').value.trim() || null;
  const address = document.getElementById('customerAddress').value.trim() || null;
  const code = document.getElementById('customerCode').value.trim() || null;
  const route = document.getElementById('customerRoute').value.trim() || null;
  const contract = document.getElementById('customerContract').value || null;
  const business_type = document.getElementById('customerBusinessType').value.trim() || null;
  const business_category = document.getElementById('customerBusinessCategory').value.trim() || null;
  const arrearsRaw = document.getElementById('customerArrears').value.trim();
  const arrears = arrearsRaw ? parseInt(arrearsRaw, 10) : 0;
  const isSelectMode = document.querySelector('input[name="contractInputMode"]:checked').value === 'select';
  const contract_content = isSelectMode ? getContractContentFromSelect() : document.getElementById('customerContractContentText').value.trim() || null;
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
    const payload = { phone, address, route, contract: contractVal, contract_content, latitude, longitude, business_registration_number, representative_name, business_type, business_category, arrears };
    if (id) {
      await api.customers.update(parseInt(id), payload);
    } else {
      await api.customers.create({ name, code, memo: null, ...payload });
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
      <td>${i.unit || '-'}</td>
      <td>${i.unit_price != null ? Math.round(Number(i.unit_price)).toLocaleString('ko-KR') + '원' : '-'}</td>
      <td>${i.description || '-'}</td>
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
  document.getElementById('itemUnit').value = '박스';
  document.getElementById('itemUnitPrice').value = '';
  document.getElementById('itemDescription').value = '';
  document.getElementById('itemModal').style.display = 'flex';
}

function showItemEditForm(id) {
  api.items.list().then(list => {
    const i = list.find(x => x.id === id);
    if (!i) return;
    document.getElementById('itemModalTitle').textContent = '품목 수정';
    document.getElementById('itemId').value = i.id;
    document.getElementById('itemProduct').value = i.product || '';
    const unitVal = ['박스', '판', '관'].includes(i.unit) ? i.unit : '박스';
    document.getElementById('itemUnit').value = unitVal;
    document.getElementById('itemUnitPrice').value = i.unit_price != null ? Math.round(Number(i.unit_price)) : '';
    document.getElementById('itemDescription').value = i.description || '';
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
  const unit = document.getElementById('itemUnit').value || '박스';
  const priceVal = document.getElementById('itemUnitPrice').value.trim();
  const description = document.getElementById('itemDescription').value.trim() || null;
  if (!product) { alert('상품명을 입력하세요'); return; }
  const unit_price = priceVal ? Math.round(parseFloat(priceVal)) : null;
  if (priceVal && isNaN(unit_price)) { alert('단가는 숫자로 입력하세요'); return; }
  try {
    if (id) {
      await api.items.update(parseInt(id), { product, unit, unit_price, description });
    } else {
      await api.items.create({ product, unit, unit_price, description });
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

let addressCheckTimeout = null;

async function loadSettings() {
  try {
    const s = await api.settings.get();
    document.getElementById('settingCompanyName').value = s.company_name || '';
    document.getElementById('settingBusinessRegNum').value = s.business_registration_number || '';
    document.getElementById('settingRepresentativeName').value = s.representative_name || '';
    document.getElementById('settingCompanyAddress').value = s.company_address || '';
    document.getElementById('settingCompanyPhone').value = s.company_phone || '';
    document.getElementById('settingBusinessType').value = s.business_type || '';
    document.getElementById('settingBusinessCategory').value = s.business_category || '';
    document.getElementById('settingBankName').value = s.bank_name || '';
    document.getElementById('settingBankAccount').value = s.bank_account || '';
    document.getElementById('settingBankHolder').value = s.bank_holder || '';
    document.getElementById('settingDeliveryRouteCount').value = s.delivery_route_count ?? 5;
    if (s.company_address) {
      setTimeout(() => checkAddressGeocode(), 100);
    } else {
      const el = document.getElementById('settingAddressStatus');
      if (el) { el.textContent = ''; el.className = 'address-status'; }
    }
  } catch (e) {
    document.getElementById('settingDeliveryRouteCount').value = 5;
  }
}

async function checkAddressGeocode() {
  const addr = document.getElementById('settingCompanyAddress')?.value?.trim() || '';
  const el = document.getElementById('settingAddressStatus');
  if (!el) return;
  if (!addr) {
    el.textContent = '';
    el.className = 'address-status';
    return;
  }
  el.textContent = '…';
  el.className = 'address-status';
  try {
    const r = await api.settings.geocodeAddress(addr);
    el.textContent = r.found ? '✓' : '✗';
    el.className = 'address-status ' + (r.found ? 'ok' : 'fail');
  } catch (e) {
    el.textContent = '✗';
    el.className = 'address-status fail';
  }
}

function updateAddressStatus(addr) {
  const el = document.getElementById('settingAddressStatus');
  if (!el) return;
  if (!addr) { el.textContent = ''; el.className = 'address-status'; return; }
  checkAddressGeocode();
}

function bindAddressCheck() {
  const inp = document.getElementById('settingCompanyAddress');
  if (!inp) return;
  inp.addEventListener('input', () => {
    if (addressCheckTimeout) clearTimeout(addressCheckTimeout);
    addressCheckTimeout = setTimeout(() => {
      updateAddressStatus(inp.value?.trim());
    }, 600);
  });
  inp.addEventListener('blur', () => {
    if (inp.value?.trim()) updateAddressStatus(inp.value.trim());
  });
}

bindAddressCheck();

const settingsFormEl = document.getElementById('settingsForm');
if (settingsFormEl) settingsFormEl.onsubmit = async (e) => {
  e.preventDefault();
  const company_name = document.getElementById('settingCompanyName').value.trim() || null;
  const business_registration_number = document.getElementById('settingBusinessRegNum').value.trim() || null;
  const representative_name = document.getElementById('settingRepresentativeName').value.trim() || null;
  const company_address = document.getElementById('settingCompanyAddress').value.trim() || null;
  const company_phone = document.getElementById('settingCompanyPhone').value.trim() || null;
  const business_type = document.getElementById('settingBusinessType').value.trim() || null;
  const business_category = document.getElementById('settingBusinessCategory').value.trim() || null;
  const bank_name = document.getElementById('settingBankName').value.trim() || null;
  const bank_account = document.getElementById('settingBankAccount').value.trim() || null;
  const bank_holder = document.getElementById('settingBankHolder').value.trim() || null;
  const val = parseInt(document.getElementById('settingDeliveryRouteCount').value, 10);
  if (isNaN(val) || val < 1 || val > 99) {
    alert('배달 루트 개수는 1~99 사이로 입력하세요');
    return;
  }
  try {
    await api.settings.update({
      company_name,
      business_registration_number,
      representative_name,
      company_address,
      company_phone,
      business_type,
      business_category,
      bank_name,
      bank_account,
      bank_holder,
      delivery_route_count: val,
    });
    alert('저장되었습니다');
  } catch (e) {
    alert(e?.detail || e?.message || '저장 실패');
  }
};

loadPlans();
