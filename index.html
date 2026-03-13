<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Flight Monitor - Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #080e1a; color: #e2e8f0; font-family: 'Inter', sans-serif; min-height: 100vh; }
  .header { padding: 24px 28px 18px; border-bottom: 1px solid #111827; }
  .header-top { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
  .header-label { font-size: 10px; color: #475569; letter-spacing: 4px; text-transform: uppercase; margin-bottom: 4px; }
  .header h1 { font-size: 22px; font-weight: 300; color: #f1f5f9; }
  .btn { border: none; padding: 8px 16px; border-radius: 8px; font-size: 12px; cursor: pointer; font-family: inherit; }
  .btn-primary { background: #0ea5e9; color: #fff; font-weight: 600; }
  .btn-secondary { background: #1e293b; color: #94a3b8; border: 1px solid #334155; }
  .btn-ghost { background: transparent; color: #475569; border: 1px solid #1e293b; }
  .destino-tabs { display: flex; gap: 4px; margin-top: 16px; border-bottom: 1px solid #1e293b; }
  .destino-tab { background: transparent; border: 1px solid transparent; border-bottom: 2px solid transparent; color: #64748b; padding: 10px 18px; font-size: 13px; cursor: pointer; font-family: inherit; font-weight: 500; border-radius: 8px 8px 0 0; }
  .destino-tab.active { color: #0ea5e9; border-bottom-color: #0ea5e9; background: #0c1222; }
  .busqueda-tabs { display: flex; gap: 6px; margin-top: 12px; flex-wrap: wrap; }
  .tab { background: transparent; border: 1px solid #111827; color: #64748b; padding: 8px 14px; border-radius: 8px; font-size: 12px; cursor: pointer; font-family: inherit; }
  .tab.active { background: #1e293b; border-color: #334155; color: #f1f5f9; }
  .tab-price { margin-left: 8px; font-family: 'JetBrains Mono', monospace; font-size: 11px; }
  .content { padding: 24px 28px; }
  .stats-grid { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
  .stat-card { background: #0c1222; border: 1px solid #1e293b; border-radius: 12px; padding: 16px; flex: 1; min-width: 110px; }
  .stat-label { font-size: 10px; color: #475569; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }
  .stat-value { font-size: 20px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
  .stat-sub { font-size: 11px; color: #64748b; margin-top: 4px; }
  .badge { padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; display: inline-block; }
  .badge-down { background: #064e3b; color: #34d399; border: 1px solid #065f46; }
  .badge-up { background: #7f1d1d; color: #fca5a5; border: 1px solid #991b1b; }
  .badge-stable { background: #1e293b; color: #94a3b8; border: 1px solid #334155; }
  .badge-none { background: #1e293b; color: #64748b; border: 1px solid #334155; }
  .objetivo-bar { border-radius: 10px; padding: 12px 18px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
  .objetivo-dentro { background: #064e3b; border: 1px solid #065f46; }
  .objetivo-fuera { background: #1e293b; border: 1px solid #334155; }
  .card { background: #0c1222; border: 1px solid #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
  .section-label { font-size: 10px; color: #475569; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 14px; }
  .oferta-item { padding: 10px 0; border-bottom: 1px solid #111827; }
  .oferta-item:last-child { border-bottom: none; }
  .oferta-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
  .oferta-precio { font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 600; }
  .oferta-aerolinea { font-size: 12px; color: #94a3b8; }
  .oferta-duracion { font-size: 11px; color: #f59e0b; font-family: 'JetBrains Mono', monospace; }
  .oferta-tramo { font-size: 11px; color: #64748b; margin-top: 6px; padding-left: 12px; line-height: 1.8; }
  .oferta-tramo-duracion { font-size: 10px; color: #475569; font-family: 'JetBrains Mono', monospace; margin-left: 6px; }
  .escala-tag { display: inline-block; background: #1e293b; color: #f59e0b; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-family: 'JetBrains Mono', monospace; margin-left: 2px; }
  .directo-tag { display: inline-block; background: #064e3b; color: #34d399; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }
  .history-row { padding: 12px 0; border-bottom: 1px solid #111827; }
  .history-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
  .history-date { font-size: 12px; color: #94a3b8; font-family: 'JetBrains Mono', monospace; }
  .history-airline { font-size: 12px; color: #475569; margin-left: 12px; }
  .history-meta { font-size: 10px; color: #334155; margin-left: 8px; }
  .toggle-icon { color: #475569; font-size: 10px; margin-left: 8px; }
  .history-diff { font-size: 10px; margin-right: 10px; }
  .history-price { font-size: 14px; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
  .history-scroll { max-height: 500px; overflow-y: auto; }
  .ofertas-detalle { margin-top: 10px; padding: 12px; background: #0a0f1e; border-radius: 8px; border: 1px solid #1e293b; }
  .price-green { color: #34d399; }
  .price-red { color: #ef4444; }
  .price-white { color: #e2e8f0; }
  .price-muted { color: #475569; }
  .error-bar { margin-top: 12px; padding: 10px 14px; background: #7f1d1d; border: 1px solid #991b1b; border-radius: 8px; font-size: 12px; color: #fca5a5; }
  .connect-screen { display: flex; align-items: center; justify-content: center; height: 100vh; text-align: center; }
  .connect-box { max-width: 420px; padding: 40px; }
  .connect-box h1 { color: #f1f5f9; font-size: 22px; font-weight: 300; margin-bottom: 8px; }
  .connect-box p { color: #64748b; font-size: 13px; margin-bottom: 28px; }
  .connect-form { display: flex; gap: 8px; }
  .connect-input { flex: 1; background: #1e293b; color: #e2e8f0; border: 1px solid #334155; padding: 12px 16px; border-radius: 8px; font-size: 13px; outline: none; font-family: inherit; }
  .connect-input:focus { border-color: #0ea5e9; }
  .empty-state { text-align: center; padding: 60px 20px; color: #334155; }
</style>
</head>
<body>
<div id="app"></div>
<script>
let apiUrl = localStorage.getItem("fm_api_url") || "";
let data = null;
let selectedDestino = null;
let selectedBusqueda = null;
let chart = null;
let error = null;
let lastFetch = null;
let expandedRows = {};

function getDestinos() {
  if (!data) return {};
  const destinos = {};
  for (const [nombre, info] of Object.entries(data)) {
    const dest = info.destino || "Sin destino";
    if (!destinos[dest]) destinos[dest] = [];
    destinos[dest].push(nombre);
  }
  return destinos;
}

function getObjetivo() {
  if (!data || !selectedBusqueda || !data[selectedBusqueda]) return 1500;
  return data[selectedBusqueda].objetivo || 1500;
}

function render() {
  const app = document.getElementById("app");
  if (!apiUrl) { app.innerHTML = renderConnect(); setupConnectEvents(); }
  else { app.innerHTML = renderDashboard(); setupDashboardEvents(); if (data && selectedBusqueda && data[selectedBusqueda]) renderChart(); }
}

function renderConnect() {
  return `<div class="connect-screen"><div class="connect-box">
    <div style="font-size:48px;margin-bottom:20px">✈️</div>
    <h1>Flight Monitor Dashboard</h1>
    <p>Pega la URL de tu servicio en Railway para conectar</p>
    <div class="connect-form">
      <input type="text" id="urlInput" class="connect-input" placeholder="tu-servicio.up.railway.app">
      <button class="btn btn-primary" id="connectBtn">Conectar</button>
    </div>
  </div></div>`;
}

function renderOfertasDetalle(ofertas, objetivo) {
  if (!ofertas || ofertas.length === 0) return '<div style="color:#334155;font-size:11px;padding:8px">Sin detalle</div>';
  return ofertas.map(o => {
    const priceClass = o.precio <= objetivo ? 'price-green' : 'price-white';
    const tramosHtml = o.tramos.map(t => {
      let escInfo = '';
      if (t.numEscalas === 0) escInfo = '<span class="directo-tag">DIRECTO</span>';
      else escInfo = `${t.numEscalas} esc: ${t.escalas.map(e => `<span class="escala-tag">${e}</span>`).join(' ')}`;
      const durHtml = t.duracion ? `<span class="oferta-tramo-duracion">${t.duracion}</span>` : '';
      const airlinesHtml = t.aerolineasTramo && t.aerolineasTramo.length > 0 && t.aerolineasTramo[0] !== o.aerolinea
        ? `<span style="color:#334155;font-size:10px;margin-left:6px">(opera: ${t.aerolineasTramo.join(', ')})</span>` : '';
      return `<div class="oferta-tramo">${t.origen} → ${t.destino} ${escInfo} ${durHtml} ${airlinesHtml}</div>`;
    }).join('');
    const durTotal = o.duracionTotal ? `<span class="oferta-duracion">${o.duracionTotal} total</span>` : '';
    return `<div class="oferta-item">
      <div class="oferta-header">
        <div><span class="oferta-precio ${priceClass}">USD ${o.precio}</span> <span class="oferta-aerolinea">${o.aerolinea}</span></div>
        ${durTotal}
      </div>
      ${tramosHtml}
    </div>`;
  }).join('');
}

function renderDashboard() {
  const destinos = getDestinos();
  const destinoNames = Object.keys(destinos);
  if (destinoNames.length > 0 && !selectedDestino) selectedDestino = destinoNames[0];
  const busquedasEnDestino = selectedDestino ? (destinos[selectedDestino] || []) : [];
  if (busquedasEnDestino.length > 0 && (!selectedBusqueda || !busquedasEnDestino.includes(selectedBusqueda))) selectedBusqueda = busquedasEnDestino[0];

  const current = data && selectedBusqueda ? data[selectedBusqueda] : null;
  const registros = current ? current.registros || [] : [];
  const stats = current ? current.stats : null;
  const tendencia = current ? current.tendencia || "SIN DATOS" : "SIN DATOS";
  const objetivo = getObjetivo();
  const ultimo = registros.length > 0 ? registros[registros.length - 1] : null;
  const anterior = registros.length > 1 ? registros[registros.length - 2] : null;
  const diff = ultimo && anterior ? Math.round((ultimo.precio - anterior.precio) * 100) / 100 : null;
  const dentroObj = ultimo && ultimo.precio <= objetivo;

  let destinoTabsHtml = destinoNames.map(d => `<button class="destino-tab ${d === selectedDestino ? 'active' : ''}" data-destino="${d}">${d}</button>`).join('');
  let busquedaTabsHtml = busquedasEnDestino.map(name => {
    const isActive = name === selectedBusqueda;
    const r = data[name]?.registros;
    const lp = r && r.length > 0 ? r[r.length - 1].precio : null;
    return `<button class="tab ${isActive ? 'active' : ''}" data-busqueda="${name}">${name}${lp ? `<span class="tab-price" style="color:${isActive ? '#0ea5e9' : '#334155'}">$${lp}</span>` : ''}</button>`;
  }).join("");

  let errorHtml = error ? `<div class="error-bar">${error}</div>` : '';
  let contentHtml = '';

  if (!data || destinoNames.length === 0) {
    contentHtml = `<div class="empty-state"><div style="font-size:40px;margin-bottom:16px">⏳</div><div style="font-size:16px;color:#64748b;margin-bottom:8px">Esperando datos</div><div style="font-size:13px">El monitor corre cada 6 horas.</div></div>`;
  } else if (current && stats) {
    const badgeClass = tendencia === 'BAJANDO' ? 'badge-down' : tendencia === 'SUBIENDO' ? 'badge-up' : tendencia === 'ESTABLE' ? 'badge-stable' : 'badge-none';
    const badgeIcon = tendencia === 'BAJANDO' ? '↘' : tendencia === 'SUBIENDO' ? '↗' : tendencia === 'ESTABLE' ? '→' : '·';
    const diffText = diff !== null ? `${diff > 0 ? '+' : ''}${diff} vs anterior` : '';
    const precioColor = dentroObj ? 'price-green' : 'price-white';

    let ultimasOfertasHtml = '';
    if (ultimo && ultimo.ofertas && ultimo.ofertas.length > 0) {
      ultimasOfertasHtml = `<div class="card"><div class="section-label">Ofertas de la ultima busqueda (${ultimo.fecha})</div>${renderOfertasDetalle(ultimo.ofertas, objetivo)}</div>`;
    }

    const reversed = [...registros].reverse();
    let historyHtml = '<div class="history-scroll">' + reversed.map((d, i) => {
      const realIndex = registros.length - 1 - i;
      const prev = realIndex > 0 ? registros[realIndex - 1]?.precio : null;
      const dd = prev ? Math.round((d.precio - prev) * 100) / 100 : null;
      const diffClass = dd !== null ? (dd < 0 ? 'price-green' : dd > 0 ? 'price-red' : 'price-muted') : '';
      const priceClass = d.precio <= objetivo ? 'price-green' : 'price-white';
      const isExpanded = expandedRows[`${selectedBusqueda}-${realIndex}`];
      const hasOfertas = d.ofertas && d.ofertas.length > 0;
      return `<div class="history-row">
        <div class="history-header" ${hasOfertas ? `data-toggle="${selectedBusqueda}-${realIndex}"` : ''}>
          <div>
            <span class="history-date">${d.fecha}</span>
            <span class="history-airline">${d.aerolinea}</span>
            <span class="history-meta">${d.totalOfertas} ofertas / ${d.ofertasBaratas} baratas</span>
            ${hasOfertas ? `<span class="toggle-icon">${isExpanded ? '▲' : '▼'}</span>` : ''}
          </div>
          <div style="display:flex;align-items:center;gap:10px">
            ${dd !== null ? `<span class="history-diff ${diffClass}">${dd > 0 ? '+' : ''}${dd}</span>` : ''}
            <span class="history-price ${priceClass}">$${d.precio}</span>
          </div>
        </div>
        ${isExpanded && hasOfertas ? `<div class="ofertas-detalle">${renderOfertasDetalle(d.ofertas, objetivo)}</div>` : ''}
      </div>`;
    }).join('') + '</div>';

    contentHtml = `
      <div class="stats-grid">
        <div class="stat-card"><div class="stat-label">Precio actual</div><div class="stat-value ${precioColor}">${ultimo ? '$' + ultimo.precio : '-'}</div><div class="stat-sub">${diffText}</div></div>
        <div class="stat-card"><div class="stat-label">Minimo</div><div class="stat-value price-green">$${stats.minimo}</div></div>
        <div class="stat-card"><div class="stat-label">Maximo</div><div class="stat-value price-red">$${stats.maximo}</div></div>
        <div class="stat-card"><div class="stat-label">Promedio</div><div class="stat-value">$${stats.promedio}</div><div class="stat-sub">${stats.total} registros</div></div>
        <div class="stat-card" style="display:flex;flex-direction:column;align-items:center;justify-content:center">
          <div class="stat-label">Tendencia</div><span class="badge ${badgeClass}" style="margin-top:6px">${badgeIcon} ${tendencia}</span>
        </div>
      </div>
      <div class="objetivo-bar ${dentroObj ? 'objetivo-dentro' : 'objetivo-fuera'}">
        <span style="font-size:13px;color:${dentroObj ? '#34d399' : '#94a3b8'}">${dentroObj ? '✅ DENTRO DEL OBJETIVO' : ultimo ? 'Faltan USD ' + Math.round(ultimo.precio - objetivo) + ' para el objetivo' : 'Sin datos'}</span>
        <span style="font-size:12px;color:#64748b;font-family:monospace">Objetivo: USD ${objetivo}</span>
      </div>
      ${ultimasOfertasHtml}
      ${registros.length > 1 ? `<div class="card"><div class="section-label">Evolucion de precio</div><canvas id="priceChart" height="220"></canvas></div>` : ''}
      <div class="card"><div class="section-label">Historial de busquedas — click para ver detalle</div>${historyHtml}</div>`;
  }

  return `
    <div class="header">
      <div class="header-top">
        <div><div class="header-label">Flight Monitor</div><h1>Dashboard de Precios</h1></div>
        <div style="display:flex;align-items:center;gap:12px">
          ${lastFetch ? `<span style="font-size:10px;color:#334155">Actualizado: ${lastFetch}</span>` : ''}
          <button class="btn btn-secondary" id="refreshBtn">↻ Refrescar</button>
          <button class="btn btn-ghost" id="disconnectBtn">Desconectar</button>
        </div>
      </div>
      ${errorHtml}
      ${destinoNames.length > 0 ? `<div class="destino-tabs">${destinoTabsHtml}</div>` : ''}
      ${busquedaTabsHtml ? `<div class="busqueda-tabs">${busquedaTabsHtml}</div>` : ''}
    </div>
    <div class="content">${contentHtml}</div>`;
}

function renderChart() {
  const canvas = document.getElementById("priceChart");
  if (!canvas) return;
  const registros = data[selectedBusqueda]?.registros || [];
  const objetivo = getObjetivo();
  if (chart) chart.destroy();
  chart = new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: registros.map(r => r.fecha.slice(5, 16)),
      datasets: [{
        label: "Precio USD", data: registros.map(r => r.precio),
        borderColor: "#0ea5e9", backgroundColor: "rgba(14,165,233,0.1)",
        fill: true, tension: 0.3, pointRadius: 4,
        pointBackgroundColor: "#0ea5e9", pointBorderColor: "#080e1a", pointBorderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => { const r = registros[ctx.dataIndex]; return `USD ${r.precio} (${r.aerolinea})`; }}}},
      scales: {
        x: { ticks: { color: "#475569", font: { size: 10 } }, grid: { color: "#1e293b" } },
        y: { ticks: { color: "#475569", font: { size: 10 } }, grid: { color: "#1e293b" } }
      }
    },
    plugins: [{ id: "obj", afterDraw(c) {
      const y = c.scales.y.getPixelForValue(objetivo);
      const ctx = c.ctx; ctx.save(); ctx.beginPath(); ctx.setLineDash([6,3]);
      ctx.strokeStyle = "#f59e0b"; ctx.lineWidth = 1;
      ctx.moveTo(c.chartArea.left, y); ctx.lineTo(c.chartArea.right, y); ctx.stroke();
      ctx.fillStyle = "#f59e0b"; ctx.font = "10px Inter";
      ctx.fillText("Objetivo $"+objetivo, c.chartArea.right - 80, y - 6); ctx.restore();
    }}]
  });
}

async function fetchData() {
  if (!apiUrl) return;
  error = null;
  try {
    const res = await fetch(apiUrl + "/api/precios");
    if (!res.ok) throw new Error("HTTP " + res.status);
    data = await res.json();
    lastFetch = new Date().toLocaleTimeString();
  } catch (e) { error = "Error: " + e.message; }
  render();
}

function setupConnectEvents() {
  document.getElementById("connectBtn").addEventListener("click", connect);
  document.getElementById("urlInput").addEventListener("keydown", e => { if (e.key === "Enter") connect(); });
}

function connect() {
  let url = document.getElementById("urlInput").value.trim();
  if (!url) return;
  if (!url.startsWith("http")) url = "https://" + url;
  if (url.endsWith("/")) url = url.slice(0, -1);
  apiUrl = url;
  localStorage.setItem("fm_api_url", apiUrl);
  fetchData();
}

function setupDashboardEvents() {
  document.getElementById("refreshBtn")?.addEventListener("click", fetchData);
  document.getElementById("disconnectBtn")?.addEventListener("click", () => {
    apiUrl = ""; data = null; selectedBusqueda = null; selectedDestino = null;
    localStorage.removeItem("fm_api_url"); render();
  });
  document.querySelectorAll(".destino-tab").forEach(t => t.addEventListener("click", () => {
    selectedDestino = t.dataset.destino; selectedBusqueda = null; render();
  }));
  document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", () => {
    selectedBusqueda = t.dataset.busqueda; render();
  }));
  document.querySelectorAll("[data-toggle]").forEach(el => el.addEventListener("click", () => {
    expandedRows[el.dataset.toggle] = !expandedRows[el.dataset.toggle]; render();
  }));
}

render();
if (apiUrl) { fetchData(); setInterval(fetchData, 60000); }
</script>
</body>
</html>
