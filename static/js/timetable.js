/* ════════════════════════════════════════════════════════
   College Timetable Generator — Frontend JS
   ════════════════════════════════════════════════════════ */

// ── Modal helpers ─────────────────────────────────────────────
function showModal(id) {
  const el = document.getElementById(id);
  if (el) { el.style.display = 'flex'; document.body.style.overflow = 'hidden'; }
}

function hideModal(id) {
  const el = document.getElementById(id);
  if (el) { el.style.display = 'none'; document.body.style.overflow = ''; }
}

// Close modal on backdrop click
document.addEventListener('click', function (e) {
  if (e.target.classList.contains('modal')) {
    e.target.style.display = 'none';
    document.body.style.overflow = '';
  }
});

// Close modal on Escape key
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal').forEach(m => {
      m.style.display = 'none';
      document.body.style.overflow = '';
    });
  }
});

// ── Auto-dismiss flash alerts after 5 seconds ─────────────────
document.addEventListener('DOMContentLoaded', function () {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = 'opacity .4s';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });
});

// ── Solver option card highlight ──────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  const radios = document.querySelectorAll('.solver-option input[type=radio]');
  radios.forEach(function (r) {
    r.addEventListener('change', function () {
      document.querySelectorAll('.solver-option').forEach(o => o.classList.remove('selected'));
      r.closest('.solver-option').classList.add('selected');
      const tl = document.getElementById('timeLimitGroup');
      if (tl) tl.style.display = r.value === 'cpsat' ? 'block' : 'none';
    });
  });
});

// ── Table search / filter ──────────────────────────────────────
function filterTable(inputId, tableId) {
  const val = document.getElementById(inputId).value.toLowerCase();
  const rows = document.querySelectorAll(`#${tableId} tbody tr`);
  rows.forEach(r => {
    r.style.display = r.textContent.toLowerCase().includes(val) ? '' : 'none';
  });
}

// ── Confirm delete helper (used inline via onsubmit) ──────────
function confirmDelete(msg) {
  return confirm(msg || 'Are you sure you want to delete this item?');
}

// ── Timetable cell tooltip on hover ───────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.cell-filled').forEach(cell => {
    cell.setAttribute('title', cell.textContent.trim().replace(/\s+/g, ' • '));
  });
});

// ── Stats refresh via JSON API ────────────────────────────────
function refreshStats() {
  fetch('/api/stats')
    .then(r => r.json())
    .then(data => {
      Object.entries(data).forEach(([k, v]) => {
        const el = document.getElementById('stat-' + k);
        if (el) el.textContent = v;
      });
    })
    .catch(() => {});
}

// ── Password visibility toggle ────────────────────────────────
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';

  const eyeIcon = btn.querySelector('.eye-icon');
  const eyeOffIcon = btn.querySelector('.eye-off-icon');
  if (eyeIcon && eyeOffIcon) {
    eyeIcon.style.display = isPassword ? 'none' : 'inline-block';
    eyeOffIcon.style.display = isPassword ? 'inline-block' : 'none';
    btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
    btn.setAttribute('title', isPassword ? 'Hide password' : 'Show password');
  }
}
