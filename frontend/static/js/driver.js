(async () => {
  const user = await api.me();
  if (!user || user.role !== 'DRIVER') {
    location.href = '/';
    return;
  }
})();

async function doLogout() {
  await api.logout();
  location.href = '/';
}

async function loadPlans() {
  const from = new Date(); from.setDate(1);
  const to = new Date(); to.setMonth(to.getMonth() + 1);
  const plans = await api.plans.list(from.toISOString().slice(0,10), to.toISOString().slice(0,10));
  document.getElementById('plansList').innerHTML = plans.map(p => `
    <div class="card">
      <h3>${p.plan_date} - ${p.name}</h3>
      <p><button class="btn btn-primary" onclick="loadRoutes(${p.id}, '${p.plan_date} ${p.name}')">루트 보기</button></p>
    </div>
  `).join('') || '<p>배정된 플랜이 없습니다.</p>';
}

async function loadRoutes(planId, title) {
  const routes = await api.routes.listByPlan(planId);
  if (!routes.length) {
    alert('배정된 루트가 없습니다.');
    return;
  }
  if (routes.length === 1) {
    await showRoute(routes[0], planId, title);
    return;
  }
  document.getElementById('plansList').innerHTML = routes.map(r => `
    <div class="card">
      <h3>${r.name}</h3>
      <p><button class="btn btn-primary" onclick="showRouteById(${r.id}, ${planId})">선택</button></p>
    </div>
  `).join('');
  window._planTitle = title;
}

async function showRouteById(routeId, planId) {
  const routes = await api.routes.listByPlan(planId);
  const route = routes.find(r => r.id === routeId);
  if (route) await showRoute(route, planId, window._planTitle || '');
}

async function showRoute(route, planId, title) {
  document.getElementById('routeTitle').textContent = title + ' - ' + route.name;
  await loadStops(route.id, planId);
  document.getElementById('plansSection').style.display = 'none';
  document.getElementById('routeSection').style.display = 'block';
}

async function loadStops(routeId, planId) {
  window._currentRouteId = routeId;
  window._currentPlanId = planId;
  const stops = await api.stops.listByRoute(routeId);
  document.getElementById('stopsList').innerHTML = stops.map(s => `
    <div class="card" id="stop-${s.id}">
      <h3>#${s.sequence} ${s.customer?.name || '거래처'}</h3>
      <p>${(s.order_items || []).map(oi => `${oi.item?.product || ''} x${oi.quantity}`).join(', ') || '-'}</p>
      <p>${s.is_completed ? '<span style="color:green">완료됨</span>' : `
        <button class="btn btn-primary" onclick="completeStop(${s.id})">완료 처리</button>
      `}</p>
    </div>
  `).join('');
}

async function completeStop(stopId) {
  const memo = prompt('메모 (선택)');
  try {
    await api.completions.complete(stopId, memo || null);
    const inp = document.createElement('input');
    inp.type = 'file';
    inp.multiple = true;
    inp.accept = 'image/*';
    inp.onchange = async () => {
      if (inp.files.length) {
        await api.completions.uploadPhotos(stopId, inp.files);
      }
      loadStops(window._currentRouteId, window._currentPlanId);
    };
    inp.click();
  } catch (e) {
    alert(e.detail || '완료 처리 실패');
  }
}

function backToPlans() {
  document.getElementById('routeSection').style.display = 'none';
  document.getElementById('plansSection').style.display = 'block';
  loadPlans();
}

loadPlans();
