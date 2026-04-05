/* ============================================================
   FRAUDGUARD v2 — Frontend Application Logic
   JWT Auth · SHAP · CSV Upload · Live Feed · History · Themes
   ============================================================ */

// ── Dynamic API base (works both locally and on Render) ──────────
const API_BASE = (
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1'
) ? 'http://localhost:5000' : window.location.origin;

// ── State ─────────────────────────────────────────────────────────
let jwtToken     = localStorage.getItem('fg_token') || null;
let currentUser  = JSON.parse(localStorage.getItem('fg_user') || 'null');
let feedInterval = null;
let feedCount    = 0;
let csvFile      = null;

// ── Sample Data ───────────────────────────────────────────────────
const SAMPLES = {
  fraud: { V14:-9.5, V10:-7.8, V4:-2.1, V12:-9.2, V17:-8.4, Amount:329.0, label:'🚨 Known Fraud Pattern' },
  legit: { V14:0.61, V10:0.34, V4:1.22, V12:0.15, V17:-0.14, Amount:45.0, label:'✅ Typical Legitimate Transaction' },
};

const GALLERY_ITEMS = [
  { file:'confusion_matrix.png',   label:'Confusion Matrix',    caption:'TP/FP/FN/TN breakdown' },
  { file:'roc_curves.png',         label:'ROC Curves',          caption:'All 3 models compared' },
  { file:'feature_analysis.png',   label:'Feature Analysis',    caption:'Importance & distribution' },
  { file:'amount_analysis.png',    label:'Amount Distribution', caption:'Fraud vs legitimate amounts' },
  { file:'correlation_matrix.png', label:'Correlation Matrix',  caption:'Feature correlations heatmap' },
  { file:'boxplots.png',           label:'Feature Boxplots',    caption:'Top 8 features by class' },
];

const FEATURE_INSIGHTS = [
  { feature:'V14', importance:29.8, rank:'#1', desc:'The single most powerful fraud indicator. Fraudulent transactions show dramatically negative V14 values (mean −6.97 vs 0.01 for legitimate).' },
  { feature:'V10', importance:29.2, rank:'#2', desc:'Second strongest predictor. Together with V14 these two features account for ~59% of the model\'s total detection power.' },
  { feature:'V4',  importance:6.2,  rank:'#3', desc:'Important secondary feature. Often used as a tiebreaker in ambiguous transactions.' },
  { feature:'V17', importance:3.3,  rank:'#4', desc:'Shows distinct statistical patterns between classes. Complements V14 and V10 in capturing complex fraud signatures.' },
  { feature:'V8',  importance:3.0,  rank:'#5', desc:'Captures subtle behavioral patterns. Adds critical signal in ensemble decisions.' },
  { feature:'V12', importance:2.7,  rank:'#6', desc:'Correlated with fraudulent spending patterns. Works in combination with other top-ranked features.' },
];

// ── Auth Headers ─────────────────────────────────────────────────
function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (jwtToken) h['Authorization'] = `Bearer ${jwtToken}`;
  return h;
}

// ── Theme Toggle ──────────────────────────────────────────────────
function toggleTheme() {
  const html    = document.documentElement;
  const isDark  = html.getAttribute('data-theme') === 'dark';
  const newTheme = isDark ? 'light' : 'dark';
  html.setAttribute('data-theme', newTheme);
  document.getElementById('themeToggle').textContent = newTheme === 'dark' ? '🌙' : '☀️';
  localStorage.setItem('fg_theme', newTheme);
}

function initTheme() {
  const saved = localStorage.getItem('fg_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  document.getElementById('themeToggle').textContent = saved === 'dark' ? '🌙' : '☀️';
}

// ── Auth Modal ────────────────────────────────────────────────────
function openAuthModal()  { document.getElementById('authModal').classList.add('open'); }
function closeAuthModal() { document.getElementById('authModal').classList.remove('open'); }

function switchTab(tab) {
  const isLogin = tab === 'login';
  document.getElementById('loginForm').style.display    = isLogin ? 'block' : 'none';
  document.getElementById('registerForm').style.display = isLogin ? 'none'  : 'block';
  document.getElementById('tabLogin').classList.toggle('active', isLogin);
  document.getElementById('tabRegister').classList.toggle('active', !isLogin);
}

async function doLogin() {
  const email    = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  const errEl    = document.getElementById('loginError');
  const btn      = document.getElementById('loginBtn');
  errEl.textContent = '';

  if (!email || !password) { errEl.textContent = 'Email and password are required'; return; }

  btn.disabled = true; btn.innerHTML = '<div class="spinner"></div>&nbsp;Logging in…';
  try {
    const res  = await fetch(`${API_BASE}/auth/login`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email, password}) });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.error || 'Login failed'; return; }
    saveAuth(data.access_token, data.user);
    closeAuthModal();
    showToast(`Welcome back, ${data.user.email.split('@')[0]}! 👋`, 'green');
    updateAuthUI();
  } catch { errEl.textContent = 'Network error. Is the API running?'; }
  finally { btn.disabled = false; btn.innerHTML = '🔐 Login'; }
}

async function doRegister() {
  const email    = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;
  const errEl    = document.getElementById('registerError');
  const btn      = document.getElementById('registerBtn');
  errEl.textContent = '';

  if (!email || !password) { errEl.textContent = 'Email and password are required'; return; }
  if (password.length < 8)  { errEl.textContent = 'Password must be at least 8 characters'; return; }

  btn.disabled = true; btn.innerHTML = '<div class="spinner"></div>&nbsp;Creating account…';
  try {
    const res  = await fetch(`${API_BASE}/auth/register`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email, password}) });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.error || 'Registration failed'; return; }
    saveAuth(data.access_token, data.user);
    closeAuthModal();
    showToast('Account created! Welcome to FraudGuard 🎉', 'green');
    updateAuthUI();
  } catch { errEl.textContent = 'Network error. Is the API running?'; }
  finally { btn.disabled = false; btn.innerHTML = '🚀 Create Account'; }
}

function doLogout() {
  jwtToken = null; currentUser = null;
  localStorage.removeItem('fg_token');
  localStorage.removeItem('fg_user');
  updateAuthUI();
  document.getElementById('history').style.display = 'none';
  showToast('Logged out successfully', 'green');
}

function saveAuth(token, user) {
  jwtToken = token; currentUser = user;
  localStorage.setItem('fg_token', token);
  localStorage.setItem('fg_user', JSON.stringify(user));
}

function updateAuthUI() {
  const isLoggedIn = !!jwtToken;
  document.getElementById('authArea').style.display  = isLoggedIn ? 'none'  : 'block';
  document.getElementById('userArea').style.display  = isLoggedIn ? 'flex'  : 'none';
  document.getElementById('historyNavLink').style.display = isLoggedIn ? 'inline-block' : 'none';
  document.getElementById('history').style.display   = isLoggedIn ? 'block' : 'none';
  
  const csvActions = document.getElementById('csvActions');
  if (csvActions) csvActions.style.display = isLoggedIn && csvFile ? 'flex' : 'none';

  document.querySelectorAll('.auth-required').forEach(block => {
    const overlay = block.querySelector('.locked-overlay');
    const content = block.querySelector('.auth-placeholder');
    if (isLoggedIn) {
      if (overlay) overlay.style.display = 'none';
      if (content) {
        content.style.filter = 'none';
        content.style.opacity = '1';
        content.style.pointerEvents = 'auto';
        content.style.userSelect = 'auto';
      }
    } else {
      if (overlay) overlay.style.display = 'flex';
      if (content) {
        content.style.filter = 'blur(5px) grayscale(0.6)';
        content.style.opacity = '0.5';
        content.style.pointerEvents = 'none';
        content.style.userSelect = 'none';
      }
    }
  });

  if (currentUser) {
    document.getElementById('userAvatar').textContent = currentUser.email[0].toUpperCase();
  }
  if (isLoggedIn) loadHistory('all');
}

// ── API Health Check ──────────────────────────────────────────────
async function checkApiStatus() {
  const dot = document.getElementById('statusDot');
  const txt = document.getElementById('statusText');
  try {
    const res  = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
    const data = await res.json();
    if (data.status === 'healthy') {
      dot.className = 'status-dot online';
      txt.textContent = data.model_loaded ? 'System Online' : 'No Model Loaded';
    } else throw new Error();
  } catch {
    dot.className   = 'status-dot offline';
    txt.textContent = 'System Offline';
  }
}

// ── Animated Counters ─────────────────────────────────────────────
function animateCounter(el) {
  const target = parseFloat(el.dataset.count);
  const suffix = el.dataset.suffix || '';
  const dec    = parseInt(el.dataset.decimals || '0', 10);
  const steps  = 60; let current = 0;
  const inc    = target / steps;
  const timer  = setInterval(() => {
    current = Math.min(current + inc, target);
    el.textContent = current.toFixed(dec).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + suffix;
    if (current >= target) clearInterval(timer);
  }, 1800 / steps);
}

// ── Scroll Reveal ─────────────────────────────────────────────────
function setupReveal() {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        const counter = e.target.querySelector('[data-count]');
        if (counter && !counter.dataset.animated) { counter.dataset.animated = 'true'; animateCounter(counter); }
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
}

// ── Gallery ───────────────────────────────────────────────────────
function buildGallery() {
  document.getElementById('galleryGrid').innerHTML = GALLERY_ITEMS.map(item => `
    <div class="gallery-item reveal" onclick="openLightbox('${API_BASE}/results/${item.file}','${item.label}')">
      <img src="${API_BASE}/results/${item.file}" alt="${item.label}" onerror="this.parentElement.style.display='none'" />
      <div class="gallery-overlay"><span>🔍 View Full Size</span></div>
      <div class="gallery-caption">${item.label} <span class="text-muted">— ${item.caption}</span></div>
    </div>
  `).join('');
}

function openLightbox(src, alt) {
  document.getElementById('lightboxImg').src = src;
  document.getElementById('lightboxImg').alt = alt;
  document.getElementById('lightbox').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeLightbox(e) {
  if (e && e.target !== document.getElementById('lightbox') && !e.target.classList.contains('lightbox-close')) return;
  document.getElementById('lightbox').classList.remove('open');
  document.body.style.overflow = '';
}

// ── Feature Insights ──────────────────────────────────────────────
function buildFeatureInsights() {
  const max = Math.max(...FEATURE_INSIGHTS.map(f => f.importance));
  document.getElementById('featuresGrid').innerHTML = FEATURE_INSIGHTS.map(f => `
    <div class="card feature-card reveal">
      <div class="feature-rank">${f.rank} Most Important</div>
      <div class="feature-name">${f.feature}</div>
      <div class="feature-percent">${f.importance}% importance</div>
      <div class="feature-bar-bg"><div class="feature-bar" style="width:${(f.importance/max)*100}%"></div></div>
      <div class="feature-desc">${f.desc}</div>
    </div>
  `).join('');
}

// ── Range Sliders ─────────────────────────────────────────────────
function syncRange(id) {
  const val = parseFloat(document.getElementById(`range${id}`).value);
  document.getElementById(id).value = val;
  document.getElementById(`val${id}`).textContent = val.toFixed(2);
}
function setRangeValue(id, value) {
  const r = document.getElementById(`range${id}`);
  const h = document.getElementById(id);
  const v = document.getElementById(`val${id}`);
  if (r) r.value = value;
  if (h) h.value = value;
  if (v) v.textContent = parseFloat(value).toFixed(2);
}
function loadSample(type) {
  const s = SAMPLES[type];
  setRangeValue('V14', s.V14); setRangeValue('V10', s.V10); setRangeValue('V4', s.V4);
  document.getElementById('V12').value = s.V12;
  document.getElementById('V17').value = s.V17;
  document.getElementById('Amount').value = s.Amount;
  showToast(`Loaded: ${s.label}`, type === 'fraud' ? 'red' : 'green');
}
function clearForm() {
  ['V14','V10','V4'].forEach(id => setRangeValue(id, 0));
  ['V12','V17'].forEach(id => document.getElementById(id).value = 0);
  document.getElementById('Amount').value = 100;
  document.getElementById('resultDisplay').classList.remove('visible');
  document.getElementById('resultPlaceholder').style.display = 'flex';
  document.getElementById('shapSection').style.display = 'none';
}

// ── Predict ───────────────────────────────────────────────────────
async function runPrediction() {
  const btn = document.getElementById('predictBtn');
  btn.disabled = true; btn.innerHTML = '<div class="spinner"></div>&nbsp;Analyzing…';

  const values = {};
  ['V14','V10','V4','V12','V17'].forEach(id => { values[id] = parseFloat(document.getElementById(id)?.value || 0); });
  const amount = parseFloat(document.getElementById('Amount').value) || 0;

  const featureArray = [];
  for (let i = 1; i <= 28; i++) featureArray.push(values[`V${i}`] !== undefined ? values[`V${i}`] : 0);
  featureArray.push(amount);

  try {
    const res  = await fetch(`${API_BASE}/predict`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ features: featureArray })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    renderPredictionResult(data);
    if (data.shap_values) renderShap(data.shap_values);
    if (jwtToken) loadHistory('all');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'red');
    renderDemoResult();
  } finally {
    btn.disabled = false; btn.innerHTML = '⚡ Analyze Transaction';
  }
}

function renderPredictionResult(data) {
  const isFraud   = data.prediction === 1;
  const fraudPct  = (data.fraud_probability * 100).toFixed(1);
  const legitPct  = (data.legitimate_probability * 100).toFixed(1);
  const conf      = (data.confidence * 100).toFixed(1);

  document.getElementById('resultPlaceholder').style.display = 'none';
  const display = document.getElementById('resultDisplay');
  display.classList.add('visible');

  document.getElementById('resultVerdict').className = `result-verdict ${isFraud ? 'fraud' : 'legitimate'}`;
  document.getElementById('resultIcon').textContent  = isFraud ? '🚨' : '✅';
  document.getElementById('resultLabel').textContent = data.prediction_label;
  document.getElementById('probBarFill').style.width = `${fraudPct}%`;
  document.getElementById('fraudPct').textContent    = `${fraudPct}%`;
  document.getElementById('legitPct').textContent    = `${legitPct}%`;
  document.getElementById('statConfidence').textContent = `${conf}%`;
  document.getElementById('statFraudProb').textContent  = `${fraudPct}%`;
}

function renderShap(shapValues) {
  const sec  = document.getElementById('shapSection');
  const bars = document.getElementById('shapBars');
  if (!shapValues) { sec.style.display = 'none'; return; }

  const sorted = Object.entries(shapValues)
    .map(([f, v]) => ({ f, v }))
    .sort((a, b) => Math.abs(b.v) - Math.abs(a.v))
    .slice(0, 8);

  const maxAbs = Math.max(...sorted.map(x => Math.abs(x.v)));

  bars.innerHTML = sorted.map(({ f, v }) => `
    <div class="shap-bar-row">
      <span class="shap-feat">${f}</span>
      <div class="shap-bar-bg">
        <div class="shap-bar-fill ${v > 0 ? 'positive' : 'negative'}" style="height:100%;width:${(Math.abs(v)/maxAbs)*100}%;border-radius:3px;"></div>
      </div>
      <span class="shap-val">${v > 0 ? '+' : ''}${v.toFixed(2)}</span>
    </div>
  `).join('');

  sec.style.display = 'block';
}

function renderDemoResult() {
  const v14 = parseFloat(document.getElementById('V14')?.value || 0);
  const isFraud = v14 < -5;
  renderPredictionResult({
    prediction: isFraud ? 1 : 0,
    prediction_label: isFraud ? 'Fraud [DEMO]' : 'Legitimate [DEMO]',
    fraud_probability: isFraud ? 0.89 : 0.04,
    legitimate_probability: isFraud ? 0.11 : 0.96,
    confidence: isFraud ? 0.89 : 0.96,
  });
}

// ── Batch Predict ─────────────────────────────────────────────────
function loadBatchSample() {
  const sample = { transactions: [
    { features: [-9.5,0,0,-2.1,0,0,0,0,0,-7.8,0,-9.2,0,0,0,0,-8.4,0,0,0,0,0,0,0,0,0,0,0,329.0], note:'High-risk' },
    { features: [0.61,0.2,0.3,1.22,0,0,0,0,0,0.34,0,0.15,0,0,0,0,-0.14,0,0,0,0,0,0,0,0,0,0,0,45.0], note:'Normal' },
  ]};
  document.getElementById('batchInput').value = JSON.stringify(sample, null, 2);
}
function clearBatch() { document.getElementById('batchInput').value = ''; document.getElementById('batchResults').innerHTML = ''; }

async function runBatchPredict() {
  const btn = document.getElementById('batchBtn');
  btn.disabled = true; btn.innerHTML = '<div class="spinner"></div>&nbsp;Processing…';
  let payload;
  try { payload = JSON.parse(document.getElementById('batchInput').value); }
  catch { showToast('Invalid JSON format', 'red'); btn.disabled = false; btn.innerHTML = '⚡ Run Batch'; return; }

  try {
    const res  = await fetch(`${API_BASE}/batch-predict`, { method:'POST', headers:authHeaders(), body:JSON.stringify(payload) });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    renderBatchResults(data.results, payload.transactions);
  } catch(err) {
    showToast(`Error: ${err.message}`, 'red');
    renderBatchDemoResults(payload.transactions);
  } finally { btn.disabled = false; btn.innerHTML = '⚡ Run Batch'; }
}

function renderBatchResults(results, txns) {
  const fraudCount = results.filter(r => r.prediction === 1).length;
  const rows = results.map((r, i) => {
    const note = txns[i]?.note || `Transaction ${i+1}`;
    const isFraud = r.prediction === 1;
    return `<tr class="${isFraud ? 'row-fraud' : 'row-legit'}">
      <td>#${i+1} <span class="text-muted" style="font-size:11px">— ${note}</span></td>
      <td><span class="badge ${isFraud ? 'badge-fraud' : 'badge-legit'}">${r.prediction_label}</span></td>
      <td class="${isFraud ? 'text-red' : 'text-green'}">${((r.fraud_probability||0)*100).toFixed(1)}%</td>
      <td>${((r.confidence||0)*100).toFixed(1)}%</td>
    </tr>`;
  }).join('');

  document.getElementById('batchResults').innerHTML = `
    <div style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap">
      <div class="result-stat-box" style="flex:1;min-width:100px"><div class="result-stat-val text-red">${fraudCount}</div><div class="result-stat-lbl">Fraud</div></div>
      <div class="result-stat-box" style="flex:1;min-width:100px"><div class="result-stat-val text-green">${results.length-fraudCount}</div><div class="result-stat-lbl">Legitimate</div></div>
      <div class="result-stat-box" style="flex:1;min-width:100px"><div class="result-stat-val">${results.length}</div><div class="result-stat-lbl">Total</div></div>
    </div>
    <div style="overflow-x:auto"><table class="batch-table"><thead><tr><th>Transaction</th><th>Verdict</th><th>Fraud Risk</th><th>Confidence</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderBatchDemoResults(txns) {
  if (!txns) return;
  renderBatchResults(txns.map(t => {
    const v14 = (t.features||[])[13] || 0;
    const isFraud = v14 < -5;
    return { prediction: isFraud?1:0, prediction_label: isFraud?'Fraud [DEMO]':'Legitimate [DEMO]', fraud_probability: isFraud?0.88:0.03, legitimate_probability: isFraud?0.12:0.97, confidence: isFraud?0.88:0.97 };
  }), txns);
}

// ── CSV Upload ────────────────────────────────────────────────────
function handleCsvSelect(event) {
  csvFile = event.target.files[0];
  if (csvFile) {
    document.getElementById('csvFileName').textContent = `📄 ${csvFile.name} (${(csvFile.size/1024).toFixed(1)} KB)`;
    document.getElementById('csvActions').style.display = jwtToken ? 'flex' : 'none';
    document.getElementById('csvLoginNote').style.display = jwtToken ? 'none' : 'block';
  }
}

function clearCsv() {
  csvFile = null;
  document.getElementById('csvFileInput').value = '';
  document.getElementById('csvFileName').textContent = 'Columns needed: V1–V28, Amount';
  document.getElementById('csvActions').style.display = 'none';
  document.getElementById('csvResult').textContent = '';
}

async function uploadCsv() {
  if (!csvFile || !jwtToken) return;
  const btn = document.getElementById('csvUploadBtn');
  btn.disabled = true; btn.innerHTML = '<div class="spinner"></div>&nbsp;Processing…';

  const formData = new FormData();
  formData.append('file', csvFile);

  try {
    const res = await fetch(`${API_BASE}/predict/csv`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${jwtToken}` },
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Upload failed');
    }

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'fraud_predictions.csv'; a.click();
    URL.revokeObjectURL(url);

    document.getElementById('csvResult').innerHTML = '<span style="color:var(--accent-green)">✅ Results downloaded! Check your downloads folder.</span>';
    loadHistory('all');
  } catch(err) {
    document.getElementById('csvResult').innerHTML = `<span style="color:var(--accent-red)">❌ ${err.message}</span>`;
  } finally {
    btn.disabled = false; btn.innerHTML = '⬆️ Analyze & Download Results';
  }
}

// ── Live Feed ─────────────────────────────────────────────────────
function randomFeatures() {
  const isFraud = Math.random() < 0.15;
  const features = Array(28).fill(0).map(() => (Math.random()-0.5)*2);
  if (isFraud) { features[13] = -(5 + Math.random()*6); features[9] = -(4 + Math.random()*5); }
  features.push(Math.random() * 500);
  return features;
}

function startFeed() {
  document.getElementById('feedStartBtn').style.display = 'none';
  document.getElementById('feedStopBtn').style.display  = 'inline-flex';

  feedInterval = setInterval(async () => {
    const features = randomFeatures();
    feedCount++;
    document.getElementById('feedCounter').textContent = `${feedCount} transactions processed`;

    try {
      const res  = await fetch(`${API_BASE}/predict`, {
        method:'POST', headers:authHeaders(), body:JSON.stringify({features})
      });
      const data = await res.json();
      if (!data.error) appendFeedRow(data, features[28], feedCount);
    } catch { appendFeedRow({prediction:Math.random()<0.1?1:0,prediction_label:Math.random()<0.1?'Fraud':'Legitimate',fraud_probability:Math.random()*0.3,confidence:0.8+Math.random()*0.2}, features[28], feedCount, true); }
  }, 2000);
}

function stopFeed() {
  clearInterval(feedInterval);
  document.getElementById('feedStartBtn').style.display  = 'inline-flex';
  document.getElementById('feedStopBtn').style.display   = 'none';
}

function appendFeedRow(data, amount, num, demo = false) {
  const tbody   = document.getElementById('feedBody');
  const isFraud = data.prediction === 1;
  const label   = demo ? data.prediction_label + ' [DEMO]' : data.prediction_label;
  const now     = new Date().toLocaleTimeString();

  const tr = document.createElement('tr');
  if (isFraud) tr.className = 'feed-fraud';
  tr.innerHTML = `
    <td>${num}</td>
    <td>$${parseFloat(amount).toFixed(2)}</td>
    <td><span class="badge ${isFraud?'badge-fraud':'badge-legit'}">${label}</span></td>
    <td class="${isFraud?'text-red':'text-green'}">${((data.fraud_probability||0)*100).toFixed(1)}%</td>
    <td>${((data.confidence||0)*100).toFixed(1)}%</td>
    <td class="text-muted">${now}</td>`;

  tbody.insertBefore(tr, tbody.firstChild);
  if (tbody.children.length > 50) tbody.removeChild(tbody.lastChild);
}

// ── Prediction History ────────────────────────────────────────────
async function loadHistory(filter = 'all') {
  if (!jwtToken) return;
  document.getElementById('historyContent').innerHTML = '<p class="text-muted" style="text-align:center;padding:24px">Loading…</p>';

  // Update active filter button
  ['All','Fraud','Legit'].forEach(f => document.getElementById(`hf${f}`)?.classList.remove('active'));
  const btnMap = {all:'hfAll', fraud:'hfFraud', legitimate:'hfLegit'};
  document.getElementById(btnMap[filter])?.classList.add('active');

  try {
    const res  = await fetch(`${API_BASE}/predict/history?filter=${filter}&per_page=20`, { headers: authHeaders() });
    const data = await res.json();
    if (!res.ok) { document.getElementById('historyContent').innerHTML = `<p class="text-muted" style="text-align:center;padding:24px">${data.error}</p>`; return; }

    if (!data.predictions.length) {
      document.getElementById('historyContent').innerHTML = '<p class="text-muted" style="text-align:center;padding:32px">No predictions yet. Run an analysis above!</p>';
      return;
    }

    const rows = data.predictions.map(p => {
      const isFraud = p.prediction === 1;
      const ts = new Date(p.timestamp).toLocaleString();
      return `<tr>
        <td class="text-muted" style="font-size:12px">${ts}</td>
        <td><span class="badge ${isFraud?'badge-fraud':'badge-legit'}">${p.prediction_label}</span></td>
        <td class="${isFraud?'text-red':'text-green'}">${(p.fraud_probability*100).toFixed(1)}%</td>
        <td>${(p.confidence*100).toFixed(1)}%</td>
        <td class="text-muted" style="font-size:11px">${p.amount ? '$'+p.amount.toFixed(2) : '—'}</td>
        <td><span class="badge" style="background:rgba(255,255,255,0.06);color:var(--text-muted)">${p.source}</span></td>
      </tr>`;
    }).join('');

    document.getElementById('historyContent').innerHTML = `
      <div style="overflow-x:auto">
        <table class="history-table">
          <thead><tr><th>Time</th><th>Verdict</th><th>Fraud Risk</th><th>Confidence</th><th>Amount</th><th>Source</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="text-muted" style="font-size:12px;margin-top:12px;text-align:right">${data.total} total · ${data.fraud_total} fraud · ${data.legit_total} legit</p>`;
  } catch { document.getElementById('historyContent').innerHTML = '<p class="text-muted" style="text-align:center;padding:24px">Could not load history.</p>'; }
}

async function clearHistory() {
  if (!jwtToken) return;
  
  showConfirm(
    'Delete History?',
    'Are you sure you want to delete all your prediction history? This action cannot be undone.',
    async () => {
      try {
        const res = await fetch(`${API_BASE}/predict/history`, {
          method: 'DELETE',
          headers: authHeaders()
        });
        const data = await res.json();
        if (res.ok) {
          showToast('History cleared successfully', 'green');
          loadHistory('all');
        } else {
          showToast(data.error || 'Failed to clear history', 'red');
        }
      } catch (err) {
        showToast('Failed to clear history', 'red');
      }
    },
    '🗑️'
  );
}

// ── Custom Confirm Modal ──────────────────────────────────────────
function showConfirm(title, message, onConfirm, icon = '❓') {
  const modal   = document.getElementById('confirmModal');
  const tEl     = document.getElementById('confirmTitle');
  const mEl     = document.getElementById('confirmMessage');
  const iEl     = document.getElementById('confirmIcon');
  const okBtn   = document.getElementById('confirmOk');
  const canBtn  = document.getElementById('confirmCancel');

  tEl.textContent = title;
  mEl.textContent = message;
  iEl.textContent = icon;

  modal.classList.add('open');

  const close = () => modal.classList.remove('open');

  okBtn.onclick = () => { onConfirm(); close(); };
  canBtn.onclick = close;
}

// ── Toast ─────────────────────────────────────────────────────────
function showToast(message, color = 'red') {
  document.querySelector('.toast')?.remove();
  const t = document.createElement('div');
  t.className = 'toast';
  t.style.borderColor = color === 'green' ? 'rgba(0,255,136,0.4)' : 'rgba(255,51,102,0.4)';
  t.style.color       = color === 'green' ? 'var(--accent-green)' : 'var(--accent-red)';
  t.textContent = message;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// ── CSV Drag & Drop ───────────────────────────────────────────────
function setupCsvDrop() {
  const zone = document.getElementById('csvDropZone');
  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.csv')) {
      csvFile = file;
      document.getElementById('csvFileName').textContent = `📄 ${file.name} (${(file.size/1024).toFixed(1)} KB)`;
      document.getElementById('csvActions').style.display = jwtToken ? 'flex' : 'none';
      document.getElementById('csvLoginNote').style.display = jwtToken ? 'none' : 'block';
    } else showToast('Please drop a .csv file', 'red');
  });
}

// ── Keyboard Shortcuts ────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeLightbox({ target: document.getElementById('lightbox') });
    closeAuthModal();
  }
});

// ── Init ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  checkApiStatus();
  setInterval(checkApiStatus, 20000);

  buildGallery();
  buildFeatureInsights();
  setupReveal();
  setupCsvDrop();
  updateAuthUI();

  // Trigger reveal for above-fold elements
  document.querySelectorAll('.reveal').forEach(el => {
    if (el.getBoundingClientRect().top < window.innerHeight) el.classList.add('visible');
  });
});
