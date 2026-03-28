/* ============================================
   FRAUDGUARD — FRONTEND APPLICATION LOGIC
   ============================================ */

const API_BASE = 'http://localhost:5000';

// ── SAMPLE DATA ──────────────────────────────────────────────────
const SAMPLES = {
  fraud: {
    V14: -9.5,
    V10: -7.8,
    V4: -2.1,
    V12: -9.2,
    V17: -8.4,
    Amount: 329.0,
    label: '🚨 Known Fraud Pattern'
  },
  legit: {
    V14: 0.61,
    V10: 0.34,
    V4: 1.22,
    V12: 0.15,
    V17: -0.14,
    Amount: 45.0,
    label: '✅ Typical Legitimate Transaction'
  }
};

const GALLERY_ITEMS = [
  { file: 'confusion_matrix.png',  label: 'Confusion Matrix',     caption: 'TP/FP/FN/TN breakdown' },
  { file: 'roc_curves.png',        label: 'ROC Curves',           caption: 'All 3 models compared' },
  { file: 'feature_analysis.png',  label: 'Feature Analysis',     caption: 'Importance & distribution' },
  { file: 'amount_analysis.png',   label: 'Amount Distribution',  caption: 'Fraud vs. legitimate amounts' },
  { file: 'correlation_matrix.png',label: 'Correlation Matrix',   caption: 'Feature correlations heatmap' },
  { file: 'boxplots.png',          label: 'Feature Boxplots',     caption: 'Top 8 features by class' },
];

const FEATURE_INSIGHTS = [
  { feature: 'V14', importance: 29.8, rank: '#1', desc: 'The single most powerful fraud indicator. Fraudulent transactions show dramatically negative V14 values (mean −6.97 vs 0.01 for legitimate), with far higher variance.' },
  { feature: 'V10', importance: 29.2, rank: '#2', desc: 'Second strongest predictor. Together with V14, these two features account for ~59% of the model\'s total detection power.' },
  { feature: 'V4',  importance: 6.2,  rank: '#3', desc: 'Important secondary feature with a positive correlation to fraud patterns. Often used as a tiebreaker in ambiguous transactions.' },
  { feature: 'V17', importance: 3.3,  rank: '#4', desc: 'Shows distinct statistical patterns between classes. Complements V14 and V10 in capturing complex fraud signatures.' },
  { feature: 'V8',  importance: 3.0,  rank: '#5', desc: 'Captures subtle behavioral patterns. Lower importance individually, but adds critical signal in ensemble decisions.' },
  { feature: 'V12', importance: 2.7,  rank: '#6', desc: 'Correlated with fraudulent spending patterns. Works in combination with other top-ranked features.' },
];

// ── API HEALTH CHECK ──────────────────────────────────────────────
async function checkApiStatus() {
  const dot = document.getElementById('statusDot');
  const txt = document.getElementById('statusText');
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    if (data.status === 'healthy') {
      dot.className = 'status-dot online';
      txt.textContent = data.model_loaded ? 'API Online · Model Loaded' : 'API Online · No Model';
    } else {
      throw new Error('not healthy');
    }
  } catch {
    dot.className = 'status-dot offline';
    txt.textContent = 'API Offline';
  }
}

// ── ANIMATED COUNTERS ─────────────────────────────────────────────
function animateCounter(el) {
  const target   = parseFloat(el.dataset.count);
  const suffix   = el.dataset.suffix || '';
  const decimals = parseInt(el.dataset.decimals || '0', 10);
  const duration = 1800;
  const steps    = 60;
  const step     = duration / steps;
  let current    = 0;
  const increment = target / steps;

  const timer = setInterval(() => {
    current = Math.min(current + increment, target);
    el.textContent = current.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + suffix;
    if (current >= target) clearInterval(timer);
  }, step);
}

// ── SCROLL REVEAL ─────────────────────────────────────────────────
function setupReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        // Trigger counter animation for stat cards
        const counter = entry.target.querySelector('[data-count]');
        if (counter && !counter.dataset.animated) {
          counter.dataset.animated = 'true';
          animateCounter(counter);
        }
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
}

// ── GALLERY ───────────────────────────────────────────────────────
function buildGallery() {
  const grid = document.getElementById('galleryGrid');
  grid.innerHTML = GALLERY_ITEMS.map(item => `
    <div class="gallery-item reveal" onclick="openLightbox('${API_BASE}/results/${item.file}', '${item.label}')">
      <img src="${API_BASE}/results/${item.file}"
           alt="${item.label}"
           onerror="this.parentElement.style.display='none'" />
      <div class="gallery-overlay">
        <span>🔍 View Full Size</span>
      </div>
      <div class="gallery-caption">${item.label} <span class="text-muted">— ${item.caption}</span></div>
    </div>
  `).join('');
}

function openLightbox(src, alt) {
  const lb = document.getElementById('lightbox');
  document.getElementById('lightboxImg').src = src;
  document.getElementById('lightboxImg').alt = alt;
  lb.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeLightbox(e) {
  if (e && e.target !== document.getElementById('lightbox') && !e.target.classList.contains('lightbox-close')) return;
  document.getElementById('lightbox').classList.remove('open');
  document.body.style.overflow = '';
}

// ── FEATURE INSIGHTS ─────────────────────────────────────────────
function buildFeatureInsights() {
  const grid = document.getElementById('featuresGrid');
  const maxImportance = Math.max(...FEATURE_INSIGHTS.map(f => f.importance));

  grid.innerHTML = FEATURE_INSIGHTS.map(f => `
    <div class="card feature-card reveal">
      <div class="feature-rank">${f.rank} Most Important</div>
      <div class="feature-name">${f.feature}</div>
      <div class="feature-percent">${f.importance}% importance</div>
      <div class="feature-bar-bg">
        <div class="feature-bar" style="width:${(f.importance / maxImportance) * 100}%"></div>
      </div>
      <div class="feature-desc">${f.desc}</div>
    </div>
  `).join('');
}

// ── RANGE SLIDERS ─────────────────────────────────────────────────
function syncRange(featureId) {
  const rangeEl = document.getElementById(`range${featureId}`);
  const hiddenEl = document.getElementById(featureId);
  const valEl   = document.getElementById(`val${featureId}`);
  const val = parseFloat(rangeEl.value);
  hiddenEl.value = val;
  valEl.textContent = val.toFixed(2);
}

function setRangeValue(featureId, value) {
  const rangeEl  = document.getElementById(`range${featureId}`);
  const hiddenEl = document.getElementById(featureId);
  const valEl    = document.getElementById(`val${featureId}`);
  if (rangeEl) rangeEl.value = value;
  if (hiddenEl) hiddenEl.value = value;
  if (valEl) valEl.textContent = parseFloat(value).toFixed(2);
}

// ── QUICK FILL ────────────────────────────────────────────────────
function loadSample(type) {
  const s = SAMPLES[type];
  setRangeValue('V14', s.V14);
  setRangeValue('V10', s.V10);
  setRangeValue('V4', s.V4);
  document.getElementById('V12').value = s.V12;
  document.getElementById('V17').value = s.V17;
  document.getElementById('Amount').value = s.Amount;
  showToast(`Loaded: ${s.label}`, type === 'fraud' ? 'red' : 'green');
}

function clearForm() {
  ['V14', 'V10', 'V4'].forEach(id => setRangeValue(id, 0));
  ['V12', 'V17'].forEach(id => { document.getElementById(id).value = 0; });
  document.getElementById('Amount').value = 100;
  document.getElementById('resultDisplay').classList.remove('visible');
  document.getElementById('resultPlaceholder').style.display = 'block';
}

// ── PREDICT ───────────────────────────────────────────────────────
async function runPrediction() {
  const btn = document.getElementById('predictBtn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div>&nbsp;Analyzing…';

  // Build feature array (zeroed out for V1–V28 except our key ones)
  const values = {};
  ['V14', 'V10', 'V4', 'V12', 'V17'].forEach(id => {
    values[id] = parseFloat(document.getElementById(id)?.value || 0);
  });
  const amount = parseFloat(document.getElementById('Amount').value) || 0;

  // Build full 29-feature array
  const featureArray = [];
  for (let i = 1; i <= 28; i++) {
    const key = `V${i}`;
    featureArray.push(values[key] !== undefined ? values[key] : 0);
  }
  featureArray.push(amount);

  try {
    const res = await fetch(`${API_BASE}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ features: featureArray })
    });
    const data = await res.json();

    if (data.error) throw new Error(data.error);
    renderPredictionResult(data);

  } catch (err) {
    showToast(`Error: ${err.message}. Is the Flask API running?`);
    // Show demo result when API is offline
    renderDemoResult();
  } finally {
    btn.disabled = false;
    btn.innerHTML = '⚡ Analyze Transaction';
  }
}

function renderPredictionResult(data) {
  const isFraud = data.prediction === 1;
  const fraudPct = (data.fraud_probability * 100).toFixed(1);
  const legitPct = (data.legitimate_probability * 100).toFixed(1);
  const confidence = (data.confidence * 100).toFixed(1);

  document.getElementById('resultPlaceholder').style.display = 'none';
  const display = document.getElementById('resultDisplay');
  display.classList.remove('visible');
  display.classList.add('visible');

  const verdict = document.getElementById('resultVerdict');
  verdict.className = `result-verdict ${isFraud ? 'fraud' : 'legitimate'}`;

  document.getElementById('resultIcon').textContent = isFraud ? '🚨' : '✅';
  document.getElementById('resultLabel').textContent = data.prediction_label;
  document.getElementById('probBarFill').style.width = `${fraudPct}%`;
  document.getElementById('fraudPct').textContent = `${fraudPct}%`;
  document.getElementById('legitPct').textContent = `${legitPct}%`;
  document.getElementById('statConfidence').textContent = `${confidence}%`;
  document.getElementById('statFraudProb').textContent = `${fraudPct}%`;
}

function renderDemoResult() {
  // Parse current input to guess fraud/legit
  const v14 = parseFloat(document.getElementById('V14')?.value || 0);
  const isFraud = v14 < -5;
  const demoData = isFraud
    ? { prediction: 1, prediction_label: 'Fraud [DEMO]', fraud_probability: 0.89, legitimate_probability: 0.11, confidence: 0.89 }
    : { prediction: 0, prediction_label: 'Legitimate [DEMO]', fraud_probability: 0.04, legitimate_probability: 0.96, confidence: 0.96 };
  renderPredictionResult(demoData);
}

// ── BATCH PREDICT ─────────────────────────────────────────────────
function loadBatchSample() {
  const sample = {
    transactions: [
      { features: [-9.5, 0, 0, -2.1, 0, 0, 0, 0, 0, -7.8, 0, -9.2, 0, 0, 0, 0, -8.4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 329.0], note: 'High-risk transaction' },
      { features: [0.61, 0.2, 0.3, 1.22, 0.1, 0, 0, 0, 0, 0.34, 0, 0.15, 0, 0, 0, 0, -0.14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 45.0], note: 'Normal purchase' },
      { features: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 150.0], note: 'Unknown pattern' },
    ]
  };
  document.getElementById('batchInput').value = JSON.stringify(sample, null, 2);
}

function clearBatch() {
  document.getElementById('batchInput').value = '';
  document.getElementById('batchResults').innerHTML = '';
}

async function runBatchPredict() {
  const btn = document.getElementById('batchBtn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div>&nbsp;Processing…';

  let payload;
  try {
    payload = JSON.parse(document.getElementById('batchInput').value);
  } catch {
    showToast('Invalid JSON — please check your input format.');
    btn.disabled = false;
    btn.innerHTML = '⚡ Run Batch';
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/batch-predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    renderBatchResults(data.results, payload.transactions);
  } catch (err) {
    showToast(`Error: ${err.message}. Is the Flask API running?`);
    renderBatchDemoResults(payload.transactions);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '⚡ Run Batch';
  }
}

function renderBatchResults(results, transactions) {
  const fraudCount = results.filter(r => r.prediction === 1).length;
  const legitCount = results.filter(r => r.prediction === 0).length;

  const rows = results.map((r, i) => {
    const note = transactions[i]?.note || `Transaction ${i + 1}`;
    const isFraud = r.prediction === 1;
    const fraudPct = ((r.fraud_probability || 0) * 100).toFixed(1);
    const confidence = ((r.confidence || 0) * 100).toFixed(1);
    return `
      <tr class="${isFraud ? 'row-fraud' : 'row-legit'}">
        <td>#${i + 1} <span class="text-muted" style="font-size:11px;">— ${note}</span></td>
        <td><span class="badge ${isFraud ? 'badge-fraud' : 'badge-legit'}">${r.prediction_label}</span></td>
        <td class="${isFraud ? 'text-red' : 'text-green'}">${fraudPct}%</td>
        <td>${confidence}%</td>
      </tr>`;
  }).join('');

  document.getElementById('batchResults').innerHTML = `
    <div style="display:flex; gap:16px; margin-bottom:16px; flex-wrap:wrap;">
      <div class="result-stat-box" style="flex:1; min-width:120px;">
        <div class="result-stat-val text-red">${fraudCount}</div>
        <div class="result-stat-lbl">Fraud Detected</div>
      </div>
      <div class="result-stat-box" style="flex:1; min-width:120px;">
        <div class="result-stat-val text-green">${legitCount}</div>
        <div class="result-stat-lbl">Legitimate</div>
      </div>
      <div class="result-stat-box" style="flex:1; min-width:120px;">
        <div class="result-stat-val">${results.length}</div>
        <div class="result-stat-lbl">Total Checked</div>
      </div>
    </div>
    <div style="overflow-x:auto;">
      <table class="batch-table">
        <thead><tr>
          <th>Transaction</th>
          <th>Verdict</th>
          <th>Fraud Risk</th>
          <th>Confidence</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function renderBatchDemoResults(transactions) {
  if (!transactions) return;
  const demoResults = transactions.map((txn, i) => {
    const features = txn.features || [];
    const v14 = features[13] || 0;
    const v10 = features[9]  || 0;
    const isFraud = v14 < -5 || v10 < -5;
    return {
      prediction: isFraud ? 1 : 0,
      prediction_label: isFraud ? 'Fraud [DEMO]' : 'Legitimate [DEMO]',
      fraud_probability: isFraud ? 0.88 : 0.03,
      legitimate_probability: isFraud ? 0.12 : 0.97,
      confidence: isFraud ? 0.88 : 0.97,
    };
  });
  renderBatchResults(demoResults, transactions);
}

// ── TOAST NOTIFICATIONS ───────────────────────────────────────────
function showToast(message, color = 'red') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.borderColor = color === 'green' ? 'rgba(0,255,136,0.4)' : 'rgba(255,51,102,0.4)';
  toast.style.color = color === 'green' ? 'var(--accent-green)' : 'var(--accent-red)';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ── KEYBOARD SHORTCUTS ────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeLightbox({ target: document.getElementById('lightbox') });
});

// ── INIT ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkApiStatus();
  setInterval(checkApiStatus, 15000); // Re-check every 15s

  buildGallery();
  buildFeatureInsights();
  setupReveal();

  // Kick off reveal for above-fold elements
  document.querySelectorAll('.reveal').forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight) el.classList.add('visible');
  });
});
