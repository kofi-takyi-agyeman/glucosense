// ── Config ───────────────────────────────────────────────────────
const API_BASE = "http://localhost:5000/api";

// ── Theme ─────────────────────────────────────────────────────────
const Theme = {
  init() {
    const saved = localStorage.getItem("gs_theme") || "light";
    document.documentElement.setAttribute("data-theme", saved);
  },
  toggle() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("gs_theme", next);
  },
  get() {
    return document.documentElement.getAttribute("data-theme") || "light";
  }
};
Theme.init();

// ── Auth helpers ─────────────────────────────────────────────────
const Auth = {
  getToken:  ()         => localStorage.getItem("gs_token"),
  getUser:   ()         => JSON.parse(localStorage.getItem("gs_user") || "null"),
  setSession: (token, user) => {
    localStorage.setItem("gs_token", token);
    localStorage.setItem("gs_user", JSON.stringify(user));
  },
  clearSession: () => {
    localStorage.removeItem("gs_token");
    localStorage.removeItem("gs_user");
  },
  isLoggedIn: () => !!localStorage.getItem("gs_token"),
  requireAuth: () => {
    if (!localStorage.getItem("gs_token")) window.location.href = "../pages/login.html";
  },
};

// ── API fetch wrapper ─────────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  const token = Auth.getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  try {
    const res  = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) { Auth.clearSession(); window.location.href = "../pages/login.html"; return null; }
    if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
    return data;
  } catch (err) {
    if (err.message?.includes("Failed to fetch"))
      Toast.error("Unable to reach the server. Please ensure the backend is running.");
    throw err;
  }
}

async function apiUpload(endpoint, formData) {
  const token = Auth.getToken();
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res  = await fetch(`${API_BASE}${endpoint}`, { method: "POST", headers, body: formData });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
  return data;
}

// ── Toast ─────────────────────────────────────────────────────────
const Toast = {
  show(msg, type = "info") {
    let c = document.getElementById("toast-container");
    if (!c) { c = document.createElement("div"); c.id = "toast-container"; document.body.appendChild(c); }
    const ICONS = {
      success: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
      error:   `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
      info:    `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
    };
    const t = document.createElement("div");
    t.className = `toast ${type}`;
    t.innerHTML = `<span class="toast-icon">${ICONS[type] || ICONS.info}</span><span class="toast-msg">${msg}</span>`;
    c.appendChild(t);
    setTimeout(() => { t.style.animation = "toast-out .3s ease forwards"; setTimeout(() => t.remove(), 300); }, 3500);
  },
  success: m => Toast.show(m, "success"),
  error:   m => Toast.show(m, "error"),
  info:    m => Toast.show(m, "info"),
};

// ── Icons ─────────────────────────────────────────────────────────
const NAV_ICONS = {
  dashboard:         `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>`,
  assessment:        `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
  records:           `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`,
  "kidney-assessment": `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2C8.5 2 6 6 6 10c0 5.25 6 12 6 12s6-6.75 6-12c0-4-2.5-8-6-8z"/><circle cx="12" cy="10" r="2.5"/></svg>`,
  "kidney-records":    `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2C8.5 2 6 6 6 10c0 5.25 6 12 6 12s6-6.75 6-12c0-4-2.5-8-6-8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
  reports:           `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`,
  tips:              `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  profile:           `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
};

// ── Sidebar ───────────────────────────────────────────────────────
function buildSidebar(activePage) {
  const user = Auth.getUser();
  const navItems = [
    { id: "dashboard",          label: "Dashboard",             href: "dashboard.html"          },
    { divider: "Diabetes" },
    { id: "assessment",         label: "Diabetes Assessment",   href: "assessment.html"         },
    { id: "records",            label: "Diabetes History",      href: "records.html"            },
    { divider: "Kidney Disease" },
    { id: "kidney-assessment",  label: "Kidney Assessment",     href: "kidney-assessment.html"  },
    { id: "kidney-records",     label: "Kidney History",        href: "kidney-records.html"     },
    { divider: "General" },
    { id: "reports",            label: "Medical Documents",     href: "reports.html"            },
    { id: "tips",               label: "Clinical Guidelines",   href: "tips.html"               },
    { id: "profile",            label: "Account Settings",      href: "profile.html"            },
  ];

  const initials = user?.full_name
    ? user.full_name.trim().split(/\s+/).map(n => n[0]).join("").slice(0, 2).toUpperCase()
    : "GS";

  const el = document.querySelector(".sidebar");
  if (!el) return;

  el.innerHTML = `
    <!-- Logo -->
    <div style="padding:20px 18px 16px;border-bottom:1px solid var(--border-sub);display:flex;align-items:center;gap:11px">
      <div style="width:34px;height:34px;border-radius:9px;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,rgba(14,165,233,.12),rgba(16,185,129,.08));border:1px solid rgba(14,165,233,.2)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
      </div>
      <div>
        <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.95rem;background:linear-gradient(135deg,#0ea5e9,#10b981);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">GlucoSense</div>
        <div style="font-size:.58rem;color:var(--muted2);letter-spacing:.1em;text-transform:uppercase;margin-top:1px">Clinical Platform</div>
      </div>
    </div>

    <!-- Nav -->
    <nav style="flex:1;padding:14px 10px;display:flex;flex-direction:column;gap:1px;overflow-y:auto">
      ${navItems.map(item => {
        if (item.divider) {
          return `<div style="font-size:.6rem;font-weight:700;color:var(--muted2);letter-spacing:.12em;text-transform:uppercase;padding:10px 10px 5px;margin-top:4px">${item.divider}</div>`;
        }
        const active = activePage === item.id;
        const isKidney = item.id.startsWith("kidney");
        const activeColor = isKidney ? '#a855f7' : '#0ea5e9';
        const activeBg    = isKidney ? 'rgba(168,85,247,.08)' : 'rgba(14,165,233,.08)';
        const activeBorder= isKidney ? 'rgba(168,85,247,.15)' : 'rgba(14,165,233,.15)';
        const activeGrad  = isKidney ? 'linear-gradient(to bottom,#7c3aed,#a855f7)' : 'linear-gradient(to bottom,#0ea5e9,#10b981)';
        return `
        <a href="${item.href}" style="
          display:flex;align-items:center;gap:10px;
          padding:9px 11px;border-radius:8px;
          font-size:.835rem;font-weight:500;
          text-decoration:none;position:relative;
          transition:background .15s,color .15s;
          color:${active ? activeColor : 'var(--muted)'};
          background:${active ? activeBg : 'transparent'};
          border:1px solid ${active ? activeBorder : 'transparent'};
        " onmouseover="if(!this.dataset.active)this.style.background='var(--subtle)'" onmouseout="this.style.background='${active ? activeBg : 'transparent'}'" data-active="${active}">
          ${active ? `<span style="position:absolute;left:0;top:22%;bottom:22%;width:2.5px;background:${activeGrad};border-radius:0 2px 2px 0"></span>` : ''}
          <span style="width:16px;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:${active ? activeColor : 'var(--muted2)'}">${NAV_ICONS[item.id] || ''}</span>
          <span>${item.label}</span>
        </a>`;
      }).join("")}
    </nav>

    <!-- User pill -->
    <div style="padding:10px;border-top:1px solid var(--border-sub)">
      <div onclick="window.location.href='profile.html'" style="display:flex;align-items:center;gap:9px;padding:9px 10px;border-radius:8px;cursor:pointer;background:var(--subtle);border:1px solid var(--border-sub);transition:background .15s;margin-bottom:6px" onmouseover="this.style.background='var(--hover)'" onmouseout="this.style.background='var(--subtle)'">
        <div style="width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#0ea5e9,#10b981);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.75rem;color:#fff;flex-shrink:0">${initials}</div>
        <div style="flex:1;min-width:0">
          <div style="font-size:.82rem;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${user?.full_name || "Patient"}</div>
          <div style="font-size:.68rem;color:var(--muted2);margin-top:1px">Patient Account</div>
        </div>
      </div>
      <button onclick="logout()" style="width:100%;display:flex;align-items:center;justify-content:center;gap:7px;padding:8px;border-radius:7px;background:transparent;border:1px solid var(--border);color:var(--muted2);font-size:.8rem;font-weight:500;cursor:pointer;font-family:'DM Sans',sans-serif;transition:all .15s" onmouseover="this.style.background='rgba(239,68,68,.07)';this.style.color='#ef4444';this.style.borderColor='rgba(239,68,68,.2)'" onmouseout="this.style.background='transparent';this.style.color='var(--muted2)';this.style.borderColor='var(--border)'">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Sign Out
      </button>
    </div>
  `;
}

function logout() {
  Auth.clearSession();
  window.location.href = "login.html";
}

// ── Mobile sidebar + Theme toggle ─────────────────────────────────
(function setupUI() {
  document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.querySelector(".sidebar");
    const topbar  = document.querySelector(".topbar");
    if (!sidebar || !topbar) return;

    // Mobile overlay
    const overlay = document.createElement("div");
    overlay.className = "sidebar-overlay";
    document.body.appendChild(overlay);

    // Mobile hamburger
    const btn = document.createElement("button");
    btn.className = "mobile-toggle";
    btn.setAttribute("aria-label", "Toggle navigation");
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;
    topbar.prepend(btn);

    const open  = () => { sidebar.classList.add("open"); overlay.classList.add("visible"); };
    const close = () => { sidebar.classList.remove("open"); overlay.classList.remove("visible"); };
    btn.addEventListener("click", () => sidebar.classList.contains("open") ? close() : open());
    overlay.addEventListener("click", close);

    // Theme toggle button
    const themeBtn = document.createElement("button");
    themeBtn.className = "theme-toggle";
    themeBtn.title = "Toggle light / dark mode";
    themeBtn.setAttribute("aria-label", "Toggle theme");
    themeBtn.innerHTML = `
      <svg class="icon-moon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
      </svg>
      <svg class="icon-sun" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
      </svg>`;
    themeBtn.onclick = () => Theme.toggle();
    topbar.appendChild(themeBtn);
  });
}());

// ── Helpers ───────────────────────────────────────────────────────
function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function riskBadge(level) {
  const cfg = {
    Low:      { bg: "rgba(16,185,129,.1)",  color: "#059669", border: "rgba(16,185,129,.2)"  },
    Moderate: { bg: "rgba(245,158,11,.1)",  color: "#d97706", border: "rgba(245,158,11,.2)"  },
    High:     { bg: "rgba(239,68,68,.1)",   color: "#dc2626", border: "rgba(239,68,68,.2)"   },
  };
  const c = cfg[level] || cfg.Low;
  return `<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;font-size:.72rem;font-weight:600;background:${c.bg};color:${c.color};border:1px solid ${c.border}"><span style="width:5px;height:5px;border-radius:50%;background:${c.color};display:inline-block;flex-shrink:0"></span>${level}</span>`;
}

function formatFileSize(bytes) {
  if (bytes < 1024)    return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}
