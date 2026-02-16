let currentUser = null;

(async () => {
  const user = await api.me();
  currentUser = user;
  if (!user || user.role !== 'DRIVER') {
    location.href = '/';
    return;
  }
  if (user.must_change_password) {
    location.href = '/change-password.html';
    return;
  }
  if (user.status === '승인요청중') {
    document.getElementById('pendingApprovalSection').style.display = 'block';
    document.getElementById('driverMain').style.display = 'none';
    return;
  }
  if (user.status === '퇴사') {
    document.getElementById('pendingApprovalSection').style.display = 'block';
    document.getElementById('pendingApprovalSection').querySelector('h2').textContent = '퇴사 처리된 계정';
    document.getElementById('pendingApprovalSection').querySelector('p').textContent = '퇴사 처리된 계정은 이용할 수 없습니다.';
    document.getElementById('driverMain').style.display = 'none';
    return;
  }
  bindDriverTabs();
  loadPlans();
})();

function bindDriverTabs() {
  document.querySelectorAll('#driverMain .nav-tabs a').forEach(a => {
    a.onclick = (e) => {
      e.preventDefault();
      document.querySelectorAll('#driverMain .nav-tabs a').forEach(x => x.classList.remove('active'));
      document.querySelectorAll('#driverMain .tab-content').forEach(x => { x.style.display = 'none'; });
      a.classList.add('active');
      const tab = a.dataset.tab;
      const el = document.getElementById('tab-' + tab);
      if (el) el.style.display = 'block';
      if (tab === 'plans') loadPlans();
      if (tab === 'myinfo') loadMyInfo();
    };
  });
}

function loadMyInfo() {
  if (!currentUser) return;
  const u = currentUser;
  const localeMap = { '대한민국': '🇰🇷 한국어', '미국': '🇺🇸 English', '일본': '🇯🇵 日本語', '简体中文': '🇨🇳 简体中文', '繁體中文': '🇨🇳 繁體中文', '중국': '🇨🇳 简体中文', '베트남': '🇻🇳 Tiếng Việt', '라오스': '🇱🇦 ພາສາລາວ', '캄보디아': '🇰🇭 ភាសាខ្មែរ', '인도': '🇮🇳 हिन्दी', '파키스탄': '🇵🇰 اردو' };
  const localeDisplay = localeMap[u.preferred_locale] || u.preferred_locale || '-';
  const formatPhone = (p) => {
    if (!p || !String(p).trim()) return '-';
    const d = String(p).replace(/\D/g, '');
    if (d.length === 11 && d.startsWith('010')) return d.replace(/(\d{3})(\d{4})(\d{4})/, '$1-$2-$3');
    return p;
  };
  document.getElementById('myInfoContent').innerHTML = `
    <p><strong>아이디</strong> ${u.username || '-'}</p>
    <p><strong>이름</strong> ${u.display_name || '-'}</p>
    <p><strong>전화번호</strong> ${formatPhone(u.phone) || '-'}</p>
    <p><strong>부서(루트)</strong> ${u.department || '-'}</p>
    <p><strong>선호언어</strong> ${localeDisplay}</p>
    <p><strong>상태</strong> ${u.status || '-'}</p>
  `;
}

async function doLogout() {
  await api.logout();
  location.href = '/';
}

function getLocalDateString() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function getNextStop(stops) {
  const list = (stops || []).filter(s => !s.is_completed).sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
  return list[0] || null;
}

function itemsStr(s) {
  const arr = (s.order_items || []).map(oi => `${oi.item?.product || ''} x${oi.quantity}`).filter(Boolean);
  return arr.length ? arr.join(', ') : '-';
}

function escapeHtml(str) {
  return String(str || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function toggleStopCard(stopId) {
  const el = document.getElementById('stop-' + stopId);
  if (el) el.classList.toggle('expanded');
}

async function loadPlans() {
  const today = getLocalDateString();
  const plans = await api.plans.list(today, today);
  document.getElementById('plansList').innerHTML = plans.map(p => `
    <div class="card">
      <h3>${p.plan_date} - ${p.name}</h3>
      <p><button class="btn btn-primary" onclick="loadRoutes(${p.id}, '${(p.plan_date + ' ' + p.name).replace(/'/g, "\\'")}')">배송 시작</button></p>
    </div>
  `).join('') || '<p>오늘 배정된 플랜이 없습니다.</p>';
}

async function loadRoutes(planId, title) {
  const routes = await api.routes.listByPlan(planId);
  if (!routes.length) {
    alert('배정된 루트가 없습니다.');
    return;
  }
  if (routes.length === 1) {
    await startRouteAndShow(routes[0], planId, title);
    return;
  }
  document.getElementById('plansList').innerHTML = routes.map(r => `
    <div class="card">
      <h3>${r.name}</h3>
      <p><button class="btn btn-primary" onclick="startRouteAndShowById(${r.id}, ${planId})">배송 시작</button></p>
    </div>
  `).join('');
  window._planTitle = title;
}

async function startRouteAndShow(route, planId, title) {
  try {
    await api.routes.start(route.id);
  } catch (e) {
    alert(e?.detail || e?.message || '배송 시작 처리 실패');
    return;
  }
  await showRoute(route, planId, title);
}

async function startRouteAndShowById(routeId, planId) {
  const routes = await api.routes.listByPlan(planId);
  const route = routes.find(r => r.id === routeId);
  if (route) await startRouteAndShow(route, planId, window._planTitle || '');
}

async function showRoute(route, planId, title) {
  document.getElementById('routeTitle').textContent = title + ' - ' + route.name;
  await loadStops(route.id, planId);
  document.getElementById('plansSection').style.display = 'none';
  document.getElementById('routeSection').style.display = 'block';
}

function renderRouteContext(stops) {
  const next = getNextStop(stops || []);
  const ctx = document.getElementById('routeContext');
  if (!ctx) return;
  if (next) {
    const c = next.customer || {};
    ctx.innerHTML = `
      <h3 style="margin:0 0 0.5rem">다음 목적지</h3>
      <p style="margin:0.25rem 0;font-weight:600">#${next.sequence} ${escapeHtml(c.name || '거래처')}</p>
      <p style="color:var(--muted);font-size:0.9rem;margin:0.25rem 0">${escapeHtml(c.address || '-')}</p>
      <p style="margin:0.5rem 0;font-size:0.95rem">${escapeHtml(itemsStr(next))}</p>
      <p style="margin:0.5rem 0 0"><button class="btn btn-primary" onclick="completeStop(${next.id})">완료 처리</button></p>
    `;
  } else {
    ctx.innerHTML = '<p style="margin:0;color:var(--highlight)">오늘 배달 완료</p>';
  }
}

function renderStopCard(s) {
  const name = escapeHtml(s.customer?.name || '거래처');
  const statusTxt = s.is_completed ? '<span style="color:green">완료</span>' : '<span style="color:var(--muted)">배송전</span>';
  const bodyHtml = `
    <p style="margin:0.25rem 0;color:var(--muted);font-size:0.9rem">${escapeHtml((s.customer?.address || '')) || '-'}</p>
    <p style="margin:0.5rem 0">${escapeHtml(itemsStr(s))}</p>
    <p style="margin:0.5rem 0 0">
      ${s.is_completed ? '<span style="color:green">완료됨</span>' : '<button class="btn btn-primary" onclick="completeStop(' + s.id + ')">완료 처리</button>'}
    </p>
  `;
  return `
    <div class="stop-card" id="stop-${s.id}">
      <div class="stop-card-header" onclick="toggleStopCard(${s.id})">
        <span class="stop-summary">#${s.sequence} ${name}</span>
        <span>${statusTxt}</span>
        <span class="toggle-icon">▼</span>
      </div>
      <div class="stop-card-body">${bodyHtml}</div>
    </div>
  `;
}

async function loadStops(routeId, planId) {
  window._currentRouteId = routeId;
  window._currentPlanId = planId;
  const stops = await api.stops.listByRoute(routeId);
  renderRouteContext(stops);
  document.getElementById('stopsList').innerHTML = stops.map(s => renderStopCard(s)).join('');
}

async function completeStop(stopId) {
  if (!stopId || !window._currentRouteId) {
    alert('잘못된 요청입니다. 화면을 새로고침해주세요.');
    return;
  }
  try {
    await api.completions.complete(stopId, null);
    await loadStops(window._currentRouteId, window._currentPlanId);
  } catch (e) {
    const msg = e?.detail || (e?.message || '') || '완료 처리 실패';
    alert(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
}

function backToPlans() {
  document.getElementById('routeSection').style.display = 'none';
  document.getElementById('plansSection').style.display = 'block';
  loadPlans();
}
