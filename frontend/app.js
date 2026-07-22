const state = {
  catalogs: {}, vessels: [], declarations: [], crew: [],
  declarationFilter: {}, declarationPage: 1, declarationPaging: null, vesselPage: 1, vesselPageSize: 15, dashboardCertificateWarnings: 0, editingVessel: null, editingDeclaration: null, editingCrew: null, workflowDeclaration: null,
  wizardStep: 1, wizardMaxStep: 1, declarationVesselMode: 'existing', declarationNewCrew: [],
  pendingImport: null, importResultTarget: 'main',
  importMode: 'operational', historicalImport: null, historicalPreviewPage: 1,
  historicalRowFilter: 'all', historicalBatch: [],
  historicalHistoryPage: 1, historicalHistory: [], historicalRegisterItems: [],
  portRegisterItems: [], portRegisterStats: {}, portRegisterPage: 1, portRegisterPageSize: 15,
  portRegisterSelected: new Set(), vesselSaveContext: 'customer-record',
  dashboardSearchSequence: 0,
  analyticsSource: 'live',
  reportingUnits: [], activeReportingUnitId: null, reportingUnitOrganizations: [],
  users: [], organizations: [], editingOrganization: null,
};
const CREW_ROLES = ['Thuyền trưởng', 'Máy trưởng', 'Thuyền viên', 'Thuyền phó'];

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value = '') => String(value ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const number = value => Number(value || 0);
const fmtDate = value => value ? new Intl.DateTimeFormat('vi-VN', {dateStyle:'short', timeStyle: value.includes('T') ? 'short' : undefined}).format(new Date(value)) : '—';

// Base path the app is mounted under ('' at root, '/quanlyxalan' behind the
// ttport.vn reverse proxy). Derived from <base href> so the same build works in both.
const API_BASE = new URL('.', document.baseURI).pathname.replace(/\/$/, '');

async function api(path, options = {}) {
  const token = localStorage.getItem('token');
  if (token) {
    options.headers = { ...options.headers, 'Authorization': `Bearer ${token}` };
  }
  if (state.activeReportingUnitId && ['PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role)) {
    options.headers = { ...options.headers, 'X-Reporting-Unit-ID': String(state.activeReportingUnitId) };
  }
  const response = await fetch(API_BASE + path, options);
  if (response.status === 401 && path !== '/api/auth/login') {
    showLoginDialog('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
    throw new Error('Vui lòng đăng nhập.');
  }
  const type = response.headers.get('content-type') || '';
  const body = type.includes('json') ? await response.json() : await response.blob();
  if (!response.ok) {
    const details = body?.detail || body?.error;
    const message = Array.isArray(details)
      ? details.map(item => item?.msg || String(item)).join('; ')
      : (details && typeof details === 'object' ? details.message : details) || 'Yêu cầu không thành công.';
    const error = new Error(message);
    error.status = response.status;
    error.details = details;
    throw error;
  }
  return body;
}

function toast(message, error = false) {
  const node = document.createElement('div');
  node.className = `toast${error ? ' error' : ''}`;
  node.setAttribute('role', error ? 'alert' : 'status');
  node.textContent = message;
  $('#toast-region').append(node);
  setTimeout(() => node.remove(), 4200);
}

function setSubmitting(form, submitter, pending, pendingLabel = 'Đang xử lý…') {
  form.setAttribute('aria-busy', String(pending));
  $$('button[type="submit"]', form).forEach(button => {
    if (pending) {
      button.dataset.label = button.textContent;
      button.disabled = true;
    } else {
      button.disabled = false;
      if (button.dataset.label) button.textContent = button.dataset.label;
      delete button.dataset.label;
    }
  });
  if (pending && submitter) submitter.textContent = pendingLabel;
}

function setLoginFeedback(message = '') {
  const feedback = $('#login-feedback');
  feedback.hidden = !message;
  feedback.textContent = message;
}

function showLoginDialog(message = '') {
  setLoginFeedback(message);
  const dialog = $('#login-dialog');
  if (!dialog.open) dialog.showModal();
  requestAnimationFrame(() => $('input[name="username"]', dialog)?.focus());
}

function bindLoginForm() {
  const form = $('#login-form');
  if (!form || form.dataset.bound === 'true') return;
  form.dataset.bound = 'true';
  form.addEventListener('submit', async event => {
    event.preventDefault();
    setLoginFeedback();
    if (!form.reportValidity()) return;
    setSubmitting(form, event.submitter, true, 'Đang xác thực…');
    try {
      const result = await api('/api/auth/login', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(values(form)),
      });
      localStorage.setItem('token', result.access_token);
      state.activeReportingUnitId = null;
      $('#login-dialog').close();
      toast('Đăng nhập thành công.');
      init();
    } catch (error) {
      setLoginFeedback(error.message || 'Không thể đăng nhập. Vui lòng thử lại.');
    } finally { setSubmitting(form, event.submitter, false); }
  });
}

function optionList(items = [], selected = '') {
  // Giá trị đang lưu trong CSDL nhưng không có trong danh mục vẫn phải hiển thị,
  // nếu không <select> âm thầm rơi về "Chọn" và người dùng tưởng hồ sơ bị trống.
  const extra = selected && !items.some(item => item === selected)
    ? `<option selected value="${esc(selected)}">${esc(selected)} (ngoài danh mục)</option>`
    : '';
  return `<option value="">Chọn</option>${extra}${items.map(item => `<option ${item === selected ? 'selected' : ''}>${esc(item)}</option>`).join('')}`;
}

const LAYOUT_CLASSES = ['wide-field', 'span-2', 'span-3', 'container-only'];

// Grid-column span classes (wide-field/span-2/span-3) must land on the <label>,
// since it is the actual CSS grid item — placing them on the nested <input>/
// <select> has no layout effect. Other classes (e.g. "derived") stay put.
function splitFieldExtra(extra) {
  const match = extra.match(/class="([^"]*)"/);
  if (!match) return { labelClass: '', inputExtra: extra };
  const classes = match[1].split(/\s+/).filter(Boolean);
  const layoutClasses = classes.filter(c => LAYOUT_CLASSES.includes(c));
  const inputClasses = classes.filter(c => !LAYOUT_CLASSES.includes(c));
  const labelClass = layoutClasses.length ? ` class="${layoutClasses.join(' ')}"` : '';
  const inputExtra = extra.replace(match[0], inputClasses.length ? `class="${inputClasses.join(' ')}"` : '').trim();
  return { labelClass, inputExtra };
}

function field(name, label, value = '', type = 'text', extra = '') {
  const required = extra.includes('required');
  const { labelClass, inputExtra } = splitFieldExtra(extra);
  return `<label${labelClass}>${required ? '* ' : ''}${label}<input name="${name}" type="${type}" value="${esc(value)}" ${inputExtra}></label>`;
}

function selectField(name, label, items, value = '', extra = '') {
  const required = extra.includes('required');
  const { labelClass, inputExtra } = splitFieldExtra(extra);
  return `<label${labelClass}>${required ? '* ' : ''}${label}<select name="${name}" ${inputExtra}>${optionList(items, value)}</select></label>`;
}

// Cụm chọn ngày + giờ + phút (bước 15') thay cho datetime-local, để chọn giờ/phút
// bằng dropdown thay vì gõ tay. Giá trị canonical "YYYY-MM-DDTHH:MM" nằm trong một
// input ẩn cùng name (eta/etd/...) nên phần thu thập & backend không đổi.
const MINUTE_STEP = 15;

function splitDateTime(value = '') {
  const match = String(value || '').match(/^(\d{4}-\d{2}-\d{2})[T ]?(\d{2}):(\d{2})/);
  if (!match) return { date: '', hour: '', minute: '' };
  // Làm tròn phút về bước gần nhất để khớp danh sách dropdown.
  const minute = String(Math.round(Number(match[3]) / MINUTE_STEP) * MINUTE_STEP % 60).padStart(2, '0');
  return { date: match[1], hour: match[2], minute };
}

function dateTimeField(name, label, value = '', extra = '') {
  const required = extra.includes('required');
  const { labelClass } = splitFieldExtra(extra);
  const { date, hour, minute } = splitDateTime(value);
  const hourOptions = Array.from({ length: 24 }, (_, h) => {
    const hh = String(h).padStart(2, '0');
    return `<option value="${hh}" ${hh === hour ? 'selected' : ''}>${hh}</option>`;
  }).join('');
  const minuteOptions = Array.from({ length: 60 / MINUTE_STEP }, (_, i) => {
    const mm = String(i * MINUTE_STEP).padStart(2, '0');
    return `<option value="${mm}" ${mm === minute ? 'selected' : ''}>${mm}</option>`;
  }).join('');
  return `<label${labelClass}>${required ? '* ' : ''}${label}
    <span class="datetime-field" data-dt-group="${name}">
      <input type="hidden" name="${name}" value="${esc(value)}">
      <input type="date" class="datetime-date" data-dt-part="date" data-dt-name="${name}" value="${date}" ${required ? 'required' : ''} aria-label="${esc(label)} — ngày">
      <select class="datetime-hour" data-dt-part="hour" data-dt-name="${name}" aria-label="${esc(label)} — giờ">${hourOptions}</select>
      <span class="datetime-sep" aria-hidden="true">:</span>
      <select class="datetime-minute" data-dt-part="minute" data-dt-name="${name}" aria-label="${esc(label)} — phút">${minuteOptions}</select>
    </span></label>`;
}

function syncDateTimeHidden(name, root = document) {
  const group = $(`.datetime-field[data-dt-group="${name}"]`, root);
  if (!group) return;
  const hidden = $('input[type="hidden"]', group);
  const date = $('[data-dt-part="date"]', group).value;
  const hour = $('[data-dt-part="hour"]', group).value || '00';
  const minute = $('[data-dt-part="minute"]', group).value || '00';
  // Chỉ có giá trị khi đã chọn ngày; giờ/phút mặc định 00:00 nếu bỏ trống.
  hidden.value = date ? `${date}T${hour}:${minute}` : '';
}

function bindDateTimeFields(root = document) {
  $$('.datetime-field', root).forEach(group => {
    const name = group.dataset.dtGroup;
    $$('[data-dt-part]', group).forEach(control => {
      control.addEventListener('change', () => syncDateTimeHidden(name, root));
      control.addEventListener('input', () => syncDateTimeHidden(name, root));
    });
  });
}

function values(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function pageName(route) {
  return ({dashboard:'Tổng quan khai báo', declarations:'Phiếu khai báo', vessels:'Hồ sơ phương tiện', 'port-register':'Sổ theo dõi Salan', crew:'Danh sách thuyền viên', import:'Import dữ liệu', reports:'Báo cáo hoạt động', organizations:'Thông tin khách hàng', users:'Quản lý người dùng', settings:'Cài đặt'})[route] || 'Tổng quan khai báo';
}

function roleLabel(role) {
  return ({CUSTOMER:'User', PORT_STAFF:'Port staff', PLATFORM_ADMIN:'Platform admin'})[role] || role;
}

function reportingUnitStorageKey() {
  return `reporting-unit:${state.currentUser?.username || 'anonymous'}`;
}

async function saveReportingUnit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  setSubmitting(form, event.submitter, true, 'Đang tạo…');
  try {
    const item = await api('/api/reporting-units', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(values(form)),
    });
    localStorage.setItem(reportingUnitStorageKey(), String(item.id));
    $('#reporting-unit-dialog').close();
    toast(`Đã tạo đơn vị ${item.name}.`);
    location.reload();
  } catch (error) {
    toast(error.message, true);
  } finally { setSubmitting(form, event.submitter, false); }
}

async function loadReportingUnitContext() {
  const context = $('#sidebar-unit-context');
  const trigger = $('#reporting-unit-trigger');
  const menu = $('#reporting-unit-menu');
  const notice = $('#reporting-unit-required');
  const needsUnit = ['PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role);
  context.hidden = !needsUnit;
  notice.hidden = true;
  document.body.classList.remove('tenant-context-blocked');
  if (!needsUnit) return true;

  const response = await api('/api/reporting-units');
  state.reportingUnits = response.items || [];
  const saved = Number(localStorage.getItem(reportingUnitStorageKey()) || 0);
  const validSaved = state.reportingUnits.some(item => item.id === saved);
  if (validSaved) state.activeReportingUnitId = saved;
  else if (state.currentUser.role === 'PORT_STAFF' && state.reportingUnits.length === 1) {
    state.activeReportingUnitId = state.reportingUnits[0].id;
    localStorage.setItem(reportingUnitStorageKey(), String(state.activeReportingUnitId));
  } else {
    state.activeReportingUnitId = null;
    localStorage.removeItem(reportingUnitStorageKey());
  }

  const chooseReportingUnit = next => {
    state.portRegisterSelected.clear();
    state.editingVessel = state.editingDeclaration = state.editingCrew = null;
    if (next) localStorage.setItem(reportingUnitStorageKey(), String(next));
    else localStorage.removeItem(reportingUnitStorageKey());
    location.reload();
  };
  const unitItems = state.reportingUnits.length
    ? state.reportingUnits.map(unit => `<button type="button" role="menuitemradio" aria-checked="${unit.id === state.activeReportingUnitId}" data-reporting-unit-id="${unit.id}" class="${unit.id === state.activeReportingUnitId ? 'selected' : ''}"><span><strong>${esc(unit.name)}</strong></span><b aria-hidden="true">${unit.id === state.activeReportingUnitId ? '✓' : ''}</b></button>`).join('')
    : '<p>Chưa có đơn vị được cấp.</p>';
  const createAction = state.currentUser.role === 'PLATFORM_ADMIN'
    ? '<div class="reporting-unit-create-action"><button id="create-reporting-unit" type="button" role="menuitem"><span><strong>+ Tạo đơn vị mới</strong></span></button></div>'
    : '';
  menu.innerHTML = unitItems + createAction;
  $$('[data-reporting-unit-id]', menu).forEach(button => {
    button.onclick = () => chooseReportingUnit(Number(button.dataset.reportingUnitId));
  });
  const createButton = $('#create-reporting-unit');
  if (createButton) createButton.onclick = () => {
    trigger.setAttribute('aria-expanded', 'false');
    menu.hidden = true;
    const form = $('#reporting-unit-form');
    form.reset();
    $('#reporting-unit-dialog').showModal();
    requestAnimationFrame(() => form.elements.name.focus());
  };
  const createForm = $('#reporting-unit-form');
  if (createForm.dataset.bound !== 'true') {
    createForm.dataset.bound = 'true';
    createForm.addEventListener('submit', saveReportingUnit);
    $('#close-reporting-unit-dialog').onclick = () => $('#reporting-unit-dialog').close();
    $('#cancel-reporting-unit-dialog').onclick = () => $('#reporting-unit-dialog').close();
  }
  trigger.onclick = event => {
    event.stopPropagation();
    const open = trigger.getAttribute('aria-expanded') !== 'true';
    trigger.setAttribute('aria-expanded', String(open));
    menu.hidden = !open;
    if (open) $('[role="menuitemradio"], [role="menuitem"]', menu)?.focus();
  };
  trigger.onkeydown = event => {
    if (event.key !== 'Escape') return;
    trigger.setAttribute('aria-expanded', 'false');
    menu.hidden = true;
  };
  menu.onkeydown = event => {
    const items = $$('[role="menuitemradio"], [role="menuitem"]', menu);
    if (event.key === 'Escape') {
      event.preventDefault();
      trigger.setAttribute('aria-expanded', 'false');
      menu.hidden = true;
      trigger.focus();
      return;
    }
    if (!['ArrowUp', 'ArrowDown'].includes(event.key) || !items.length) return;
    event.preventDefault();
    const index = Math.max(0, items.indexOf(document.activeElement));
    const offset = event.key === 'ArrowDown' ? 1 : -1;
    items[(index + offset + items.length) % items.length].focus();
  };
  if (context.dataset.outsideBound !== 'true') {
    context.dataset.outsideBound = 'true';
    document.addEventListener('click', event => {
      if (context.contains(event.target)) return;
      trigger.setAttribute('aria-expanded', 'false');
      menu.hidden = true;
    });
  }

  const active = state.reportingUnits.find(unit => unit.id === state.activeReportingUnitId);
  $('#active-reporting-unit').textContent = active ? active.name : 'Chưa chọn';
  trigger.title = active
    ? `Đơn vị đang chọn: ${active.name}`
    : 'Đơn vị báo cáo';
  trigger.disabled = state.reportingUnits.length === 0 && state.currentUser.role !== 'PLATFORM_ADMIN';
  if (!active) {
    notice.hidden = false;
    notice.querySelector('p:last-child').textContent = state.reportingUnits.length
      ? 'Chưa có đơn vị đang thao tác. Hệ thống không có chế độ xem gộp nhiều cảng.'
      : 'Tài khoản chưa có đơn vị báo cáo hoạt động. Liên hệ Platform Admin để cấp membership.';
    document.body.classList.add('tenant-context-blocked');
    $('#api-state').className = 'state-badge pending';
    $('#api-state').textContent = 'Chọn cảng';
    return false;
  }
  return true;
}

function setSidebarOpen(open) {
  $('.sidebar').classList.toggle('open', open);
  $('#sidebar-backdrop').classList.toggle('visible', open);
}

function route() {
  let name = location.hash.replace('#', '') || 'dashboard';
  if (state.currentUser?.role === 'CUSTOMER' && !['declarations', 'crew', 'settings'].includes(name)) {
    name = 'declarations';
    if (location.hash !== '#declarations') history.replaceState(null, '', `${location.pathname}${location.search}#declarations`);
  }
  $$('.page').forEach(page => page.classList.toggle('active', page.dataset.page === name));
  $$('nav a').forEach(link => link.classList.toggle('active', link.dataset.route === name));
  $('#page-context').textContent = pageName(name);
  setSidebarOpen(false);
  requestAnimationFrame(() => $('#main-content').focus({ preventScroll: true }));
  if (name === 'dashboard') loadDashboard();
  if (name === 'vessels') loadVessels();
  if (name === 'port-register') loadPortRegister();
  if (name === 'declarations') loadDeclarations();
  if (name === 'crew') loadCrew();
  if (name === 'import' && state.importMode === 'historical') loadHistoricalImportHistory();
  if (name === 'reports') {
    loadReportAnalytics($('.period-switch button.active')?.dataset.period || 'month', state.analyticsSource);
    if (state.currentUser?.role === 'PLATFORM_ADMIN') loadIntegration();
  }
  if (name === 'organizations' && state.currentUser?.role === 'PLATFORM_ADMIN') loadOrganizations();
  if (name === 'users' && state.currentUser?.role === 'PLATFORM_ADMIN') loadUsers();
  if (name === 'settings') loadSettings();
}

async function loadDashboard(query = '') {
  $('#main-content').setAttribute('aria-busy', 'true');
  try {
    const data = await api(`/api/dashboard${query ? `?q=${encodeURIComponent(query)}` : ''}`);
    const cards = [
      ['PHƯƠNG TIỆN', data.stats.vessels, 'Hồ sơ đang lưu'],
      ['PHIẾU NHÁP', data.stats.drafts, 'Chờ khách hoàn tất'],
      ['ĐÃ XÁC NHẬN GỬI', data.stats.submitted, 'Đang chờ Cảng xử lý hoặc đã duyệt'],
      ['DỰ KIẾN ĐẾN HÔM NAY', data.stats.arrivingToday, 'Theo ETA đã khai'],
      ['CẢNH BÁO CHỨNG CHỈ', data.stats.certificateWarnings, 'Hết hạn hoặc còn dưới 30 ngày'],
    ];
    $('#stats').innerHTML = cards.map(card => `<article class="stat-card"><p>${card[0]}</p><strong>${card[1]}</strong><small>${card[2]}</small></article>`).join('');
    $('#demo-data-notice').hidden = !data.demo_mode;
    state.dashboardCertificateWarnings = data.stats.certificateWarnings;
    renderNotificationPreferences(state.dashboardCertificateWarnings);
    renderAttentionQueue(data.attention);
    // Technical operations and database backup details remain available through
    // protected APIs, but are not end-user dashboard content (including PLATFORM_ADMIN).
    $('#admin-operations').hidden = true;
    $('#admin-backup').hidden = true;
    $('#recent-table').innerHTML = declarationTable(data.recent);
    renderDashboardMatches(data.matches || []);
  } catch (error) { toast(error.message, true); }
  finally { $('#main-content').setAttribute('aria-busy', 'false'); }
}

async function searchDashboardVessels(query, sequence) {
  try {
    const data = await api(`/api/dashboard?q=${encodeURIComponent(query)}`);
    if (sequence !== state.dashboardSearchSequence) return;
    renderDashboardMatches(data.matches || []);
  } catch (error) {
    if (sequence !== state.dashboardSearchSequence) return;
    renderDashboardMatches([]);
    toast(`Không thể tìm phương tiện: ${error.message}`, true);
  }
}

function renderAttentionQueue(queue) {
  const panel = $('#attention-queue');
  if (!queue?.count) { panel.hidden = true; return; }
  panel.hidden = false;
  $('#attention-title').textContent = `${queue.label} (${queue.count})`;
  $('#attention-content').innerHTML = queue.items.map(item => `<article><div><strong>${esc(item.reference_no)}</strong><small>${esc(item.vessel_name)} · ${workflowLabel(item.workflow_status)}</small></div><span>${item.age_hours === null ? 'Chưa rõ thời gian' : `${item.age_hours} giờ`}</span></article>`).join('');
  $('#attention-open-list').onclick = () => {
    $('#workflow-filter').value = queue.items[0]?.workflow_status || '';
    location.hash = 'declarations';
    applyDeclarationFilters();
  };
}

function renderNotificationPreferences(certificateWarnings = 0) {
  // Chỉ xử lý cảnh báo chứng chỉ ở Tổng quan. Các nút opt-in đã chuyển sang tab
  // Cài đặt (đọc/ghi qua loadSettings/saveMyProfile).
  const prefs = state.currentUser?.notification_preferences || {};
  const inAppOn = prefs.in_app_certificate_reminders !== false;
  const reminder = $('#certificate-reminder');
  if (!reminder) return;
  const showReminder = inAppOn && certificateWarnings > 0;
  reminder.hidden = !showReminder;
  reminder.textContent = showReminder ? `Có ${certificateWarnings} phương tiện có chứng chỉ hết hạn hoặc sắp hết hạn trong 30 ngày.` : '';
}

// ── Tab Cài đặt ──────────────────────────────────────────────────────────────
function loadSettings() {
  const user = state.currentUser;
  if (!user) return;
  const prefs = user.notification_preferences || {};
  // Khối "Thông báo"
  const form = $('#my-profile-form');
  form.elements.full_name.value = user.full_name || '';
  form.elements.email.value = user.email || '';
  $('#in-app-certificate-reminders').checked = prefs.in_app_certificate_reminders !== false;
  $('#email-workflow-updates').checked = prefs.email_workflow_updates === true;
  $('#email-certificate-reminders').checked = prefs.email_certificate_reminders === true;
  // Trạng thái SMTP (chỉ admin)
  const status = $('#settings-email-status');
  if (status) {
    const isAdmin = user.role === 'PLATFORM_ADMIN';
    status.hidden = !isAdmin;
    if (isAdmin) {
      const on = user.email_enabled === true;
      status.textContent = on ? 'Email: đã cấu hình' : 'Email: chưa cấu hình';
      status.className = `state-badge ${on ? 'submitted' : 'pending'}`;
    }
  }
  // Khối "Email chung của Cảng" — cho PORT_STAFF/PLATFORM_ADMIN khi đã chọn đơn vị
  const portPanel = $('#settings-port-panel');
  const canPort = ['PORT_STAFF', 'PLATFORM_ADMIN'].includes(user.role) && state.activeReportingUnitId;
  portPanel.hidden = !canPort;
  if (canPort) {
    const unit = state.reportingUnits.find(u => u.id === state.activeReportingUnitId);
    $('#settings-port-name').textContent = unit ? unit.name : 'Đơn vị đang chọn';
    $('#port-email-form').elements.notify_email.value = unit?.notify_email || '';
  }
  // Cấu hình SMTP + lối tắt quản trị (chỉ admin)
  const isAdmin = user.role === 'PLATFORM_ADMIN';
  $('#settings-admin-shortcuts').hidden = !isAdmin;
  $('#settings-smtp-panel').hidden = !isAdmin;
  if (isAdmin) loadSmtpSettings();
}

async function loadSmtpSettings() {
  try {
    const cfg = await api('/api/admin/smtp');
    const form = $('#smtp-form');
    form.elements.enabled.checked = cfg.enabled === true;
    form.elements.host.value = cfg.host || '';
    form.elements.port.value = cfg.port || 587;
    form.elements.username.value = cfg.username || '';
    form.elements.from.value = cfg.from || '';
    form.elements.use_tls.checked = cfg.use_tls !== false;
    form.elements.password.value = '';
    $('#smtp-password-hint').textContent = cfg.password_set ? 'Đã có mật khẩu — để trống nếu không đổi.' : 'Chưa đặt mật khẩu.';
    // Nếu cấu hình lấy từ .env thì khóa form, hướng dẫn dùng .env.
    const fromEnv = cfg.source === 'env';
    $('#settings-smtp-env-note').hidden = !fromEnv;
    [...form.elements].forEach(el => { el.disabled = fromEnv; });
    if (!$('#smtp-test-to').value) $('#smtp-test-to').value = state.currentUser?.email || '';
  } catch (error) { toast(error.message, true); }
}

async function saveSmtp(event) {
  event.preventDefault();
  const form = event.target;
  setSubmitting(form, event.submitter, true, 'Đang lưu…');
  const payload = {
    enabled: form.elements.enabled.checked,
    host: form.elements.host.value.trim(),
    port: Number(form.elements.port.value) || 587,
    username: form.elements.username.value.trim(),
    from: form.elements.from.value.trim(),
    use_tls: form.elements.use_tls.checked,
  };
  // Chỉ gửi password khi admin nhập mới (để trống = giữ nguyên).
  const pw = form.elements.password.value;
  if (pw) payload.password = pw;
  try {
    const cfg = await api('/api/admin/smtp', {
      method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload),
    });
    toast('Đã lưu cấu hình SMTP.');
    // Cập nhật badge trạng thái email trên trang.
    state.currentUser.email_enabled = cfg.enabled && !!cfg.host && !!cfg.from;
    loadSmtpSettings();
    const status = $('#settings-email-status');
    if (status) { const on = state.currentUser.email_enabled; status.hidden = false; status.textContent = on ? 'Email: đã cấu hình' : 'Email: chưa cấu hình'; status.className = `state-badge ${on ? 'submitted' : 'pending'}`; }
  } catch (error) {
    toast(error.message, true);
  } finally { setSubmitting(form, event.submitter, false); }
}

async function sendSmtpTest() {
  const to = $('#smtp-test-to').value.trim();
  if (!to || !to.includes('@')) return toast('Nhập địa chỉ email hợp lệ để gửi thử.', true);
  const btn = $('#smtp-test-btn');
  btn.disabled = true; const label = btn.textContent; btn.textContent = 'Đang gửi…';
  try {
    const result = await api('/api/admin/smtp/test', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ to }),
    });
    toast(result.detail, !result.sent);
  } catch (error) {
    toast(error.message, true);
  } finally { btn.disabled = false; btn.textContent = label; }
}

async function saveMyProfile(event) {
  event.preventDefault();
  const form = event.target;
  setSubmitting(form, event.submitter, true, 'Đang lưu…');
  const payload = {
    full_name: form.elements.full_name.value.trim(),
    email: form.elements.email.value.trim(),
    in_app_certificate_reminders: $('#in-app-certificate-reminders').checked,
    email_workflow_updates: $('#email-workflow-updates').checked,
    email_certificate_reminders: $('#email-certificate-reminders').checked,
  };
  try {
    const profile = await api('/api/me', {
      method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload),
    });
    state.currentUser = { ...state.currentUser, ...profile };
    renderNotificationPreferences(state.dashboardCertificateWarnings);
    toast('Đã lưu thông báo của bạn.');
  } catch (error) {
    toast(error.message, true);
  } finally { setSubmitting(form, event.submitter, false); }
}

async function savePortEmail(event) {
  event.preventDefault();
  const form = event.target;
  const unit = state.reportingUnits.find(u => u.id === state.activeReportingUnitId);
  if (!unit) return toast('Chưa chọn đơn vị báo cáo.', true);
  setSubmitting(form, event.submitter, true, 'Đang lưu…');
  try {
    const updated = await api(`/api/reporting-units/${unit.id}`, {
      method: 'PUT', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ name: unit.name, code: unit.code, notify_email: form.elements.notify_email.value.trim() }),
    });
    unit.notify_email = updated.notify_email;
    toast(`Đã lưu email cho ${updated.name}.`);
  } catch (error) {
    toast(error.message, true);
  } finally { setSubmitting(form, event.submitter, false); }
}

function renderDashboardMatches(items) {
  const container = $('#dashboard-search-results');
  if (!items.length) { container.innerHTML = ''; return; }
  container.innerHTML = items.map(v => `<article class="search-result-card"><strong>${esc(v.name)}</strong><small>${esc(v.registration_no)} · ${esc(v.vessel_type)}</small><span class="table-badge ${v.certificate_status === 'VALID' ? 'submitted' : 'draft'}">${certificateLabel(v.certificate_status)}</span></article>`).join('');
}

function certificateLabel(status) {
  return ({VALID:'Còn hạn',EXPIRING:'Sắp hết hạn',EXPIRED:'Đã hết hạn',UNKNOWN:'Chưa có hạn'})[status] || 'Chưa có hạn';
}

async function loadVessels() {
  try {
    state.vessels = await api('/api/vessels');
    renderVessels();
  } catch (error) { toast(error.message, true); }
}

function renderVessels() {
  const term = ($('#vessel-search').value || '').toLowerCase();
  const items = state.vessels.filter(v => `${v.name} ${v.registration_no}`.toLowerCase().includes(term));
  const totalPages = Math.max(1, Math.ceil(items.length / state.vesselPageSize));
  state.vesselPage = Math.min(Math.max(1, state.vesselPage), totalPages);
  const offset = (state.vesselPage - 1) * state.vesselPageSize;
  const pageItems = items.slice(offset, offset + state.vesselPageSize);
  // Xóa hồ sơ phương tiện là thao tác không thể hoàn tác — chỉ Platform admin
  // được thấy nút này; Nhân viên Cảng vẫn chỉnh sửa được như trước.
  const canDelete = state.currentUser?.role === 'PLATFORM_ADMIN';
  const deleteButton = v => canDelete ? `<button class="table-icon-button danger-icon" data-delete-vessel="${v.id}" title="Xóa ${esc(v.name)}" aria-label="Xóa ${esc(v.name)}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"></path><path d="M8 6V4h8v2"></path><path d="M19 6l-1 14H6L5 6"></path><path d="M10 11v5M14 11v5"></path></svg></button>` : '';
  $('#vessel-count').textContent = term ? `${items.length} / ${state.vessels.length} phương tiện` : `${items.length} phương tiện`;
  $('#vessel-table').innerHTML = items.length ? `<table class="data-table responsive-table record-table vessel-record-table"><colgroup><col style="width:4%"><col style="width:20%"><col style="width:11%"><col style="width:17%"><col style="width:8%"><col style="width:10%"><col style="width:12%"><col style="width:12%"><col style="width:6%"></colgroup><thead><tr><th>STT</th><th>Phương tiện</th><th>Số đăng ký</th><th>Công dụng</th><th>Cấp PT</th><th>Trọng tải</th><th>Hạn đăng kiểm</th><th>Trạng thái</th><th aria-label="Thao tác"></th></tr></thead><tbody>${pageItems.map((v, index) => `<tr><td data-label="STT">${offset + index + 1}</td><td data-label="Phương tiện"><strong>${esc(v.name)}</strong></td><td data-label="Số đăng ký">${esc(v.registration_no)}</td><td data-label="Công dụng">${esc(v.vessel_type)}</td><td data-label="Cấp PT">${esc(v.vessel_class)}</td><td data-label="Trọng tải">${number(v.deadweight_tons).toLocaleString('vi-VN')} tấn</td><td data-label="Hạn đăng kiểm" class="date-cell">${fmtDate(v.certificate_expiry_date)}</td><td data-label="Trạng thái"><span class="table-badge ${v.certificate_status === 'VALID' ? 'submitted' : 'draft'}">${certificateLabel(v.certificate_status)}</span></td><td data-label="Thao tác" class="action-cell"><button class="table-icon-button" data-edit-vessel="${v.id}" title="Chỉnh sửa ${esc(v.name)}" aria-label="Chỉnh sửa ${esc(v.name)}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"></path></svg></button>${deleteButton(v)}</td></tr>`).join('')}</tbody></table>` : empty('Chưa có phương tiện', 'Thêm hồ sơ hoặc import file Excel mẫu.');
  $('#vessel-pagination').innerHTML = items.length > state.vesselPageSize ? `<span>Trang ${state.vesselPage}/${totalPages}</span><button type="button" class="ghost-button" data-vessel-page="${state.vesselPage - 1}" ${state.vesselPage === 1 ? 'disabled' : ''}>Trước</button><button type="button" class="ghost-button" data-vessel-page="${state.vesselPage + 1}" ${state.vesselPage === totalPages ? 'disabled' : ''}>Sau</button>` : '';
  $$('[data-edit-vessel]').forEach(button => button.onclick = () => openVessel(Number(button.dataset.editVessel)));
  $$('[data-delete-vessel]').forEach(button => button.onclick = () => deleteVessel(Number(button.dataset.deleteVessel)));
  $$('[data-vessel-page]').forEach(button => button.onclick = () => {
    state.vesselPage = Number(button.dataset.vesselPage);
    renderVessels();
    $('#vessel-table').scrollIntoView({behavior: 'smooth', block: 'start'});
  });
}

async function deleteVessel(id) {
  const vessel = state.vessels.find(item => item.id === id);
  const label = vessel ? `${vessel.name} — ${vessel.registration_no}` : `phương tiện #${id}`;
  if (!window.confirm(`Xóa vĩnh viễn hồ sơ ${label}? Thao tác này không thể hoàn tác.`)) return;
  try {
    await api(`/api/vessels/${id}`, {method: 'DELETE'});
    toast(`Đã xóa hồ sơ ${label}.`);
    await loadVessels();
  } catch (error) {
    toast(error.message, true);
  }
}

async function refreshPendingBadge() {
  // Không có email/Teams/push — badge đỏ trên sidebar là tín hiệu chủ động
  // duy nhất để Admin/Nhân viên Cảng biết có phiếu mới cần mở ra duyệt, thay
  // vì phải tự vào đúng trang Tổng quan mới thấy.
  if (!['PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role)) return;
  const badge = $('#declarations-badge');
  if (!badge) return;
  try {
    const result = await api('/api/declarations?workflow_status=PENDING_REVIEW&page=1&page_size=1');
    const count = result.total || 0;
    badge.textContent = count > 99 ? '99+' : String(count);
    badge.hidden = count === 0;
  } catch (_) { /* im lặng — không để lỗi polling nền làm phiền người dùng */ }
}

async function loadDeclarations() {
  try {
    const query = new URLSearchParams(Object.entries({...state.declarationFilter, page: state.declarationPage, page_size: 25, sort: 'updated_at', direction: 'desc'}).filter(([, value]) => value));
    const result = await api(`/api/declarations?${query}`);
    state.declarations = result.items;
    state.declarationPaging = result;
    $('#declaration-count').textContent = `${result.total} phiếu`;
    $('#declaration-table').innerHTML = declarationTable(state.declarations, true);
    renderDeclarationPagination(result);
    $$('[data-edit-declaration]').forEach(button => button.onclick = () => openDeclaration(Number(button.dataset.editDeclaration)));
    $$('[data-workflow]').forEach(button => button.onclick = () => openWorkflow(Number(button.dataset.workflow)));
    $$('[data-delete-declaration]').forEach(button => button.onclick = () => deleteDeclaration(Number(button.dataset.deleteDeclaration)));
  } catch (error) { toast(error.message, true); }
}

async function deleteDeclaration(id) {
  const decl = state.declarations.find(item => item.id === id);
  const label = decl ? `${decl.reference_no} · ${decl.vessel_name}` : `phiếu #${id}`;
  if (!window.confirm(`Xóa vĩnh viễn phiếu ${label}? Thao tác này không thể hoàn tác.`)) return;
  try {
    await api(`/api/declarations/${id}`, {method: 'DELETE'});
    toast(`Đã xóa phiếu ${label}.`);
    await loadDeclarations();
    await loadDashboard();
  } catch (error) {
    toast(error.message, true);
  }
}

function renderDeclarationPagination(result) {
  const container = $('#declaration-pagination');
  if (result.total_pages <= 1) { container.innerHTML = ''; return; }
  container.innerHTML = `<span>Trang ${result.page}/${result.total_pages}</span><button type="button" data-declaration-page="${result.page - 1}" ${result.page <= 1 ? 'disabled' : ''}>Trước</button><button type="button" data-declaration-page="${result.page + 1}" ${result.page >= result.total_pages ? 'disabled' : ''}>Sau</button>`;
  $$('[data-declaration-page]', container).forEach(button => button.onclick = () => {
    state.declarationPage = Number(button.dataset.declarationPage);
    syncDeclarationUrl();
    loadDeclarations();
  });
}

function declarationTable(items = [], editable = false) {
  if (!items.length) return empty('Chưa có phiếu khai báo', 'Tạo phiếu đầu tiên từ một hồ sơ phương tiện.');
  const approvalLegend = '<div class="approval-legend"><strong>Tiến trình duyệt:</strong><span>Xanh = đã xác nhận · Xám = chờ</span></div>';
  // Platform admin có toàn quyền: sửa/xóa phiếu ở MỌI trạng thái, kể cả Đã
  // duyệt (để sửa sai hoặc dọn dữ liệu). Khách/nhân viên Cảng chỉ thao tác được
  // khi phiếu còn ở Nháp/Cần bổ sung.
  const isAdmin = state.currentUser?.role === 'PLATFORM_ADMIN';
  const canDelete = editable && isAdmin;
  const canEditRow = d => isAdmin || ['DRAFT','CHANGES_REQUESTED'].includes(d.workflow_status);
  return `${approvalLegend}<table class="data-table responsive-table"><thead><tr><th>Mã / Loại</th><th>Phương tiện</th><th>Hành trình</th><th>Thời gian</th><th class="approval-heading">Tiến trình</th><th>Trạng thái</th>${editable ? '<th></th>' : ''}</tr></thead><tbody>${items.map(d => `<tr><td data-label="Mã / Loại"><strong>${esc(d.reference_no)}</strong><br><small>${d.movement_type === 'DEPARTURE' ? 'Rời cảng' : 'Vào cảng'}</small></td><td data-label="Phương tiện">${esc(d.vessel_name)}<br><small>${esc(d.registration_no)} · ${esc(d.master_name)}</small></td><td data-label="Hành trình">${esc(d.last_port)} → ${esc(d.working_port)}${d.destination_port ? ` → ${esc(d.destination_port)}` : ''}</td><td data-label="Thời gian">${fmtDate(d.movement_type === 'DEPARTURE' ? d.etd : d.eta)}</td><td data-label="Tiến trình duyệt"><span class="approval-dots">${approvalDot(d.port_approval, 'Cảng')}</span></td><td data-label="Trạng thái"><span class="table-badge ${workflowTone(d.workflow_status)}">${workflowLabel(d.workflow_status)}</span></td>${editable ? `<td data-label="Thao tác">${canEditRow(d) ? `<button data-edit-declaration="${d.id}">Mở phiếu</button> · ` : ''}<button data-workflow="${d.id}">Chi tiết</button>${canDelete ? ` · <button class="danger-link" data-delete-declaration="${d.id}">Xóa</button>` : ''}</td>` : ''}</tr>`).join('')}</tbody></table>`;
}

function approvalDot(status, label) {
  return `<span class="approval ${String(status).toLowerCase()}" aria-hidden="true">${status === 'APPROVED' ? '✓' : ''}</span>`;
}
function workflowLabel(status) { return ({DRAFT:'Nháp',PENDING_REVIEW:'Chờ Cảng xử lý',CHANGES_REQUESTED:'Cần bổ sung',APPROVED:'Đã duyệt'})[status] || status; }
function workflowTone(status) { return status === 'APPROVED' ? 'submitted' : 'draft'; }

async function loadCrew() {
  try {
    state.crew = await api('/api/crew');
    renderCrew();
  } catch (error) { toast(error.message, true); }
}

function renderCrew() {
  const term = ($('#crew-search')?.value || '').toLowerCase();
  const items = state.crew.filter(item => `${item.full_name} ${item.crew_role} ${item.professional_certificate_no}`.toLowerCase().includes(term));
  $('#crew-count').textContent = `${items.length} người`;
  const warnings = state.crew.filter(item => ['EXPIRING','EXPIRED'].includes(item.certificate_status));
  const messages = [];
  if (warnings.length) messages.push(`${warnings.length} chứng chỉ đã hết hạn hoặc sẽ hết hạn trong 30 ngày. Cần rà soát trước khi lập phiếu.`);
  const strip = $('#crew-warning-strip');
  strip.classList.toggle('visible', messages.length > 0);
  strip.textContent = messages.join(' ');
  const canEdit = ['CUSTOMER', 'PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role);
  $('#crew-table').innerHTML = items.length ? `<table class="data-table responsive-table record-table crew-record-table"><thead><tr><th>Họ tên</th><th>Chức danh</th><th>Ngày sinh</th><th>Chứng chỉ</th><th>Thời hạn</th><th>Trạng thái</th>${canEdit ? '<th aria-label="Thao tác"></th>' : ''}</tr></thead><tbody>${items.map(item => `<tr><td data-label="Họ tên"><strong>${esc(item.full_name)}</strong><br><small>${esc(item.phone || '')}</small></td><td data-label="Chức danh">${esc(item.crew_role)}</td><td data-label="Ngày sinh" class="date-cell">${fmtDate(item.birth_date)}</td><td data-label="Chứng chỉ">${esc(item.professional_certificate_type)}<br><small>${esc(item.professional_certificate_no)}</small></td><td data-label="Thời hạn" class="date-cell">${fmtDate(item.certificate_expiry_date)}</td><td data-label="Trạng thái"><span class="table-badge ${item.certificate_status === 'VALID' ? 'submitted' : 'draft'}">${certificateLabel(item.certificate_status)}</span></td>${canEdit ? `<td data-label="Thao tác" class="action-cell"><button class="table-icon-button" data-edit-crew="${item.id}" title="Chỉnh sửa ${esc(item.full_name)}" aria-label="Chỉnh sửa ${esc(item.full_name)}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"></path></svg></button></td>` : ''}</tr>`).join('')}</tbody></table>` : empty('Chưa có danh sách thuyền viên', 'Thêm thuyền trưởng hoặc thuyền viên cùng chứng chỉ chuyên môn.');
  $$('[data-edit-crew]').forEach(button => button.onclick = () => openCrew(Number(button.dataset.editCrew)));
}

async function openCrew(id = null) {
  if (!state.vessels.length) await loadVessels();
  const item = id ? state.crew.find(row => row.id === id) : {};
  state.editingCrew = item || {};
  const needsOrganization = ['PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role);
  const organizationField = needsOrganization ? `<label>* Doanh nghiệp<select name="organization_id" required><option value="">Chọn doanh nghiệp</option>${state.reportingUnitOrganizations.map(org => `<option value="${org.id}" ${Number(item.organization_id) === org.id ? 'selected' : ''}>${esc(org.name)}</option>`).join('')}</select></label>` : '';
  const vesselField = `<label>Phương tiện phụ trách<select name="vessel_id"><option value="">Chưa gán phương tiện</option>${state.vessels.map(v => `<option value="${v.id}" ${Number(item.vessel_id) === v.id ? 'selected' : ''}>${esc(v.name)} — ${esc(v.registration_no)}</option>`).join('')}</select></label>`;
  $('#crew-fields').innerHTML = `
    ${organizationField}
    ${vesselField}
    ${field('full_name','Họ và tên',item.full_name,'text','required')}
    ${selectField('crew_role','Chức danh',CREW_ROLES,item.crew_role,'required')}
    ${field('birth_date','Ngày sinh (không bắt buộc)',item.birth_date,'date')}
    ${field('phone','Số điện thoại',item.phone,'tel','required')}
    ${field('identity_no','CCCD / Hộ chiếu',item.identity_no)}
    ${field('professional_certificate_type','Loại chứng chỉ chuyên môn',item.professional_certificate_type)}
    ${field('professional_certificate_no','Số chứng chỉ',item.professional_certificate_no)}
    ${field('certificate_issue_date','Ngày cấp',item.certificate_issue_date,'date')}
    ${field('certificate_expiry_date','Ngày hết hạn',item.certificate_expiry_date,'date')}
    <label class="span-2">Ghi chú<textarea name="notes">${esc(item.notes || '')}</textarea></label>`;
  $('#crew-dialog').showModal();
}

async function saveCrew(event) {
  event.preventDefault();
  const form = $('#crew-form');
  const data = values(form);
  // "" từ <select> không parse được thành int ở backend — gửi null khi chưa gán phương tiện.
  data.vessel_id = data.vessel_id ? Number(data.vessel_id) : null;
  if (state.editingCrew?.id) {
    data.id = state.editingCrew.id;
    data.version = state.editingCrew.version;
  }
  setSubmitting(form, event.submitter, true, 'Đang lưu…');
  try {
    await api('/api/crew', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    $('#crew-dialog').close();
    toast('Đã lưu thông tin thuyền viên và chứng chỉ.');
    await Promise.all([loadCrew(), loadDashboard()]);
  } catch (error) { toast(error.message, true); }
  finally { setSubmitting(form, event.submitter, false); }
}

function empty(title, text) { return `<div class="empty-state"><div><strong>${title}</strong><p>${text}</p></div></div>`; }

function vesselProfilesHtml() {
  return state.editingVesselProfiles.map((profile, index) => `<div class="operating-profile-row" data-profile-index="${index}">
    ${field('activity_area', 'Vùng hoạt động / Cấp PT', profile.activity_area, 'text', 'required')}
    ${field('profile_deadweight_tons', 'Trọng tải toàn phần (tấn)', profile.deadweight_tons, 'number', 'step="0.01" min="0"')}
    ${field('profile_cargo_capacity_tons', 'Khả năng khai thác (tấn)', profile.cargo_capacity_tons, 'number', 'step="0.01" min="0"')}
    <button type="button" class="table-icon-button remove-profile" data-remove-profile="${index}" aria-label="Xóa vùng hoạt động" ${state.editingVesselProfiles.length === 1 ? 'disabled' : ''}>×</button>
  </div>`).join('');
}

function renderVesselProfiles() {
  const container = $('#operating-profiles');
  if (!container) return;
  container.innerHTML = vesselProfilesHtml();
  $$('[data-remove-profile]', container).forEach(button => button.onclick = () => {
    state.editingVesselProfiles.splice(Number(button.dataset.removeProfile), 1);
    renderVesselProfiles();
  });
}

function openVessel(id = null, portRegister = false) {
  const records = portRegister ? state.portRegisterItems : state.vessels;
  const v = id ? records.find(item => item.id === id) : {};
  state.editingVessel = v || {};
  state.vesselSaveContext = portRegister ? 'port-register' : 'customer-record';
  state.editingVesselProfiles = (v.operating_profiles?.length ? v.operating_profiles : [{
    activity_area: v.vessel_class || '',
    deadweight_tons: v.deadweight_tons ?? '',
    cargo_capacity_tons: v.cargo_capacity_tons ?? '',
  }]).map(profile => ({...profile}));
  $('#vessel-fields').innerHTML = `
    ${field('organization_name','Doanh nghiệp / Chủ phương tiện',v.organization_name || '', 'text', 'required class="span-2"')}
    ${field('name','Tên phương tiện',v.name,'text','required')}
    ${field('registration_no','Số đăng ký',v.registration_no,'text','required')}
    ${field('registry_or_imo','Số đăng kiểm / IMO',v.registry_or_imo)}
    ${field('vessel_type','Công dụng / Loại phương tiện',v.vessel_type,'text','required list="vessel-type-suggestions"')}
    <datalist id="vessel-type-suggestions">${(state.catalogs.vesselTypeSuggestions || []).map(item => `<option value="${esc(item)}">`).join('')}</datalist>
    ${selectField('vessel_category','Phân loại phương tiện (không bắt buộc)',state.catalogs.vesselCategories,v.vessel_category)}
    ${selectField('shell_material','Vật liệu vỏ',state.catalogs.shellMaterials,v.shell_material)}
    ${field('build_year','Năm đóng',v.build_year,'number','min="1800" max="2100"')}
    ${field('length_m','Chiều dài Lmax (m)',v.length_m,'number','step="0.01" min="0"')}
    ${field('width_m','Chiều rộng B (m)',v.width_m,'number','step="0.01" min="0"')}
    ${field('side_height_m','Chiều cao mạn (m)',v.side_height_m,'number','step="0.01" min="0"')}
    ${field('draft_m','Mớn nước đầy tải (m)',v.draft_m,'number','step="0.01" min="0"')}
    ${field('gross_tonnage','Dung tích (GT)',v.gross_tonnage,'number','step="0.01" min="0"')}
    ${field('engine_power_cv','Tổng công suất máy (CV)',v.engine_power_cv,'number','step="0.01" min="0"')}
    ${field('container_capacity_teu','Sức chở container (TEU)',v.container_capacity_teu,'number','step="1" min="0"')}
    ${field('passenger_capacity','Sức chở khách',v.passenger_capacity,'number','min="0"')}
    ${field('min_crew','Định biên thuyền viên tối thiểu',v.min_crew,'number','min="0"')}
    ${field('safety_certificate_no','Số GCN ATKT & BVMT',v.safety_certificate_no)}
    ${field('certificate_issue_date','Ngày cấp GCN',v.certificate_issue_date,'date')}
    ${field('certificate_expiry_date','Ngày hết hạn GCN',v.certificate_expiry_date,'date')}
    ${field('tracking_master_name','Thuyền trưởng theo dõi',v.tracking_master_name)}
    ${field('tracking_master_phone','Số điện thoại liên hệ',v.tracking_master_phone,'tel')}
    <section class="form-section span-3 operating-profiles-section"><div class="panel-header"><div><h3>Vùng hoạt động và năng lực tương ứng</h3><p>Mỗi vùng giữ riêng trọng tải và khả năng khai thác.</p></div><button type="button" class="outline-button" id="add-operating-profile">+ Thêm vùng</button></div><div id="operating-profiles"></div></section>
    <label class="span-3">Ghi chú<textarea name="notes">${esc(v.notes || '')}</textarea></label>`;
  renderVesselProfiles();
  $('#add-operating-profile').onclick = () => {
    state.editingVesselProfiles.push({activity_area: '', deadweight_tons: '', cargo_capacity_tons: ''});
    renderVesselProfiles();
  };
  $('#vessel-dialog').showModal();
}

async function saveVessel(event) {
  event.preventDefault();
  const form = $('#vessel-form');
  const data = values(form);
  data.operating_profiles = $$('.operating-profile-row', form).map((row, index) => ({
    sequence: index + 1,
    activity_area: $('[name="activity_area"]', row).value.trim(),
    deadweight_tons: $('[name="profile_deadweight_tons"]', row).value || null,
    cargo_capacity_tons: $('[name="profile_cargo_capacity_tons"]', row).value || null,
  }));
  const primaryProfile = data.operating_profiles[0] || {};
  data.vessel_class = data.operating_profiles.map(profile => profile.activity_area).filter(Boolean).join(' / ');
  data.deadweight_tons = primaryProfile.deadweight_tons;
  data.cargo_capacity_tons = primaryProfile.cargo_capacity_tons;
  delete data.activity_area;
  delete data.profile_deadweight_tons;
  delete data.profile_cargo_capacity_tons;
  data.organization = {name: data.organization_name};
  delete data.organization_name;
  if (state.editingVessel?.id) {
    data.id = state.editingVessel.id;
    data.version = state.editingVessel.version;
  }
  setSubmitting(form, event.submitter, true, 'Đang lưu…');
  try {
    const path = state.vesselSaveContext === 'port-register' ? '/api/vessels?port_register=true' : '/api/vessels';
    await api(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    $('#vessel-dialog').close();
    toast('Đã lưu hồ sơ phương tiện.');
    await loadVessels();
    if (state.vesselSaveContext === 'port-register') await loadPortRegister();
  } catch (error) { toast(error.message, true); }
  finally { setSubmitting(form, event.submitter, false); }
}

function containerCountTons(prefix, key, label, current) {
  // Một ô gộp: số lượng container (thu nhỏ) + số tấn cho mỗi container, để công
  // thức tự nhân số lượng × số tấn cho Khối lượng.
  return `<label class="container-count-field container-only">${label}
    <span class="count-tons">
      <input name="${prefix}_cont${key}" type="number" min="0" step="1" value="${esc(current[`cont${key}`] ?? '')}" class="count-input" aria-label="${esc(label)} — số lượng" placeholder="SL">
      <span class="count-tons-mult" aria-hidden="true">×</span>
      <input name="${prefix}_tons${key}" type="number" min="0" step="0.01" value="${esc(current[`tons${key}`] ?? '')}" class="tons-input" aria-label="${esc(label)} — số tấn mỗi container" placeholder="tấn">
    </span></label>`;
}

function cargoFields(prefix, title, current = {}, load = false) {
  return `<section class="form-section"><h3>${title}</h3><div class="section-grid">
    ${selectField(`${prefix}_cargo_type`,'Loại hàng',state.catalogs.cargoTypes,current.cargo_type)}
    ${selectField(`${prefix}_movement_type`,'Loại hình',load ? state.catalogs.loadMovements : state.catalogs.unloadMovements,current.movement_type)}
    ${field(`${prefix}_cargo_name`,'Tên hàng',current.cargo_name,'text','class="wide-field"')}
    ${containerCountTons(prefix,'20_full','20ft có hàng',current)}
    ${containerCountTons(prefix,'20_empty','20ft rỗng',current)}
    ${containerCountTons(prefix,'40_full','40ft có hàng',current)}
    ${containerCountTons(prefix,'40_empty','40ft rỗng',current)}
    ${field(`${prefix}_total`,'Tổng container',current.total_containers || 0,'number','readonly class="derived container-only"')}
    ${field(`${prefix}_teu`,'Quy đổi TEU',current.teu || 0,'number','readonly class="derived container-only"')}
    ${field(`${prefix}_empty_teu`,'TEU rỗng',current.empty_teu || 0,'number','readonly class="derived container-only"')}
    ${field(`${prefix}_tons`,'Khối lượng (tấn)',current.tons,'number','min="0" step="0.01"')}
  </div></section>`;
}

function crewForVessel(vesselId) {
  if (!vesselId) return [];
  // Thuyền viên đã gán đúng phương tiện được ưu tiên; nếu chưa có ai được gán thì
  // hiển thị nhóm chưa gán để người dùng vẫn chọn được và bổ sung gán sau.
  const assigned = state.crew.filter(member => Number(member.vessel_id) === Number(vesselId));
  return assigned.length ? assigned : state.crew.filter(member => !member.vessel_id);
}

function crewChecklistHtml(vesselId, selectedIds = []) {
  const heading = '<h4 class="crew-section-heading">Thuyền viên</h4>';
  if (!vesselId) return heading + '<p class="muted">Chọn phương tiện ở bước 1 để tiếp tục chọn thuyền viên cho lượt khai báo.</p>';
  const pool = crewForVessel(vesselId);
  if (!pool.length) return heading + '<p class="muted">Chưa có thuyền viên. Hãy cập nhật Danh sách thuyền viên trước khi tạo phiếu.</p>';
  return heading + `<ul class="crew-checklist" role="group" aria-label="Chọn thuyền viên đi theo phương tiện">${pool.map(member => {
    const isCaptain = member.crew_role.trim().toLowerCase() === 'thuyền trưởng';
    const checked = selectedIds.some(id => Number(id) === member.id);
    return `<li><label class="${isCaptain ? 'crew-captain' : ''}">
      <input type="checkbox" name="crew_ids" value="${member.id}" ${checked ? 'checked' : ''}>
      <span class="crew-name">${esc(member.full_name)}</span>
      ${isCaptain ? '<span class="crew-badge-captain">Thuyền trưởng</span>' : `<span class="crew-role">${esc(member.crew_role)}</span>`}
      <span class="crew-cert table-badge ${member.certificate_status === 'VALID' ? 'submitted' : 'draft'}">${certificateLabel(member.certificate_status)}</span>
    </label></li>`;
  }).join('')}</ul>`;
}

function captainForVessel(vesselId) {
  if (!vesselId) return null;
  const fromCrew = crewForVessel(vesselId).find(member => member.crew_role.trim().toLowerCase() === 'thuyền trưởng');
  if (fromCrew) return fromCrew;
  // Hồ sơ Salan nhập từ Excel lưu Thuyền trưởng ngay trên bản ghi phương tiện
  // (tracking_master_name/phone) chứ không tạo bản ghi trong Danh sách thuyền viên.
  // Không có `id` nên chỉ dùng để tự điền Họ tên / SĐT, không tick được checklist.
  const vessel = state.vessels.find(v => Number(v.id) === Number(vesselId));
  if (vessel?.tracking_master_name) {
    return { id: null, full_name: vessel.tracking_master_name, phone: vessel.tracking_master_phone || '', fromVesselRecord: true };
  }
  return null;
}

function refreshCrewOptions(vesselId) {
  const container = $('#declaration-crew-container');
  if (!container) return;
  const currentlySelected = [...container.querySelectorAll('[name="crew_ids"]:checked')].map(input => Number(input.value));
  const captain = captainForVessel(vesselId);
  if (captain?.id && !currentlySelected.includes(captain.id)) currentlySelected.push(captain.id);
  container.innerHTML = crewChecklistHtml(vesselId, currentlySelected);
  const form = $('#declaration-form');
  // Chỉ ghi đè khi phương tiện có Thuyền trưởng được gán; nếu không, giữ nguyên
  // thông tin người dùng đang nhập tay ở bước 4.
  if (captain) {
    form.elements.master_name.value = captain.full_name || '';
    form.elements.master_phone.value = captain.phone || '';
    state.editingDeclaration.master_name = form.elements.master_name.value;
    state.editingDeclaration.master_phone = form.elements.master_phone.value;
  }
  const summary = $('#assigned-captain');
  if (summary) summary.textContent = captain
    ? `Tự điền từ Danh sách thuyền viên: ${captain.full_name}. Sửa trực tiếp nếu thông tin chưa đúng.`
    : 'Chưa gán Thuyền trưởng cho phương tiện này — nhập trực tiếp Họ tên và Số điện thoại.';
}

const DECLARATION_STEPS = [
  { label: 'Phương tiện' },
  { label: 'Hành trình' },
  { label: 'Hàng hóa' },
  { label: 'Thuyền trưởng & thuyền viên' },
  { label: 'Đính kèm' },
  { label: 'Xem lại & Gửi' },
];

function newCrewRowTemplate(role = 'Thuyền viên') {
  return { full_name: '', crew_role: role, phone: '', professional_certificate_type: '', professional_certificate_no: '', certificate_expiry_date: '' };
}

async function openDeclaration(id = null) {
  if (!state.vessels.length) await loadVessels();
  if (!state.crew.length) await loadCrew();
  const draft = localStorage.getItem('tanthuan-declaration-draft');
  const existing = id ? state.declarations.find(item => item.id === id) : (draft ? JSON.parse(draft) : {});
  state.editingDeclaration = existing || {};
  state.wizardStep = 1;
  state.wizardMaxStep = 1;
  state.declarationVesselMode = 'existing';
  state.declarationNewCrew = [newCrewRowTemplate('Thuyền trưởng')];
  renderDeclarationWizard();
  const fieldsContainer = $('#declaration-fields');
  if (fieldsContainer.dataset.autosaveBound !== 'true') {
    fieldsContainer.dataset.autosaveBound = 'true';
    fieldsContainer.addEventListener('input', rememberDraft);
  }
  loadSuggestions();
  $('#declaration-dialog').showModal();
  updateLocalDraftStatus(draft ? localStorage.getItem('tanthuan-declaration-draft-saved-at') : null, Boolean(draft));
}

function applyVesselToForm(vessel) {
  const form = $('#declaration-form');
  const mapping = ['vessel_name:name','registration_no:registration_no','vessel_type:vessel_type','vessel_class:vessel_class','length_m:length_m','deadweight_tons:deadweight_tons','gross_tonnage:gross_tonnage','certificate_expiry_date:certificate_expiry_date','crew_count:min_crew'];
  mapping.forEach(pair => { const [target, source] = pair.split(':'); form.elements[target].value = vessel[source] ?? ''; });
  form.elements.company_name.value = vessel.organization_name || form.elements.company_name.value;
}

async function fillFromVessel(event) {
  const vesselId = Number(event.target.value) || null;
  if (!vesselId) return;
  refreshCrewOptions(vesselId);
  state.vesselSuggestion = null;
  const suggestionBox = $('#vessel-suggestion');
  if (suggestionBox) suggestionBox.innerHTML = '';
  const vessel = state.vessels.find(v => v.id === vesselId);
  if (!vessel) return;
  applyVesselToForm(vessel);
  rememberDraft();
  try {
    const suggestion = await api(`/api/vessels/${vesselId}/suggestions`);
    if (Number($('#declaration-vessel')?.value) === vesselId) renderVesselSuggestion(suggestion);
  } catch (_) {}
}

function renderVesselSuggestion(suggestion) {
  state.vesselSuggestion = suggestion?.available ? suggestion : null;
  const box = $('#vessel-suggestion');
  if (!box) return;
  if (!state.vesselSuggestion) { box.innerHTML = ''; return; }
  const route = [suggestion.last_port, suggestion.working_port, suggestion.destination_port].filter(Boolean).join(' → ');
  box.innerHTML = `<div class="attachment-field"><strong>Gợi ý theo lượt gần nhất (${esc(suggestion.reference_no)})</strong><p>${esc(route)}</p><button type="button" class="outline-button" id="apply-vessel-suggestion">Áp dụng gợi ý</button></div>`;
  $('#apply-vessel-suggestion').onclick = applyVesselSuggestion;
}

function applyVesselSuggestion() {
  const suggestion = state.vesselSuggestion;
  const form = $('#declaration-form');
  if (!suggestion || !form) return;
  ['last_port', 'working_port', 'destination_port'].forEach(field_ => {
    if (suggestion[field_] && form.elements[field_]) form.elements[field_].value = suggestion[field_];
  });
  ['unload', 'load'].forEach(prefix => {
    const data = suggestion[prefix];
    if (!data) return;
    if (data.cargo_type && form.elements[`${prefix}_cargo_type`]) form.elements[`${prefix}_cargo_type`].value = data.cargo_type;
    if (data.movement_type && form.elements[`${prefix}_movement_type`]) form.elements[`${prefix}_movement_type`].value = data.movement_type;
  });
  const crewContainer = $('#declaration-crew-container');
  if (crewContainer && suggestion.crew_ids?.length) {
    [...crewContainer.querySelectorAll('[name="crew_ids"]')].forEach(input => {
      if (suggestion.crew_ids.includes(Number(input.value))) input.checked = true;
    });
  }
  rememberDraft();
  toast('Đã áp dụng gợi ý từ lượt gần nhất.');
}

function captureWizardFormState() {
  const form = $('#declaration-form');
  if (!form) return state.editingDeclaration;
  Object.assign(state.editingDeclaration, values(form));
  if (state.declarationVesselMode === 'existing') {
    state.editingDeclaration.crew_ids = [...form.querySelectorAll('[name="crew_ids"]:checked')].map(input => Number(input.value));
  }
  return state.editingDeclaration;
}

function activeStepFields(step) {
  return $$(`.wizard-step[data-step="${step}"] input, .wizard-step[data-step="${step}"] select, .wizard-step[data-step="${step}"] textarea`, $('#declaration-fields'));
}

function showStepErrors(invalidFields, heading = 'Vui lòng kiểm tra các thông tin sau:') {
  const container = $('#step-error-summary');
  if (!container) return;
  if (!invalidFields.length) { container.hidden = true; return; }
  container.hidden = false;
  container.innerHTML = `<strong>${esc(heading)}</strong><ul>${invalidFields.map(fieldName => `<li>${esc(fieldName)}</li>`).join('')}</ul>`;
  requestAnimationFrame(() => container.focus());
}

function fieldErrorKey(input) {
  const raw = input.name || input.id || `${input.dataset.crewField || 'field'}-${input.dataset.crewRow || '0'}`;
  return raw.replace(/[^a-zA-Z0-9_-]/g, '-');
}

function showFieldError(input, message) {
  input.setAttribute('aria-invalid', 'true');
  const errorId = `field-err-${fieldErrorKey(input)}`;
  input.setAttribute('aria-describedby', errorId);
  let errorEl = document.getElementById(errorId);
  if (!errorEl) {
    errorEl = document.createElement('span');
    errorEl.id = errorId;
    errorEl.className = 'field-error';
    input.closest('label')?.appendChild(errorEl);
  }
  errorEl.textContent = message;
  input.addEventListener('input', () => clearFieldError(input), { once: true });
}

function clearFieldError(input) {
  input.removeAttribute('aria-invalid');
  input.removeAttribute('aria-describedby');
  document.getElementById(`field-err-${fieldErrorKey(input)}`)?.remove();
}

function validateStep(step) {
  const invalid = [];
  let firstInvalid = null;
  for (const el of activeStepFields(step)) {
    if (el.disabled || el.type === 'hidden' || el.hidden) continue;
    if (!el.checkValidity()) {
      if (!firstInvalid) firstInvalid = el;
      const label = el.closest('label')?.childNodes[0]?.textContent?.trim().replace(/^\*\s*/, '') || el.name;
      invalid.push(label);
      showFieldError(el, el.validationMessage || 'Thông tin không hợp lệ.');
    } else {
      clearFieldError(el);
    }
  }
  if (invalid.length) {
    showStepErrors(invalid);
    requestAnimationFrame(() => firstInvalid?.focus());
    return false;
  }
  showStepErrors([]);
  return true;
}

function validateWizardForm() {
  for (let step = 1; step <= DECLARATION_STEPS.length; step += 1) {
    if (!activeStepFields(step).some(el => !el.disabled && el.type !== 'hidden' && !el.hidden && !el.checkValidity())) continue;
    if (state.wizardStep !== step) {
      captureWizardFormState();
      state.wizardStep = step;
      renderDeclarationWizard();
    }
    return validateStep(step);
  }
  return true;
}

function goToWizardStep(next) {
  if (next > state.wizardStep && !validateStep(state.wizardStep)) return;
  captureWizardFormState();
  state.wizardStep = next;
  state.wizardMaxStep = Math.max(state.wizardMaxStep, next);
  renderDeclarationWizard();
}

function wizardNavHtml() {
  const dots = DECLARATION_STEPS.map((step, index) => {
    const num = index + 1;
    const tone = num < state.wizardStep ? 'done' : num === state.wizardStep ? 'active' : 'todo';
    const locked = num > state.wizardMaxStep;
    const current = num === state.wizardStep ? ' aria-current="step"' : '';
    return `<li class="wizard-dot ${tone}"><button type="button" class="wizard-step-button" data-wizard-dot="${num}" aria-label="Bước ${num}: ${esc(step.label)}"${current}${locked ? ' disabled' : ''}><span aria-hidden="true">${num}</span><small>${esc(step.label)}</small></button></li>`;
  }).join('');
  return `<nav class="wizard-progress-wrap" aria-label="Các bước khai báo"><ol class="wizard-progress">${dots}</ol></nav>
    <div class="wizard-nav">
      <button type="button" class="ghost-button" data-wizard-back ${state.wizardStep === 1 ? 'disabled' : ''}>← Quay lại</button>
      <button type="button" class="primary-button" data-wizard-next ${state.wizardStep === DECLARATION_STEPS.length ? 'disabled' : ''}>Tiếp tục →</button>
    </div>`;
}

function newCrewRowsHtml() {
  const rows = state.declarationNewCrew.map((row, index) => `
    <div class="section-grid new-crew-row">
      <label class="wide-field">${index === 0 ? '* Họ và Tên' : 'Họ tên thuyền viên'}<input data-crew-field="full_name" data-crew-row="${index}" value="${esc(row.full_name)}" ${index === 0 ? 'required' : ''}></label>
      ${index === 0
        ? `<input type="hidden" data-crew-field="crew_role" data-crew-row="0" value="Thuyền trưởng">`
        : `<label>Chức danh<select data-crew-field="crew_role" data-crew-row="${index}">${CREW_ROLES.filter(r => r !== 'Thuyền trưởng').map(r => `<option ${row.crew_role === r ? 'selected' : ''}>${r}</option>`).join('')}</select></label>`}
      <label>${index === 0 ? '* Số điện thoại' : 'Số điện thoại'}<input data-crew-field="phone" data-crew-row="${index}" value="${esc(row.phone)}" type="tel" ${index === 0 ? 'required' : ''}></label>
      <label>Loại chứng chỉ chuyên môn<input data-crew-field="professional_certificate_type" data-crew-row="${index}" value="${esc(row.professional_certificate_type)}"></label>
      <label>Số chứng chỉ<input data-crew-field="professional_certificate_no" data-crew-row="${index}" value="${esc(row.professional_certificate_no)}"></label>
      <label>Hạn chứng chỉ<input type="date" data-crew-field="certificate_expiry_date" data-crew-row="${index}" value="${esc(row.certificate_expiry_date)}"></label>
      ${index > 0 ? `<button type="button" class="ghost-button" data-remove-crew-row="${index}">Xóa</button>` : ''}
    </div>`).join('');
  return `${rows}<button type="button" class="outline-button" id="add-new-crew-row">+ Thêm thuyền viên</button>`;
}

function reviewSummaryHtml(d) {
  const isNew = state.declarationVesselMode === 'new';
  const captainName = isNew ? state.declarationNewCrew[0]?.full_name : d.master_name;
  const captainPhone = isNew ? state.declarationNewCrew[0]?.phone : d.master_phone;
  const crewOnboard = Number($('#declaration-form')?.elements?.crew_onboard_count?.value ?? d.crew_onboard_count) || 0;
  const isAdmin = state.currentUser?.role === 'PLATFORM_ADMIN';
  return `<section class="form-section"><h3>F. ${isAdmin ? 'Xem lại & Lưu' : 'Xem lại & Gửi'}</h3><div class="section-grid">
    <div class="attachment-field wide-field"><strong>Phương tiện</strong><p>${esc(d.vessel_name || '')} — ${esc(d.registration_no || '')}${isNew ? ' (hồ sơ mới)' : ''}</p></div>
    <div class="attachment-field wide-field"><strong>Thuyền trưởng</strong><p>${captainName ? `${esc(captainName)}${captainPhone ? ` · ${esc(captainPhone)}` : ''}` : 'Chưa có thông tin'}</p></div>
    <div class="attachment-field"><strong>Thuyền viên đi theo</strong><p>${crewOnboard} người</p></div>
    <div class="attachment-field"><strong>Hành trình</strong><p>${esc(d.last_port || '')} → ${esc(d.working_port || '')}${d.destination_port ? ` → ${esc(d.destination_port)}` : ''}</p></div>
  </div>
  <p class="muted">${isAdmin
    ? 'Kiểm tra kỹ thông tin trước khi lưu phiếu.'
    : 'Kiểm tra kỹ thông tin trước khi bấm “Xác nhận”. Sau khi gửi, thông tin được khóa trong khi Cảng xem xét.'}</p></section>`;
}

async function loadPortRegister() {
  try {
    const data = await api('/api/port-vessel-register');
    state.portRegisterItems = data.items || [];
    state.portRegisterStats = data.stats || {};
    renderPortRegisterStats(data);
  } catch (error) { toast(error.message, true); return; }
  renderPortRegister();
}

async function removePortRegisterItems(ids, label = '') {
  if (!ids.length) return;
  const target = label || `${ids.length} Salan đã chọn`;
  if (!window.confirm(`Gỡ ${target} khỏi sổ theo dõi nội bộ của Cảng? Hồ sơ phương tiện gốc vẫn được giữ lại.`)) return;
  try {
    const result = await api('/api/port-vessel-register/remove', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ids}),
    });
    ids.forEach(id => state.portRegisterSelected.delete(id));
    toast(`Đã gỡ ${result.removed} Salan khỏi sổ theo dõi.`);
    await loadPortRegister();
  } catch (error) {
    toast(error.message, true);
  }
}

function renderPortRegisterStats(data) {
  const stats = data.stats || {};
  const cards = [
    ['SALAN THEO DÕI', stats.vessels || 0, 'Hồ sơ nội bộ của Cảng'],
    ['NĂNG LỰC TẤN', number(stats.tonnageCapacity).toLocaleString('vi-VN'), 'Tổng năng lực đã ghi nhận'],
    ['NĂNG LỰC TEU', number(stats.teuCapacity).toLocaleString('vi-VN'), 'Tổng năng lực đã ghi nhận'],
    ['CẢNH BÁO GCN', stats.certificateWarnings || 0, 'Hết hạn hoặc còn dưới 30 ngày'],
  ];
  $('#port-register-stats').innerHTML = cards.map(card => `<article class="stat-card"><p>${card[0]}</p><strong>${card[1]}</strong><small>${card[2]}</small></article>`).join('');
  const renderBars = (selector, items) => {
    const max = Math.max(...items.map(item => item.value), 1);
    $(selector).innerHTML = items.length ? items.map(item => `<div class="summary-bar"><span>${esc(item.label)}</span><div><i style="width:${Math.max(4, item.value / max * 100)}%"></i></div><strong>${item.value}</strong></div>`).join('') : '<p class="muted">Chưa có dữ liệu.</p>';
  };
  renderBars('#port-register-by-area', data.byArea || []);
  renderBars('#port-register-by-type', data.byType || []);
}

function profileText(vessel, field, fallback = '') {
  const values = (vessel.operating_profiles || []).map(profile => profile[field]).filter(value => value !== null && value !== undefined && value !== '');
  return values.length ? values.map(value => typeof value === 'number' ? value.toLocaleString('vi-VN') : value).join(' / ') : fallback;
}

function renderPortRegister() {
  const input = $('#port-register-search');
  if (!input) return;
  const term = input.value.trim().toLowerCase();
  const items = state.portRegisterItems.filter(v => `${v.name} ${v.registration_no} ${v.tracking_master_name || ''}`.toLowerCase().includes(term));
  const totalPages = Math.max(1, Math.ceil(items.length / state.portRegisterPageSize));
  state.portRegisterPage = Math.min(Math.max(1, state.portRegisterPage), totalPages);
  const offset = (state.portRegisterPage - 1) * state.portRegisterPageSize;
  const pageItems = items.slice(offset, offset + state.portRegisterPageSize);
  const pageIds = pageItems.map(item => item.id);
  const allPageSelected = pageIds.length > 0 && pageIds.every(id => state.portRegisterSelected.has(id));
  const selectedCount = state.portRegisterSelected.size;
  $('#port-register-count').textContent = term ? `${items.length} / ${state.portRegisterItems.length} Salan` : `${items.length} Salan`;
  $('#port-register-selection').hidden = selectedCount === 0;
  $('#port-register-selection').textContent = `Đã chọn ${selectedCount}`;
  $('#remove-selected-port-vessels').hidden = selectedCount === 0;
  $('#port-register-table').innerHTML = items.length ? `<table class="data-table port-register-table"><thead><tr><th class="select-column"><input id="select-port-register-page" type="checkbox" ${allPageSelected ? 'checked' : ''} aria-label="Chọn tất cả Salan trên trang này"></th><th>STT</th><th>Tên phương tiện</th><th>Số đăng ký</th><th>Loại / công dụng</th><th>Vùng hoạt động</th><th>Chiều dài (m)</th><th>Trọng tải toàn phần (tấn)</th><th>Dung tích (m³)</th><th>Khả năng khai thác (tấn)</th><th>Khả năng khai thác (TEU)</th><th>Hạn GCN ATKT & BVMT</th><th>Số thuyền viên</th><th>Thuyền trưởng</th><th>Điện thoại</th><th aria-label="Thao tác"></th></tr></thead><tbody>${pageItems.map((v, index) => `<tr class="${state.portRegisterSelected.has(v.id) ? 'selected-row' : ''}"><td class="select-column"><input type="checkbox" data-select-port-vessel="${v.id}" ${state.portRegisterSelected.has(v.id) ? 'checked' : ''} aria-label="Chọn ${esc(v.name)}"></td><td>${offset + index + 1}</td><td><strong>${esc(v.name)}</strong></td><td>${esc(v.registration_no)}</td><td>${esc(v.vessel_type)}</td><td>${esc(profileText(v, 'activity_area', v.vessel_class))}</td><td>${esc(v.length_m ?? '')}</td><td>${esc(profileText(v, 'deadweight_tons', v.deadweight_tons ?? ''))}</td><td>${esc(v.gross_tonnage ?? '')}</td><td>${esc(profileText(v, 'cargo_capacity_tons', v.cargo_capacity_tons ?? ''))}</td><td>${esc(v.container_capacity_teu ?? '')}</td><td>${fmtDate(v.certificate_expiry_date)}</td><td>${esc(v.min_crew ?? '')}</td><td>${esc(v.tracking_master_name || '')}</td><td>${esc(v.tracking_master_phone || '')}</td><td class="action-cell port-row-actions"><button class="table-icon-button" data-edit-port-vessel="${v.id}" title="Chỉnh sửa ${esc(v.name)}" aria-label="Chỉnh sửa ${esc(v.name)}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"></path></svg></button><button class="table-icon-button danger-icon" data-remove-port-vessel="${v.id}" title="Gỡ ${esc(v.name)} khỏi sổ theo dõi" aria-label="Gỡ ${esc(v.name)} khỏi sổ theo dõi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"></path><path d="M8 6V4h8v2"></path><path d="M19 6l-1 14H6L5 6"></path><path d="M10 11v5M14 11v5"></path></svg></button></td></tr>`).join('')}</tbody></table>` : empty('Chưa có dữ liệu Salan', 'Import file theo dõi hoặc thêm thủ công một Salan.');
  $('#port-register-pagination').innerHTML = items.length > state.portRegisterPageSize ? `<span>Trang ${state.portRegisterPage}/${totalPages}</span><button type="button" class="ghost-button" data-port-register-page="${state.portRegisterPage - 1}" ${state.portRegisterPage === 1 ? 'disabled' : ''}>Trước</button><button type="button" class="ghost-button" data-port-register-page="${state.portRegisterPage + 1}" ${state.portRegisterPage === totalPages ? 'disabled' : ''}>Sau</button>` : '';
  $$('[data-edit-port-vessel]').forEach(button => button.onclick = () => openVessel(Number(button.dataset.editPortVessel), true));
  $$('[data-remove-port-vessel]').forEach(button => button.onclick = () => {
    const id = Number(button.dataset.removePortVessel);
    const vessel = state.portRegisterItems.find(item => item.id === id);
    removePortRegisterItems([id], vessel ? vessel.name : 'Salan này');
  });
  $$('[data-select-port-vessel]').forEach(checkbox => checkbox.onchange = () => {
    const id = Number(checkbox.dataset.selectPortVessel);
    if (checkbox.checked) state.portRegisterSelected.add(id); else state.portRegisterSelected.delete(id);
    renderPortRegister();
  });
  if ($('#select-port-register-page')) $('#select-port-register-page').onchange = event => {
    pageIds.forEach(id => event.target.checked ? state.portRegisterSelected.add(id) : state.portRegisterSelected.delete(id));
    renderPortRegister();
  };
  $$('[data-port-register-page]').forEach(button => button.onclick = () => {
    state.portRegisterPage = Number(button.dataset.portRegisterPage);
    renderPortRegister();
    $('#port-register-table').scrollIntoView({behavior: 'smooth', block: 'start'});
  });
}

function renderDeclarationWizard() {
  const d = state.editingDeclaration;
  const isNew = state.declarationVesselMode === 'new';
  const assignedCaptain = d.vessel_id ? captainForVessel(d.vessel_id) : null;
  // Giá trị người dùng đã sửa (nằm trong editingDeclaration sau captureWizardFormState)
  // được ưu tiên so với hồ sơ gán sẵn, để chỉnh tay không bị ghi đè khi render lại.
  const masterName = isNew ? '' : (d.master_name || assignedCaptain?.full_name || '');
  const masterPhone = isNew ? '' : (d.master_phone || assignedCaptain?.phone || '');

  $('#declaration-fields').innerHTML = `
    ${wizardNavHtml()}
    <div id="step-error-summary" class="step-error-summary" role="alert" tabindex="-1" hidden></div>
    ${isNew ? `<input name="master_name" type="hidden" value="">
    <input name="master_phone" type="hidden" value="">` : ''}
    <div class="wizard-step" data-step="1" ${state.wizardStep === 1 ? '' : 'hidden'}>
      <section class="form-section"><h3>A. Thông tin chung và phương tiện</h3><div class="section-grid">
        <input name="movement_type" type="hidden" value="ARRIVAL">
        ${field('declaration_date','Ngày khai báo',d.declaration_date || new Date().toISOString().slice(0,10),'date','required')}
        ${field('company_name','Tên doanh nghiệp/Chủ phương tiện',d.company_name)}
        <label id="declaration-vessel-label" ${isNew ? 'hidden' : ''}>* Chọn hồ sơ phương tiện<select name="vessel_id" id="declaration-vessel" ${isNew ? '' : 'required'}><option value="">Chọn phương tiện</option>${state.vessels.map(v => `<option value="${v.id}" ${Number(d.vessel_id) === v.id ? 'selected' : ''}>${esc(v.name)} — ${esc(v.registration_no)}</option>`).join('')}</select></label>
        <div id="vessel-suggestion" class="span-full" ${isNew ? 'hidden' : ''}></div>
        <div class="vessel-mode-toggle wide-field" role="radiogroup" aria-label="Nguồn hồ sơ phương tiện">
          <label><input type="radio" name="vessel_mode" value="existing" ${isNew ? '' : 'checked'}> Phương tiện đã có hồ sơ</label>
          <label><input type="radio" name="vessel_mode" value="new" ${isNew ? 'checked' : ''}> Khai phương tiện mới</label>
        </div>
        ${field('vessel_name','Tên phương tiện',d.vessel_name,'text',isNew ? 'required' : 'required readonly class="locked-field"')}
        ${field('registration_no','Số đăng ký',d.registration_no,'text',isNew ? 'required' : 'required readonly class="locked-field"')}
        ${field('vessel_type','Công dụng / Loại phương tiện',d.vessel_type,'text',isNew ? 'required list="vessel-type-suggestions"' : 'required readonly class="locked-field"')}
        <datalist id="vessel-type-suggestions">${(state.catalogs.vesselTypeSuggestions || []).map(item => `<option value="${esc(item)}">`).join('')}</datalist>
        ${selectField('vessel_class','Cấp phương tiện',state.catalogs.vesselClasses,d.vessel_class,isNew ? 'required' : 'required data-locked="true" tabindex="-1" class="locked-field"')}
        ${field('length_m','Chiều dài (m)',d.length_m,'number',isNew ? 'step="0.01" min="0"' : 'step="0.01" min="0" readonly class="locked-field"')}
        ${field('deadweight_tons','Trọng tải toàn phần',d.deadweight_tons,'number',isNew ? 'step="0.01" min="0"' : 'step="0.01" min="0" readonly class="locked-field"')}
        ${field('gross_tonnage','Dung tích (GT)',d.gross_tonnage,'number',isNew ? 'step="0.01" min="0"' : 'step="0.01" min="0" readonly class="locked-field"')}
        ${field('certificate_expiry_date','Hạn GCN ATKT & BVMT',d.certificate_expiry_date,'date',isNew ? '' : 'readonly class="locked-field"')}
        ${field('crew_count','Số thuyền viên tối thiểu',d.crew_count,'number',isNew ? 'min="0"' : 'min="0" readonly class="locked-field"')}
        ${field('passenger_count','Số hành khách',d.passenger_count,'number','min="0"')}
        <label class="wide-field"><span>Phân loại tàu khách</span><span class="checkbox-line"><input name="is_passenger_call" type="checkbox" ${d.is_passenger_call ? 'checked' : ''}>Đánh dấu để chọn phượng tiện này là tàu khách</span></label>
        <div class="record-lock-note wide-field" ${isNew ? 'hidden' : ''}><strong>Thông tin hồ sơ phương tiện</strong><span>Chọn đúng phương tiện để hệ thống tự điền.</span></div>
        <p class="muted wide-field" ${isNew ? '' : 'hidden'}>Hồ sơ phương tiện mới sẽ được lưu khi phiếu được xác nhận gửi, để lần sau có thể chọn lại.</p>
      </div></section>
    </div>
    <div class="wizard-step" data-step="2" ${state.wizardStep === 2 ? '' : 'hidden'}>
      <section class="form-section"><h3>B. Hành trình</h3><div class="section-grid">
        ${field('last_port','Cảng rời cuối cùng',d.last_port,'text','required list="ports-list"')}
        ${field('working_port','Cảng / cầu bến đến làm hàng',d.working_port,'text','required list="ports-list"')}
        ${field('departure_berth','Cảng / cầu bến rời',d.departure_berth,'text','list="ports-list"')}
        ${field('destination_port','Cảng đích',d.destination_port,'text','list="ports-list"')}
        ${dateTimeField('eta','Thời gian dự kiến đến',d.eta,'required')}
        ${dateTimeField('etd','Thời gian dự kiến rời',d.etd,'required')}
        ${dateTimeField('actual_arrival_at','Thời gian đến thực tế',d.actual_arrival_at)}
        ${dateTimeField('actual_departure_at','Thời gian rời thực tế',d.actual_departure_at)}
        ${field('agent_ptnd_name','Đại lý PTND',d.agent_ptnd_name,'text','class="wide-field"')}
        <datalist id="ports-list"></datalist>
      </div></section>
    </div>
    <div class="wizard-step" data-step="3" ${state.wizardStep === 3 ? '' : 'hidden'}>
      ${cargoFields('unload','C. Hàng hóa dỡ tại cảng',d.unload || {},false)}
      ${cargoFields('load','D. Hàng hóa xếp tại cảng',d.load || {},true)}
    </div>
    <div class="wizard-step" data-step="4" ${state.wizardStep === 4 ? '' : 'hidden'}>
      <section class="form-section"><h3>E. Thuyền trưởng và thuyền viên</h3><div class="section-grid">
        ${isNew
          ? `<div class="span-full">${newCrewRowsHtml()}</div>`
          : `<div class="span-full captain-edit-block">
              <strong>Thuyền trưởng</strong>
              <div class="captain-edit-fields">
                ${field('master_name','Họ và Tên',masterName,'text','required')}
                ${field('master_phone','Số điện thoại',masterPhone,'tel','required')}
              </div>
              <small id="assigned-captain">${assignedCaptain
                ? `Tự điền từ Danh sách thuyền viên: ${esc(assignedCaptain.full_name)}.`
                : 'Chưa có thông tin Thuyền trưởng theo phương tiện — vui lòng bổ sung.'}</small>
            </div>`}
        <label class="span-full crew-onboard-field">Số lượng thuyền viên đi theo lượt này
          <div class="stepper">
            <button type="button" class="stepper-btn" data-stepper-delta="-1" aria-label="Giảm số lượng thuyền viên">−</button>
            <input type="number" name="crew_onboard_count" min="0" step="1" value="${Number(d.crew_onboard_count) || 0}">
            <button type="button" class="stepper-btn" data-stepper-delta="1" aria-label="Tăng số lượng thuyền viên">+</button>
          </div>
        </label>
        <div class="span-full" id="declaration-crew-container" ${isNew ? 'hidden' : ''}>${isNew ? '' : crewChecklistHtml(d.vessel_id, [...(d.crew || []).map(item => item.id), ...(d.crew_ids || []), ...(assignedCaptain?.id ? [assignedCaptain.id] : [])])}</div>
      </div></section>
    </div>
    <div class="wizard-step" data-step="5" ${state.wizardStep === 5 ? '' : 'hidden'}>
      <section class="form-section"><h3>Đính kèm hồ sơ</h3><div class="section-grid">
        <label class="attachment-field wide-field">Hình ảnh / PDF / Word / Excel<input name="attachments" type="file" multiple accept=".jpg,.jpeg,.png,.webp,.pdf,.doc,.docx,.xls,.xlsx"><small>Mỗi file tối đa 12 MB. File được lưu cùng phiếu khai báo.</small></label>
      </div></section>
    </div>
    <div class="wizard-step" data-step="6" ${state.wizardStep === 6 ? '' : 'hidden'}>
      ${reviewSummaryHtml(d)}
    </div>`;

  const container = $('#declaration-fields');
  const declarationVessel = $('#declaration-vessel');
  if (declarationVessel) declarationVessel.onchange = fillFromVessel;
  ['unload','load'].forEach(prefix => {
    // Đổi số lượng cont, số tấn/cont, hoặc loại hàng đều tính lại tổng. Lưu ý:
    // ô Khối lượng (_tons) KHÔNG nằm trong danh sách này để người dùng sửa tay
    // không bị ghi đè — chỉ các ô _tons20_*/_tons40_* mới kích hoạt tính lại.
    $$(`[name^="${prefix}_cont"], [name="${prefix}_tons20_full"], [name="${prefix}_tons20_empty"], [name="${prefix}_tons40_full"], [name="${prefix}_tons40_empty"]`, $('#declaration-form')).forEach(input => input.addEventListener('input', () => calculateCargo(prefix)));
    const typeSelect = $('#declaration-form').elements[`${prefix}_cargo_type`];
    if (typeSelect) typeSelect.addEventListener('change', () => { toggleContainerFields(prefix); calculateCargo(prefix); });
    toggleContainerFields(prefix);
  });
  bindDateTimeFields(container);
  $$('input[name="vessel_mode"]', container).forEach(radio => radio.addEventListener('change', event => {
    captureWizardFormState();
    state.declarationVesselMode = event.target.value;
    if (state.declarationVesselMode === 'new') state.editingDeclaration.vessel_id = '';
    // Switching modes changes which fields are required on later steps — forget any
    // further progress so it gets re-validated under the new mode instead of being
    // reachable via a stale wizard-dot jump.
    state.wizardMaxStep = state.wizardStep;
    renderDeclarationWizard();
  }));
  $$('[data-crew-field]', container).forEach(input => input.addEventListener('input', event => {
    const row = Number(event.target.dataset.crewRow);
    state.declarationNewCrew[row][event.target.dataset.crewField] = event.target.value;
  }));
  $('#add-new-crew-row', container)?.addEventListener('click', () => {
    captureWizardFormState();
    state.declarationNewCrew.push(newCrewRowTemplate());
    renderDeclarationWizard();
  });
  $$('[data-remove-crew-row]', container).forEach(button => button.addEventListener('click', () => {
    captureWizardFormState();
    state.declarationNewCrew.splice(Number(button.dataset.removeCrewRow), 1);
    renderDeclarationWizard();
  }));
  $$('[data-stepper-delta]', container).forEach(button => button.addEventListener('click', () => {
    const input = button.parentElement.querySelector('input[type="number"]');
    if (!input) return;
    const min = Number(input.min) || 0;
    input.value = Math.max(min, (Number(input.value) || 0) + Number(button.dataset.stepperDelta));
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }));
  $('[data-wizard-back]', container)?.addEventListener('click', () => goToWizardStep(state.wizardStep - 1));
  $('[data-wizard-next]', container)?.addEventListener('click', () => goToWizardStep(state.wizardStep + 1));
  $$('[data-wizard-dot]', container).forEach(dot => dot.addEventListener('click', () => {
    const target = Number(dot.dataset.wizardDot);
    if (target <= state.wizardMaxStep) goToWizardStep(target);
  }));

  // Cả hai nút lưu/gửi chỉ xuất hiện ở bước cuối (Xem lại & Gửi); các bước trước
  // đã có autosave nháp cục bộ nên không mất dữ liệu.
  const onLastStep = state.wizardStep === DECLARATION_STEPS.length;
  const submitButton = $('#submit-declaration');
  if (submitButton) submitButton.disabled = !onLastStep;
  // #save-draft không bị logic phân quyền lúc khởi động đụng tới nên ẩn/hiện ở đây là an toàn.
  const saveDraftButton = $('#save-draft');
  if (saveDraftButton) saveDraftButton.hidden = !onLastStep;
}

function toggleContainerFields(prefix) {
  const form = $('#declaration-form');
  const typeSelect = form?.elements[`${prefix}_cargo_type`];
  if (!typeSelect) return;
  const isContainer = (typeSelect.value || '') === 'Container';
  // Chỉ hiện các ô liên quan container khi Loại hàng = Container; hàng khô/lỏng
  // chỉ cần nhập Khối lượng (tấn) trực tiếp.
  const section = typeSelect.closest('.form-section');
  if (!section) return;
  $$('.container-only', section).forEach(el => { el.hidden = !isContainer; });
}

function calculateCargo(prefix) {
  const form = $('#declaration-form');
  const a = number(form.elements[`${prefix}_cont20_full`].value), b = number(form.elements[`${prefix}_cont20_empty`].value), c = number(form.elements[`${prefix}_cont40_full`].value), d = number(form.elements[`${prefix}_cont40_empty`].value);
  form.elements[`${prefix}_total`].value = a + b + c + d;
  form.elements[`${prefix}_teu`].value = a + b + (c + d) * 2;
  form.elements[`${prefix}_empty_teu`].value = b + d * 2;
  // Với hàng Container: Khối lượng = Σ(số lượng × số tấn mỗi container). Vẫn cho
  // sửa tay (hàng khô/lỏng nhập trực tiếp) — chỉ tự tính khi loại = Container.
  const isContainer = (form.elements[`${prefix}_cargo_type`]?.value || '') === 'Container';
  if (isContainer) {
    const t20f = number(form.elements[`${prefix}_tons20_full`].value), t20e = number(form.elements[`${prefix}_tons20_empty`].value);
    const t40f = number(form.elements[`${prefix}_tons40_full`].value), t40e = number(form.elements[`${prefix}_tons40_empty`].value);
    const totalTons = a * t20f + b * t20e + c * t40f + d * t40e;
    form.elements[`${prefix}_tons`].value = Math.round(totalTons * 100) / 100;
  }
}

function declarationData() {
  const form = $('#declaration-form');
  const data = values(form);
  // Blank optional number/date inputs arrive as "" via FormData, which the backend's
  // numeric fields reject outright — drop them so the schema's own default applies.
  Object.keys(data).forEach(key => { if (data[key] === '') delete data[key]; });
  data.crew_ids = [...$('#declaration-form').querySelectorAll('[name="crew_ids"]:checked')].map(input => Number(input.value));
  data.is_passenger_call = Boolean(form.elements.is_passenger_call?.checked);
  delete data.attachments;
  delete data.vessel_mode;
  ['unload','load'].forEach(prefix => {
    data[prefix] = {cargo_type:data[`${prefix}_cargo_type`],movement_type:data[`${prefix}_movement_type`],cargo_name:data[`${prefix}_cargo_name`],cont20_full:data[`${prefix}_cont20_full`],cont20_empty:data[`${prefix}_cont20_empty`],cont40_full:data[`${prefix}_cont40_full`],cont40_empty:data[`${prefix}_cont40_empty`],tons20_full:data[`${prefix}_tons20_full`] || 0,tons20_empty:data[`${prefix}_tons20_empty`] || 0,tons40_full:data[`${prefix}_tons40_full`] || 0,tons40_empty:data[`${prefix}_tons40_empty`] || 0,tons:data[`${prefix}_tons`]};
    Object.keys(data).filter(key => key.startsWith(`${prefix}_`)).forEach(key => delete data[key]);
  });
  if (state.editingDeclaration?.id) {
    data.id = state.editingDeclaration.id;
    data.version = state.editingDeclaration.version;
  }
  return data;
}

function updateLocalDraftStatus(savedAt = null, restored = false) {
  const node = $('#draft-state');
  if (!node) return;
  const parsed = savedAt ? new Date(savedAt) : null;
  const time = parsed && !Number.isNaN(parsed.getTime()) ? new Intl.DateTimeFormat('vi-VN', {hour:'2-digit', minute:'2-digit'}).format(parsed) : '';
  node.innerHTML = `<span aria-hidden="true">●</span> ${restored ? 'Đã khôi phục nháp cục bộ' : 'Nháp cục bộ'}${time ? ` · lưu lúc ${esc(time)}` : ''} · chưa gửi`;
}

function rememberDraft() {
  try {
    const savedAt = new Date().toISOString();
    localStorage.setItem('tanthuan-declaration-draft', JSON.stringify(declarationData()));
    localStorage.setItem('tanthuan-declaration-draft-saved-at', savedAt);
    updateLocalDraftStatus(savedAt);
  } catch (_) {}
}

async function saveDeclaration(event) {
  event.preventDefault();
  const form = $('#declaration-form');
  const submit = event.submitter?.value === 'submit';
  if (submit && state.wizardStep !== DECLARATION_STEPS.length) {
    toast('Vui lòng hoàn tất tất cả các bước trước khi xác nhận gửi.', true);
    return;
  }
  if (!validateWizardForm()) return;
  const isNewVessel = state.declarationVesselMode === 'new';
  if (!isNewVessel && (!form.elements.master_name.value || !form.elements.master_phone.value)) {
    toast('Phương tiện chưa có Thuyền trưởng kèm số điện thoại. Hãy gán trong Danh sách thuyền viên trước khi lập phiếu.', true);
    return;
  }
  setSubmitting(form, event.submitter, true, submit ? 'Đang xác nhận…' : 'Đang lưu…');
  try {
    if (isNewVessel) {
      const newVessel = await api('/api/vessels', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
        name: form.elements.vessel_name.value,
        registration_no: form.elements.registration_no.value,
        vessel_type: form.elements.vessel_type.value,
        vessel_class: form.elements.vessel_class.value,
        length_m: form.elements.length_m.value || null,
        deadweight_tons: form.elements.deadweight_tons.value || null,
        gross_tonnage: form.elements.gross_tonnage.value || null,
        certificate_expiry_date: form.elements.certificate_expiry_date.value || null,
        organization_name: form.elements.company_name.value,
      })});
      const newCrewIds = [];
      for (const row of state.declarationNewCrew) {
        // Gán ngay vào hồ sơ phương tiện vừa tạo để lần khai báo sau tự điền được Thuyền trưởng.
        const savedCrew = await api('/api/crew', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({...row, vessel_id: newVessel.id})});
        newCrewIds.push(savedCrew.id);
      }
      await Promise.all([loadVessels(), loadCrew()]);
      // <select> ignores .value assignments that don't match an existing <option>,
      // so add one before selecting it (the select is hidden while vesselMode==='new').
      const vesselOption = document.createElement('option');
      vesselOption.value = String(newVessel.id);
      vesselOption.selected = true;
      form.elements.vessel_id.appendChild(vesselOption);
      form.elements.master_name.value = state.declarationNewCrew[0]?.full_name || '';
      form.elements.master_phone.value = state.declarationNewCrew[0]?.phone || '';
      $('#declaration-crew-container').innerHTML = newCrewIds.map(crewId => `<input type="checkbox" name="crew_ids" value="${crewId}" checked hidden>`).join('');
      state.declarationVesselMode = 'existing';
    }
    const result = await api(`/api/declarations?submit=${submit}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(declarationData())});
    const files = [...$('#declaration-form').elements.attachments.files];
    for (const file of files) {
      await api(`/api/declarations/${result.id}/attachments?filename=${encodeURIComponent(file.name)}`, {method:'POST', headers:{'Content-Type':file.type || 'application/octet-stream'}, body:file});
    }
    localStorage.removeItem('tanthuan-declaration-draft');
    localStorage.removeItem('tanthuan-declaration-draft-saved-at');
    $('#declaration-dialog').close();
    const savedLabel = submit ? 'Phiếu đã được xác nhận gửi đến Cảng.' : 'Đã lưu phiếu nháp — xem ở đầu danh sách Phiếu khai báo.';
    toast(`${savedLabel}${files.length ? ` Đã tải ${files.length} file.` : ''}`);
    state.declarationPage = 1;
    await loadDeclarations();
    await loadDashboard();
    if (submit) refreshPendingBadge();
  } catch (error) {
    showStepErrors([error.message], `Không thể ${submit ? 'xác nhận gửi' : 'lưu'} phiếu:`);
    toast(error.message, true);
  }
  finally { setSubmitting(form, event.submitter, false); }
}

async function loadSuggestions() {
  try {
    const [last, work, destination] = await Promise.all(['last_port','working_port','destination_port'].map(name => api(`/api/suggestions?field=${name}`)));
    $('#ports-list').innerHTML = [...new Set([...last,...work,...destination])].map(value => `<option value="${esc(value)}">`).join('');
  } catch (_) {}
}

function renderWorkflowRisks(result) {
  const risks = result?.risks || [];
  const container = $('#workflow-risks');
  if (!container) return;
  if (!risks.length) {
    container.innerHTML = '<div class="risk-clear">✓ Không phát hiện rủi ro tự động. Vẫn nên đối chiếu giấy tờ đính kèm.</div>';
    return;
  }
  const icon = {danger: '⛔', warning: '⚠', info: 'ℹ'};
  const heading = result.dangerCount
    ? `Trợ lý kiểm tra: ${result.dangerCount} rủi ro nghiêm trọng cần rà soát`
    : `Trợ lý kiểm tra: ${risks.length} điểm cần lưu ý`;
  container.innerHTML = `<div class="risk-heading"><strong>${heading}</strong><small>Hệ thống chỉ cảnh báo — nhân viên Cảng đối chiếu giấy tờ và quyết định.</small></div>
    <ul class="risk-list">${risks.map(r => `<li class="risk-item ${r.severity}"><span aria-hidden="true">${icon[r.severity] || 'ℹ'}</span><span>${esc(r.message)}</span></li>`).join('')}</ul>`;
}

async function openWorkflow(id) {
  const declaration = state.declarations.find(item => item.id === id);
  if (!declaration) return;
  state.workflowDeclaration = declaration;
  $('#workflow-title').textContent = `${declaration.reference_no} · ${declaration.vessel_name}`;
  $('#workflow-summary').innerHTML = `<article><small>LOẠI PHIẾU</small><strong>${declaration.movement_type === 'DEPARTURE' ? 'Rời cảng' : 'Vào cảng'}</strong></article><article><small>TRẠNG THÁI</small><strong>${workflowLabel(declaration.workflow_status)}</strong></article><article><small>XÁC NHẬN CỦA CẢNG</small><span class="approval-dots">${approvalDot(declaration.port_approval, 'Cảng')}</span></article>`;
  $('#workflow-risks').innerHTML = '';
  api(`/api/declarations/${id}/risks`).then(renderWorkflowRisks).catch(() => {});
  const events = await api(`/api/declarations/${id}/events`);
  $('#workflow-timeline').innerHTML = events.length ? events.map(event => `<article><span></span><div><strong>${workflowLabel(event.to_status)} · ${esc(event.actor_name)}</strong><small>${esc(roleLabel(event.actor_role))} · ${fmtDate(event.created_at)}</small><p>${esc(event.note || event.action)}</p></div></article>`).join('') : empty('Chưa có lịch sử', 'Dấu vết sẽ xuất hiện khi phiếu được xử lý.');

  // Port-side confirmation gate: PORT_STAFF and PLATFORM_ADMIN can both act
  // (backend already permits both — see require_port_scope). PLATFORM_ADMIN
  // has the highest privilege and must be able to intervene here too.
  const select = $('#workflow-form select[name="action"]');
  const role = state.currentUser ? state.currentUser.role : '';
  const canAct = ['PORT_STAFF', 'PLATFORM_ADMIN'].includes(role);
  select.innerHTML = canAct
    ? '<option value="">Chọn</option><option value="PORT_APPROVE">Xác nhận hoàn tất</option><option value="REQUEST_CHANGES">Yêu cầu bổ sung</option>'
    : '<option value="">Chọn</option>';

  // Hide workflow action form for customers / read-only reviewers
  $('#workflow-form').style.display = canAct ? 'block' : 'none';

  $('#workflow-dialog').showModal();
}

async function saveWorkflow(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = values(event.currentTarget);
  if (data.action === 'REQUEST_CHANGES' && !data.note.trim()) return toast('Cần nhập lý do cho thao tác này.', true);
  setSubmitting(form, event.submitter, true, 'Đang ghi nhận…');
  try {
    await api(`/api/declarations/${state.workflowDeclaration.id}/workflow`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    form.reset();
    // Cả hai thao tác (Duyệt/hoàn tất và Yêu cầu bổ sung) đều đóng dialog sau khi
    // ghi nhận. Với REQUEST_CHANGES, phiếu chuyển sang CHANGES_REQUESTED nên khách
    // hàng thấy ngay trong hàng đợi "Cần chú ý" và timeline (kèm lý do) — đó là
    // kênh thông báo in-app hiện có.
    toast(data.action === 'REQUEST_CHANGES'
      ? 'Đã gửi yêu cầu bổ sung. Khách hàng sẽ thấy phiếu trong mục cần xử lý.'
      : 'Đã xác nhận hoàn tất và cập nhật timeline.');
    $('#workflow-dialog').close();
    state.workflowDeclaration = null;
    await loadDeclarations();
    refreshPendingBadge();
  } catch (error) { toast(error.message, true); }
  finally { setSubmitting(form, event.submitter, false); }
}

function applyDeclarationFilters() {
  state.declarationFilter = {q:$('#declaration-search').value.trim(),movement_type:$('#movement-filter').value,workflow_status:$('#workflow-filter').value,master_name:$('#master-filter').value.trim(),from:$('#declaration-from').value,to:$('#declaration-to').value};
  state.declarationPage = 1;
  syncDeclarationUrl();
  loadDeclarations();
}

function syncDeclarationUrl() {
  const params = new URLSearchParams(Object.entries({...state.declarationFilter, page: state.declarationPage}).filter(([, value]) => value));
  const url = new URL(window.location);
  url.search = params.toString();
  history.replaceState(null, '', url);
}

const IMPORT_FILE_HEADERS = {'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'};

function setImportResult(html, isEmptyPlaceholder = false) {
  const container = state.importResultTarget === 'port-register' ? $('#port-import-result') : $('#import-result');
  container.classList.toggle('empty-state', isEmptyPlaceholder);
  container.innerHTML = html;
}

async function previewImport(input, path, kind) {
  const file = input.files[0];
  if (!file) return;
  state.importResultTarget = path.includes('/port-vessel-register') ? 'port-register' : 'main';
  if (state.importResultTarget === 'port-register' && !$('#port-import-dialog').open) {
    $('#port-import-dialog').showModal();
  }
  setImportResult('Đang đọc và kiểm tra file…');
  try {
    const preview = await api(`${path}?preview=true`, {method:'POST', headers:IMPORT_FILE_HEADERS, body:file});
    state.pendingImport = {kind, path, file, preview};
    renderImportPreview();
  } catch (error) {
    setImportResult(`<div><strong>Không thể đọc file</strong><p>${esc(error.message)}</p></div>`);
    toast(error.message, true);
    input.value = '';
  }
}

function renderImportPreview() {
  const {kind, preview} = state.pendingImport;
  let warningCount = 0;
  let conflictCount = 0;
  let overwritableCount = 0;
  let bodyHtml;
  if (kind === 'vessels') {
    const rows = preview.rows || [];
    warningCount = rows.filter(row => row.missingFields?.length).length;
    conflictCount = rows.filter(row => row.existing).length;
    overwritableCount = rows.filter(row => row.existing && !row.ownershipConflict).length;
    bodyHtml = rows.length
      ? `<table class="data-table responsive-table"><thead><tr><th>Dòng</th><th>Tên phương tiện</th><th>Số đăng ký</th><th>Kiểm tra</th></tr></thead><tbody>${rows.map(row => {
          const check = row.missingFields?.length
            ? `<span class="table-badge danger">Thiếu: ${esc(row.missingFields.join(', '))}</span>`
            : row.ownershipConflict
              ? '<span class="table-badge danger">Trùng dữ liệu tổ chức khác</span>'
            : row.existing
              ? `<span class="table-badge draft" title="${esc((row.changes || []).map(item => `${item.label}: ${item.current ?? '—'} → ${item.incoming ?? '—'}`).join(' · '))}">Đã có · ${(row.changes || []).length} thay đổi</span>`
            : row.mappingWarnings?.length
              ? `<span class="table-badge draft" title="${esc(row.mappingWarnings.join(' · '))}">Hợp lệ · đã chuẩn hóa</span>`
              : '<span class="table-badge submitted">Hợp lệ</span>';
          return `<tr><td data-label="Dòng">${row.sourceRow}</td><td data-label="Tên phương tiện">${esc(row.name || '—')}</td><td data-label="Số đăng ký">${esc(row.registration_no || '—')}</td><td data-label="Kiểm tra">${check}</td></tr>`;
        }).join('')}</tbody></table>`
      : empty('Không tìm thấy dòng dữ liệu', 'Kiểm tra lại file có đúng mẫu và còn dữ liệu hay không.');
  } else if (kind === 'crew') {
    const rows = preview.rows || [];
    warningCount = rows.filter(row => row.missingFields?.length).length;
    conflictCount = rows.filter(row => row.existing).length;
    bodyHtml = rows.length
      ? `<table class="data-table responsive-table"><thead><tr><th>Dòng</th><th>Doanh nghiệp</th><th>Họ tên</th><th>Chức danh</th><th>Kiểm tra</th></tr></thead><tbody>${rows.map(row => {
          const check = row.missingFields?.length
            ? `<span class="table-badge danger">Thiếu: ${esc(row.missingFields.join(', '))}</span>`
            : row.existing
              ? `<span class="table-badge draft" title="${esc((row.changes || []).map(item => `${item.label}: ${item.current ?? '—'} → ${item.incoming ?? '—'}`).join(' · '))}">Sẽ cập nhật · ${(row.changes || []).length} thay đổi</span>`
              : '<span class="table-badge submitted">Sẽ thêm mới</span>';
          return `<tr><td data-label="Dòng">${row.sourceRow}</td><td data-label="Doanh nghiệp">${esc(row.organization_name || '—')}</td><td data-label="Họ tên">${esc(row.full_name || '—')}</td><td data-label="Chức danh">${esc(row.crew_role || '—')}</td><td data-label="Kiểm tra">${check}</td></tr>`;
        }).join('')}</tbody></table>`
      : empty('Không tìm thấy dòng dữ liệu', 'Kiểm tra lại file có đúng cột và còn dữ liệu hay không.');
  } else {
    const row = preview.row || {};
    const missing = preview.missingFields || [];
    warningCount = missing.length ? 1 : 0;
    bodyHtml = `<div class="attachment-field"><strong>${esc(row.vessel_name || '—')} · ${esc(row.registration_no || '—')}</strong><p>${esc(row.last_port || '—')} → ${esc(row.working_port || '—')}</p><small>${missing.length ? `Thiếu: ${esc(missing.join(', '))}` : 'Đủ dữ liệu bắt buộc.'}</small></div>`;
  }
  const mapping = preview.mapping;
  setImportResult(`
    ${mapping ? `<div class="import-mapping-note"><strong>Đã tự nhận diện cấu trúc</strong><span>Sheet: ${esc(mapping.sheet || '—')} · Mapping: theo nhãn cột</span></div>` : ''}
    ${warningCount ? `<div class="warning-strip visible">${kind === 'declaration' ? 'File thiếu dữ liệu bắt buộc — không thể import cho đến khi bổ sung.' : `Có ${warningCount} dòng thiếu hoặc sai dữ liệu bắt buộc — các dòng này sẽ bị bỏ qua nếu bạn tiếp tục.`}</div>` : ''}
    ${kind === 'crew' && conflictCount ? `<div class="warning-strip visible"><strong>Có ${conflictCount} thuyền viên đã tồn tại.</strong> Khi xác nhận, nhân viên Cảng sẽ cập nhật các trường thay đổi theo file Excel; không có thao tác gán phương tiện.</div>` : ''}
    ${kind === 'vessels' && conflictCount ? `<div class="warning-strip visible"><strong>Có ${conflictCount} phương tiện đã tồn tại.</strong> Mặc định hệ thống giữ dữ liệu hiện có. Chỉ chọn ghi đè sau khi xem các thay đổi trong cột Kiểm tra.${preview.previousImportId ? ` File này trùng lần import #${esc(preview.previousImportId)}.` : ''}</div>` : ''}
    ${bodyHtml}
    <div class="modal-actions">
      <button type="button" class="ghost-button" id="cancel-import">Huỷ</button>
      <button type="button" class="outline-button" id="confirm-import" ${kind === 'declaration' && warningCount ? 'disabled' : ''}>${kind === 'vessels' && conflictCount ? 'Giữ dữ liệu hiện có & tiếp tục' : kind === 'crew' ? 'Xác nhận cập nhật' : 'Xác nhận import'}</button>
      ${kind === 'vessels' && overwritableCount ? `<button type="button" class="primary-button" id="overwrite-import">Ghi đè ${overwritableCount} bản ghi</button>` : ''}
    </div>`);
  $('#cancel-import').onclick = cancelImport;
  $('#confirm-import').onclick = () => confirmImport(false);
  const overwriteButton = $('#overwrite-import');
  if (overwriteButton) overwriteButton.onclick = () => {
    if (window.confirm(`Ghi đè ${overwritableCount} phương tiện bằng dữ liệu đã chuẩn hóa trong file Excel?`)) {
      confirmImport(true);
    }
  };
}

function cancelImport() {
  state.pendingImport = null;
  $('#import-vessels').value = '';
  $('#import-declaration').value = '';
  $('#import-crew').value = '';
  if ($('#import-port-register')) $('#import-port-register').value = '';
  setImportResult('Chưa có file nào được import trong phiên này.', true);
  if ($('#port-import-dialog').open) $('#port-import-dialog').close();
  state.importResultTarget = 'main';
}

async function confirmImport(overwriteExisting = false) {
  const {path, file} = state.pendingImport;
  const button = overwriteExisting ? $('#overwrite-import') : $('#confirm-import');
  button.disabled = true;
  button.textContent = overwriteExisting ? 'Đang ghi đè…' : 'Đang import…';
  try {
    const requestPath = overwriteExisting ? `${path}?overwrite_existing=true` : path;
    const result = await api(requestPath, {method:'POST', headers:IMPORT_FILE_HEADERS, body:file});
    if (result.idempotent) {
      setImportResult(`<div><strong>File đã được nhập trước đó</strong><p>Không tạo thêm bản ghi. Kết quả lần nhập gốc: ${result.accepted || 0} bản ghi, ${result.rejected?.length || 0} dòng bị từ chối.</p><small>Mã import: ${esc(result.importJobId || '—')}</small></div>`);
      toast('Không tạo bản ghi trùng — file này đã được nhập trước đó.');
    } else {
      setImportResult(`<div><strong>Import thành công</strong><p>Thêm mới: ${result.created || 0} · Cập nhật: ${result.updated || 0} · Giữ dữ liệu cũ: ${result.skipped || 0}.${result.rejected?.length ? ` Có ${result.rejected.length} dòng bị từ chối.` : ''}</p>${result.rejected?.length ? `<ul>${result.rejected.map(item => `<li>Dòng ${item.sourceRow}: ${esc(item.error)}</li>`).join('')}</ul>` : ''}</div>`);
      toast(overwriteExisting ? 'Đã ghi đè các bản ghi được chọn từ Excel.' : 'Đã nhập dữ liệu mới và giữ nguyên các bản ghi đã có.');
    }
    state.pendingImport = null;
    $('#import-vessels').value = '';
    $('#import-declaration').value = '';
    $('#import-crew').value = '';
    if ($('#import-port-register')) $('#import-port-register').value = '';
    const refreshes = [loadVessels(), loadDeclarations(), loadCrew(), loadDashboard()];
    if (['PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role)) refreshes.push(loadPortRegister());
    await Promise.all(refreshes);
    if (state.importResultTarget === 'port-register' && $('#port-import-dialog').open) $('#port-import-dialog').close();
    state.importResultTarget = 'main';
  } catch (error) {
    setImportResult(`<div><strong>Không thể import</strong><p>${esc(error.message)}</p></div>`);
    toast(error.message, true);
  }
}

const HISTORICAL_SOURCE_LABELS = {
  tos_berth_call: 'TOS Berth · lượt cập/rời bến',
  tos_cargo_detail: 'TOS chi tiết container',
  reported_pl03: 'PL.03 lịch sử đã báo cáo',
};
const HISTORICAL_STATUS_LABELS = {
  PREVIEWED: 'Chờ xác nhận', COMMITTED: 'Đang dùng', REVIEW: 'Chờ kiểm tra',
  REJECTED: 'Đã hủy / giữ bản cũ', SUPERSEDED: 'Đã được thay bằng revision mới',
};
const HISTORICAL_WARNING_LABELS = {
  INVALID_CALL_IDENTITY: 'Thiếu hoặc sai tên phương tiện, năm hay số chuyến.',
  ATB_BLANK: 'Thiếu ATB. Bổ sung trong file Berth rồi upload lại.',
  ATB_INVALID: 'ATB không đúng định dạng ngày giờ. Sửa file Berth rồi upload lại.',
  ATD_BLANK: 'Thiếu ATD. Bổ sung trong file Berth rồi upload lại.',
  ATD_INVALID: 'ATD không đúng định dạng ngày giờ. Sửa file Berth rồi upload lại.',
  DUPLICATE_CALL_KEY: 'Trùng tên phương tiện, năm và chuyến trong file Berth.',
  UNSUPPORTED_CONTAINER_SIZE: 'Kích cỡ container không phải 20/40 feet.',
  UNKNOWN_FULL_EMPTY: 'F/E phải là F hoặc E.',
  UNKNOWN_TRADE_SCOPE: 'Không nhận diện được Hàng nội/Hàng ngoại.',
  UNKNOWN_MOVEMENT_METHOD: 'Không nhận diện được phương án xếp dỡ.',
  WEIGHT_BLANK: 'Thiếu trọng lượng container.',
  WEIGHT_INVALID: 'Trọng lượng không phải số.',
  UNMATCHED_VESSEL: 'Chưa có phương tiện tương ứng trong Sổ theo dõi. Xử lý tại mục Liên kết phương tiện bên dưới.',
  AMBIGUOUS_VESSEL: 'Có nhiều phương tiện có thể trùng. Chọn đúng phương tiện tại mục Liên kết bên dưới.',
  REVIEW_NORMALIZED_VESSEL_LINK: 'Tên chỉ khớp sau chuẩn hóa. Xác nhận tại mục Liên kết phương tiện bên dưới.',
};

function historicalWarnings(row) {
  // Provenance keeps the original warning codes for audit. Once a row becomes
  // VALID, those codes are resolved history and must not be presented as an
  // active error to the operator.
  if (row.validationStatus === 'VALID') return [];
  const codes = [...(row.warnings || row.provenance?.warnings || [])];
  if (row.matchStatus === 'UNMATCHED' && !codes.includes('UNMATCHED_CALL')) codes.push('UNMATCHED_CALL');
  if (row.matchStatus === 'AMBIGUOUS' && !codes.includes('AMBIGUOUS_CALL')) codes.push('AMBIGUOUS_CALL');
  return [...new Set(codes)].map(code => {
    if (code === 'UNMATCHED_CALL') return 'Chưa ghép được lượt Berth. Xác nhận file Berth trong cùng đợt rồi mở lại file này.';
    if (code === 'AMBIGUOUS_CALL') return 'Có nhiều lượt Berth trùng khóa chuyến; cần kiểm tra file Berth.';
    const metric = /^INVALID_METRIC_([A-Z]+)$/.exec(code);
    if (metric) return `Cột ${metric[1]} không phải số. Sửa ô tương ứng trong file PL.03 rồi upload lại.`;
    return HISTORICAL_WARNING_LABELS[code] || code.replaceAll('_', ' ').toLowerCase();
  });
}

function historicalWarningCell(row) {
  const warnings = historicalWarnings(row);
  return warnings.length ? `<ul class="historical-warning-list">${warnings.map(item => `<li>${esc(item)}</li>`).join('')}</ul>` : '<span class="muted">—</span>';
}

function setImportMode(mode) {
  state.importMode = mode === 'historical' ? 'historical' : 'operational';
  const historical = state.importMode === 'historical';
  $('#operational-import-panel').hidden = historical;
  $('#historical-import-panel').hidden = !historical;
  $('#operational-import-tab').classList.toggle('active', !historical);
  $('#historical-import-tab').classList.toggle('active', historical);
  $('#operational-import-tab').setAttribute('aria-selected', String(!historical));
  $('#historical-import-tab').setAttribute('aria-selected', String(historical));
  if (historical) {
    ensureHistoricalExportPanel();
    loadHistoricalImportHistory();
  }
}

// Report period picker: two selects (Tháng / Năm) instead of the native month
// input, to match the app's own control styling. Value is a "YYYY-MM" string.
function pl03PeriodSelectsHtml() {
  const now = new Date().getFullYear();
  const years = Array.from({length: 7}, (_, i) => now - i);
  const months = Array.from({length: 12}, (_, i) => String(i + 1).padStart(2, '0'));
  return `<label>Tháng<select id="historical-pl03-month"><option value="">—</option>${months.map(m => `<option value="${m}">${Number(m)}</option>`).join('')}</select></label>`
    + `<label>Năm<select id="historical-pl03-year"><option value="">—</option>${years.map(y => `<option value="${y}">${y}</option>`).join('')}</select></label>`;
}

function pl03PeriodValue() {
  const m = $('#historical-pl03-month')?.value;
  const y = $('#historical-pl03-year')?.value;
  return (m && y) ? `${y}-${m}` : '';
}

function setPl03Period(period) {
  if (!period) return;
  const [y, m] = period.split('-');
  const monthSel = $('#historical-pl03-month');
  const yearSel = $('#historical-pl03-year');
  if (!monthSel || !yearSel) return;
  if (y && !Array.from(yearSel.options).some(option => option.value === y)) {
    yearSel.insertBefore(new Option(y, y), yearSel.options[1] || null);
  }
  monthSel.value = m;
  yearSel.value = y;
}

function ensureHistoricalExportPanel() {
  if ($('#historical-pl03-export')) return;
  const historyPanel = $('.historical-history-panel');
  if (!historyPanel) return;
  const panel = document.createElement('section');
  panel.id = 'historical-pl03-export';
  panel.className = 'panel historical-export-panel';
  panel.innerHTML = `<div><p class="eyebrow">KẾT QUẢ ĐỐI SOÁT</p><h2>PL.03 tổng hợp từ TOS</h2></div><div class="historical-export-actions">${pl03PeriodSelectsHtml()}<button id="export-historical-pl03" type="button" class="primary-button">Xuất PL.03 tổng hợp</button></div>`;
  historyPanel.before(panel);
  $('#export-historical-pl03').onclick = exportHistoricalPl03;
}

async function exportHistoricalPl03() {
  const reportingPeriod = pl03PeriodValue();
  if (!reportingPeriod) {
    toast('Chọn tháng báo cáo trước khi xuất PL.03 tổng hợp.', true);
    $('#historical-pl03-month')?.focus();
    return;
  }
  const button = $('#export-historical-pl03');
  const original = button.textContent;
  button.disabled = true;
  button.textContent = 'Đang tổng hợp…';
  try {
    await downloadFile(
      `/api/historical-imports/exports/pl03?reporting_period=${encodeURIComponent(reportingPeriod)}`,
      `PL03_TOS_${reportingPeriod}.xlsx`,
    );
    toast('Đã xuất PL.03 tổng hợp từ dữ liệu TOS đã xác nhận.');
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; button.textContent = original; }
}

function historicalStatusTone(status) {
  if (status === 'COMMITTED') return 'submitted';
  if (status === 'REJECTED') return 'danger';
  return 'draft';
}

// Result cell: colour carries the meaning (green = hợp lệ, cam = cần kiểm tra,
// đỏ = từ chối). Zeros are omitted; only non-zero exceptions show. Titles keep
// the words available for screen readers and hover without visual clutter.
function historicalResultCell(item) {
  const n = value => number(value).toLocaleString('vi-VN');
  const parts = [`<b class="hres ok" title="${n(item.accepted)} hợp lệ">${n(item.accepted)}</b>`];
  if (item.review) parts.push(`<b class="hres warn" title="${n(item.review)} cần kiểm tra">${n(item.review)}</b>`);
  if (item.rejected) parts.push(`<b class="hres rej" title="${n(item.rejected)} từ chối">${n(item.rejected)}</b>`);
  return `<span class="hres-cell">${parts.join('')}</span>`;
}

// Revision cell: rev 1 is the default, so keep it quiet; a superseding revision
// (rev >= 2) or a superseded link is what actually needs attention.
function historicalRevCell(item) {
  const link = item.supersededByImportId ? `<br><small>→ #${item.supersededByImportId}</small>` : '';
  const rev = item.revisionNo > 1
    ? `<span class="rev-badge">rev ${item.revisionNo}</span>`
    : `<span class="rev-muted">${item.revisionNo}</span>`;
  return rev + link;
}

function historicalEffectivePeriod(item, activeBerthPeriods) {
  if (item.reportingPeriod) return item.reportingPeriod;
  if (item.sourceKind === 'reported_pl03' && activeBerthPeriods.length === 1) {
    return activeBerthPeriods[0];
  }
  return 'Chưa xác định';
}

function renderHistoricalHistorySummary(summary = {}) {
  const target = $('#historical-history-summary');
  if (!target) return;
  const accepted = number(summary.accepted);
  const review = number(summary.review);
  const rejected = number(summary.rejected);
  const parts = [
    `<span class="history-total-ok"><b>${accepted.toLocaleString('vi-VN')}</b> đạt</span>`,
    `<span class="history-total-review"><b>${review.toLocaleString('vi-VN')}</b> cần kiểm tra</span>`,
  ];
  if (rejected) parts.push(`<span class="history-total-rejected"><b>${rejected.toLocaleString('vi-VN')}</b> bị loại</span>`);
  target.innerHTML = parts.join('<span class="history-total-separator">·</span>');
}

function renderHistoricalPagination(container, result, attribute, callback) {
  const totalPages = Math.max(1, Math.ceil((result.total || 0) / (result.pageSize || 1)));
  if (totalPages <= 1) { container.innerHTML = ''; return; }
  container.innerHTML = `<span>Trang ${result.page}/${totalPages}</span><button type="button" data-${attribute}="${result.page - 1}" ${result.page <= 1 ? 'disabled' : ''}>Trước</button><button type="button" data-${attribute}="${result.page + 1}" ${result.page >= totalPages ? 'disabled' : ''}>Sau</button>`;
  $$(`[data-${attribute}]`, container).forEach(button => button.onclick = () => callback(Number(button.dataset[attribute.replace(/-([a-z])/g, (_, c) => c.toUpperCase())])));
}

function updateHistoricalSteps(item) {
  const steps = $$('.historical-import-steps li');
  steps.forEach(step => step.classList.remove('active', 'done'));
  if (!item) { steps[0]?.classList.add('active'); return; }
  steps[0]?.classList.add('done');
  steps[1]?.classList.add('done');
  if (item.status !== 'PREVIEWED') {
    steps.forEach(step => step.classList.add('done'));
  } else if (item.conflictingImportIds?.length) {
    steps[2]?.classList.add('active');
  } else {
    steps[2]?.classList.add('done');
    steps[3]?.classList.add('active');
  }
}

async function previewHistoricalImport(input) {
  const files = [...input.files];
  if (!files.length) return;
  const panel = $('#historical-preview');
  panel.hidden = true;
  const batchPanel = $('#historical-batch');
  batchPanel.hidden = false;
  state.historicalBatch = files.map(file => ({filename: file.name, loading: true}));
  renderHistoricalBatch();
  batchPanel.scrollIntoView({behavior: 'smooth', block: 'start'});
  for (let index = 0; index < files.length; index += 1) {
    const file = files[index];
    try {
      const result = await api('/api/historical-imports/preview', {
        method: 'POST',
        headers: {...IMPORT_FILE_HEADERS, 'X-Source-Filename': encodeURIComponent(file.name)},
        body: file,
      });
      state.historicalBatch[index] = {filename: file.name, result};
    } catch (error) {
      state.historicalBatch[index] = {filename: file.name, error: error.message};
    }
    renderHistoricalBatch();
  }
  input.value = '';
  const successful = state.historicalBatch.filter(item => item.result);
  if (!successful.length) {
    toast('Không file nào tạo được preview.', true);
    return;
  }
  const first = successful.sort((a, b) => {
    const priority = {tos_berth_call: 0, tos_cargo_detail: 1, reported_pl03: 2};
    return (priority[a.result.sourceKind] ?? 9) - (priority[b.result.sourceKind] ?? 9);
  })[0].result;
  state.historicalImport = first;
  state.historicalPreviewPage = 1;
  state.historicalRowFilter = first.review ? 'review' : (first.rejected ? 'rejected' : 'all');
  await renderHistoricalImportWorkspace();
  await loadHistoricalImportHistory();
  toast(`Đã tạo preview cho ${successful.length}/${files.length} file. Chưa có dữ liệu nào được kích hoạt.`);
}

function renderHistoricalBatch() {
  const panel = $('#historical-batch');
  panel.hidden = !state.historicalBatch.length;
  if (panel.hidden) return;
  const complete = state.historicalBatch.filter(item => !item.loading).length;
  $('#historical-batch-title').textContent = complete < state.historicalBatch.length
    ? `Đang đọc ${complete}/${state.historicalBatch.length} file`
    : `${state.historicalBatch.length} file trong đợt upload`;
  $('#historical-batch-list').innerHTML = state.historicalBatch.map(item => {
    if (item.loading) return `<article class="historical-batch-row"><div><strong>${esc(item.filename)}</strong><small>Đang nhận diện cấu trúc…</small></div><span class="table-badge draft">Đang đọc</span></article>`;
    if (item.error) return `<article class="historical-batch-row error"><div><strong>${esc(item.filename)}</strong><small>${esc(item.error)}</small></div><span class="table-badge danger">Không đọc được</span></article>`;
    const result = item.result;
    return `<article class="historical-batch-row"><div><strong>${esc(item.filename)}</strong><small>${esc(HISTORICAL_SOURCE_LABELS[result.sourceKind] || result.sourceKind)} · ${number(result.accepted)} hợp lệ · ${number(result.review)} cần xử lý · ${number(result.rejected)} bị loại</small></div><button type="button" class="outline-button" data-open-batch-import="${result.id}">Mở kiểm tra</button></article>`;
  }).join('');
  $$('[data-open-batch-import]', panel).forEach(button => button.onclick = () => openHistoricalImport(Number(button.dataset.openBatchImport)));
}

async function refreshHistoricalBatch() {
  if (!state.historicalBatch.length) return;
  await Promise.all(state.historicalBatch.map(async entry => {
    if (!entry.result) return;
    try { entry.result = await api(`/api/historical-imports/${entry.result.id}`); }
    catch (_) { /* Keep the last visible receipt if one refresh fails. */ }
  }));
  renderHistoricalBatch();
}

async function openHistoricalImport(importId) {
  try {
    state.historicalImport = await api(`/api/historical-imports/${importId}`);
    state.historicalPreviewPage = 1;
    state.historicalRowFilter = state.historicalImport.review ? 'review' : (state.historicalImport.rejected ? 'rejected' : 'all');
    const batchEntry = state.historicalBatch.find(entry => entry.result?.id === importId);
    if (batchEntry) { batchEntry.result = state.historicalImport; renderHistoricalBatch(); }
    await renderHistoricalImportWorkspace();
    $('#historical-preview').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (error) { toast(error.message, true); }
}

async function renderHistoricalImportWorkspace() {
  const item = state.historicalImport;
  if (!item) return;
  $('#historical-preview').hidden = false;
  $('#historical-preview-title').textContent = HISTORICAL_SOURCE_LABELS[item.sourceKind] || item.sourceKind;
  $('#historical-preview-subtitle').textContent = `${item.sourceFilename || 'File Excel'} · Mapping ${item.mappingVersion || '—'} · SHA-256 ${String(item.checksum || '').slice(0, 12)}…`;
  $('#historical-preview-summary').innerHTML = `
    <article class="historical-summary-card"><small>Kỳ báo cáo</small><strong>${esc(item.reportingPeriod || 'Chưa xác định')}</strong></article>
    <article class="historical-summary-card"><small>Trạng thái</small><strong>${esc(HISTORICAL_STATUS_LABELS[item.status] || item.status)}</strong></article>
    <article class="historical-summary-card valid"><small>Hợp lệ</small><strong>${number(item.accepted).toLocaleString('vi-VN')}</strong></article>
    <article class="historical-summary-card review"><small>Cần xử lý</small><strong>${number(item.review).toLocaleString('vi-VN')}</strong></article>
    <article class="historical-summary-card rejected"><small>Bị loại</small><strong>${number(item.rejected).toLocaleString('vi-VN')}</strong></article>`;
  const conflicts = item.conflictingImportIds || [];
  const conflictNotice = $('#historical-conflict-notice');
  conflictNotice.hidden = !conflicts.length;
  conflictNotice.innerHTML = conflicts.length
    ? `<strong>Phát hiện dữ liệu cùng nguồn và cùng kỳ đang được sử dụng</strong>File hiện tại chưa thay bản cũ. Chọn “Giữ bản đang dùng” hoặc ghi lý do và chọn “Dùng file mới · tạo revision”. Lượt liên quan: ${conflicts.map(id => `#${esc(id)}`).join(', ')}.` : '';
  const reviewGuide = $('#historical-review-guide');
  reviewGuide.hidden = !item.review && !item.rejected;
  if (!reviewGuide.hidden) {
    const pendingBerth = [
      ...state.historicalBatch.map(entry => entry.result), ...state.historicalHistory,
    ].find(entry => entry?.sourceKind === 'tos_berth_call' && entry.status === 'PREVIEWED');
    const location = item.sourceKind === 'tos_berth_call'
      ? 'Lỗi liên kết phương tiện xử lý tại mục “Liên kết phương tiện” ngay dưới bảng.'
      : item.sourceKind === 'tos_cargo_detail'
        ? 'Nếu chưa ghép lượt, mở file Berth đang chờ và xác nhận; hệ thống sẽ tự kiểm tra lại Detail, kể cả sau khi khởi động lại.'
        : 'Lỗi giá trị phải sửa đúng ô trong file PL.03 nguồn rồi upload lại.';
    reviewGuide.innerHTML = `<strong>Kiểm tra ở đâu?</strong><span>Màn hình đang ưu tiên các dòng cần xử lý. Cột “Lý do / xử lý” ghi rõ lỗi và cách xử lý. ${esc(location)}</span>${pendingBerth && item.sourceKind === 'tos_cargo_detail' ? `<button type="button" class="outline-button" data-open-required-berth="${pendingBerth.id}">Mở Berth #${pendingBerth.id}</button>` : ''}`;
    const requiredBerth = $('[data-open-required-berth]', reviewGuide);
    if (requiredBerth) requiredBerth.onclick = () => openHistoricalImport(Number(requiredBerth.dataset.openRequiredBerth));
  }
  const isPreview = item.status === 'PREVIEWED';
  $('.historical-confirm-area').hidden = !isPreview;
  $('#keep-historical-existing').hidden = !conflicts.length;
  $('#historical-revision-reason').hidden = !conflicts.length;
  $('#confirm-historical-import').textContent = conflicts.length
    ? 'Dùng file mới · tạo revision'
    : item.sourceKind === 'tos_berth_call'
      ? 'Xác nhận Berth & ghép Detail'
      : item.sourceKind === 'tos_cargo_detail'
        ? 'Ghi nhận Detail · chờ Berth'
        : 'Xác nhận import';
  const filters = {all: `Tất cả (${number(item.accepted) + number(item.review) + number(item.rejected)})`, review: `Cần xử lý (${number(item.review)})`, rejected: `Bị loại (${number(item.rejected)})`};
  $$('[data-historical-row-filter]').forEach(button => {
    button.textContent = filters[button.dataset.historicalRowFilter];
    button.classList.toggle('active', button.dataset.historicalRowFilter === state.historicalRowFilter);
    button.disabled = button.dataset.historicalRowFilter === 'review' ? !item.review : button.dataset.historicalRowFilter === 'rejected' ? !item.rejected : false;
    button.onclick = () => {
      state.historicalRowFilter = button.dataset.historicalRowFilter;
      state.historicalPreviewPage = 1;
      renderHistoricalImportWorkspace();
    };
  });
  updateHistoricalSteps(item);
  await Promise.all([loadHistoricalPreviewRows(state.historicalPreviewPage), loadHistoricalVesselLinks()]);
}

async function loadHistoricalPreviewRows(page = 1) {
  const item = state.historicalImport;
  if (!item) return;
  try {
    const status = state.historicalRowFilter === 'review' ? 'REVIEW' : state.historicalRowFilter === 'rejected' ? 'REJECTED' : '';
    const result = await api(`/api/historical-imports/${item.id}/rows?page=${page}&page_size=50${status ? `&status=${status}` : ''}`);
    state.historicalPreviewPage = result.page;
    const rows = result.items || [];
    let headers;
    let body;
    if (item.sourceKind === 'tos_berth_call') {
      headers = '<th>Dòng</th><th>Phương tiện / chuyến</th><th>Bến đến & rời</th><th>ATB</th><th>ATD</th><th>Kết quả</th><th>Lý do / xử lý</th>';
      body = rows.map(row => `<tr><td data-label="Dòng">${row.sourceRow}</td><td data-label="Phương tiện / chuyến"><strong>${esc(row.vesselName)}</strong><br><small>${esc(row.year)} · chuyến ${esc(row.voyage)}</small></td><td data-label="Bến đến & rời">${esc(row.berth || '—')}</td><td data-label="ATB">${esc(row.atb || '—')}</td><td data-label="ATD">${esc(row.atd || '—')}</td><td data-label="Kết quả"><span class="table-badge ${row.validationStatus === 'VALID' ? 'submitted' : row.validationStatus === 'REJECTED' ? 'danger' : 'draft'}">${row.validationStatus === 'VALID' ? 'Hợp lệ' : row.validationStatus === 'REJECTED' ? 'Bị loại' : 'Cần xử lý'}</span></td><td data-label="Lý do / xử lý">${historicalWarningCell(row)}</td></tr>`).join('');
    } else if (item.sourceKind === 'tos_cargo_detail') {
      headers = '<th>Dòng</th><th>Khóa chuyến</th><th>Container</th><th>Luồng hàng</th><th>Trọng lượng</th><th>Ghép lượt</th><th>Kết quả</th><th>Lý do / xử lý</th>';
      body = rows.map(row => `<tr><td data-label="Dòng">${row.sourceRow}</td><td data-label="Khóa chuyến">${esc(row.sourceCallKey)}</td><td data-label="Container">${esc(row.size)} · ${esc(row.fullEmpty)} · ${row.teuFactor || '—'} TEU</td><td data-label="Luồng hàng">${esc(row.trade || '—')} · ${esc(row.direction || '—')}</td><td data-label="Trọng lượng">${row.weightTonnes == null ? '—' : `${number(row.weightTonnes).toLocaleString('vi-VN')} tấn`}</td><td data-label="Ghép lượt"><span class="table-badge ${row.matchStatus === 'MATCHED' ? 'submitted' : 'draft'}">${row.matchStatus === 'MATCHED' ? 'Đã ghép' : 'Chưa ghép'}</span></td><td data-label="Kết quả"><span class="table-badge ${row.validationStatus === 'VALID' ? 'submitted' : row.validationStatus === 'REJECTED' ? 'danger' : 'draft'}">${row.validationStatus === 'VALID' ? 'Hợp lệ' : row.validationStatus === 'REJECTED' ? 'Bị loại' : 'Cần xử lý'}</span></td><td data-label="Lý do / xử lý">${historicalWarningCell(row)}</td></tr>`).join('');
    } else {
      headers = '<th>Dòng</th><th>STT báo cáo</th><th>Phương tiện</th><th>Số đăng ký</th><th>Kết quả</th><th>Lý do / xử lý</th>';
      body = rows.map(row => `<tr><td data-label="Dòng">${row.sourceRow}</td><td data-label="STT báo cáo">${row.appendixRowNo}</td><td data-label="Phương tiện">${esc(row.dimensions?.vesselNameRaw || '—')}</td><td data-label="Số đăng ký">${esc(row.dimensions?.registrationRaw || '—')}</td><td data-label="Kết quả"><span class="table-badge ${row.validationStatus === 'VALID' ? 'submitted' : 'draft'}">${row.validationStatus === 'VALID' ? 'Hợp lệ' : 'Cần xử lý'}</span></td><td data-label="Lý do / xử lý">${historicalWarningCell(row)}</td></tr>`).join('');
    }
    $('#historical-preview-table').innerHTML = rows.length
      ? `<table class="data-table responsive-table historical-preview-table"><thead><tr>${headers}</tr></thead><tbody>${body}</tbody></table>`
      : empty('Không có dòng preview', 'File không có dòng nghiệp vụ phù hợp với cấu trúc đã nhận diện.');
    renderHistoricalPagination($('#historical-preview-pagination'), result, 'historical-preview-page', loadHistoricalPreviewRows);
  } catch (error) { toast(error.message, true); }
}

async function loadHistoricalVesselLinks() {
  const item = state.historicalImport;
  const section = $('#historical-link-review');
  if (!item || item.sourceKind !== 'tos_berth_call') { section.hidden = true; return; }
  try {
    const [links, register] = await Promise.all([
      api(`/api/historical-imports/${item.id}/vessel-links?status=PENDING&page=1&page_size=200`),
      state.historicalRegisterItems.length ? Promise.resolve({items: state.historicalRegisterItems}) : api('/api/port-vessel-register'),
    ]);
    state.historicalRegisterItems = register.items || [];
    section.hidden = !links.items?.length;
    if (!links.items?.length) return;
    $('#historical-link-list').innerHTML = links.items.map(link => {
      const suggested = link.candidateVesselId
        ? `<strong>${esc(link.candidateVesselName)}</strong><small>${esc(link.candidateRegistration || '')} · ${link.matchMethod === 'EXACT' ? 'Khớp chính xác' : 'Khớp sau chuẩn hóa'}</small>`
        : `<label class="sr-only" for="historical-link-${link.id}">Chọn phương tiện cho ${esc(link.rawVesselName)}</label><select id="historical-link-${link.id}" data-historical-link-select="${link.id}"><option value="">Chọn trong Sổ theo dõi</option>${state.historicalRegisterItems.map(vessel => `<option value="${vessel.id}">${esc(vessel.name)} · ${esc(vessel.registration_no)}</option>`).join('')}</select>`;
      return `<div class="historical-link-row"><div><strong>${esc(link.rawVesselName)}</strong><small>${esc(link.reason || 'Cần xác nhận liên kết')}</small></div><div>${suggested}</div><div class="historical-link-actions"><button type="button" class="outline-button" data-reject-historical-link="${link.id}">Không đúng</button><button type="button" class="primary-button" data-accept-historical-link="${link.id}" data-candidate-id="${link.candidateVesselId || ''}">Xác nhận</button></div></div>`;
    }).join('');
    $$('[data-accept-historical-link]', section).forEach(button => button.onclick = () => {
      const linkId = Number(button.dataset.acceptHistoricalLink);
      const selected = Number(button.dataset.candidateId || $(`[data-historical-link-select="${linkId}"]`)?.value || 0);
      if (!selected) { toast('Chọn một phương tiện trong Sổ theo dõi trước khi xác nhận.', true); return; }
      resolveHistoricalVesselLink(linkId, 'ACCEPT', selected);
    });
    $$('[data-reject-historical-link]', section).forEach(button => button.onclick = () => resolveHistoricalVesselLink(Number(button.dataset.rejectHistoricalLink), 'REJECT'));
  } catch (error) { section.hidden = true; toast(error.message, true); }
}

async function resolveHistoricalVesselLink(linkId, decision, candidateVesselId = null) {
  try {
    await api(`/api/historical-imports/${state.historicalImport.id}/vessel-links/${linkId}/resolve`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({decision, candidate_vessel_id: candidateVesselId, reason: decision === 'ACCEPT' ? 'Nhân viên Cảng xác nhận trên preview.' : 'Nhân viên Cảng xác nhận không đúng phương tiện.'}),
    });
    state.historicalImport = await api(`/api/historical-imports/${state.historicalImport.id}`);
    const batchEntry = state.historicalBatch.find(entry => entry.result?.id === state.historicalImport.id);
    if (batchEntry) batchEntry.result = state.historicalImport;
    renderHistoricalBatch();
    await renderHistoricalImportWorkspace();
    await loadHistoricalImportHistory();
    toast(decision === 'ACCEPT' ? 'Đã xác nhận liên kết phương tiện.' : 'Đã từ chối liên kết phương tiện.');
  } catch (error) { toast(error.message, true); }
}

async function confirmHistoricalImport(action = null) {
  const item = state.historicalImport;
  if (!item) return;
  const reason = $('#historical-revision-reason-input').value.trim();
  if (action === 'ACTIVATE_NEW_REVISION' && reason.length < 5) {
    toast('Ghi lý do cụ thể trước khi dùng file mới làm revision đang hoạt động.', true);
    $('#historical-revision-reason-input').focus();
    return;
  }
  const button = action === 'KEEP_EXISTING' ? $('#keep-historical-existing') : $('#confirm-historical-import');
  const original = button.textContent;
  button.disabled = true;
  button.textContent = 'Đang xác nhận…';
  try {
    const payload = action ? {conflict_action: action, reason: reason || 'Người dùng chọn giữ bản đang dùng.'} : {};
    const result = await api(`/api/historical-imports/${item.id}/confirm`, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
    });
    state.historicalImport = await api(`/api/historical-imports/${result.id}`);
    await refreshHistoricalBatch();
    await renderHistoricalImportWorkspace();
    await loadHistoricalImportHistory();
    toast(result.status === 'REVIEW' ? 'Đã ghi nhận; các dòng cần kiểm tra vẫn chưa được đưa vào báo cáo.' : result.status === 'REJECTED' ? 'Đã giữ bản đang dùng; file preview không được kích hoạt.' : 'Đã kích hoạt dữ liệu lịch sử.');
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; button.textContent = original; }
}

async function cancelHistoricalImport() {
  const item = state.historicalImport;
  if (!item || item.status !== 'PREVIEWED') return;
  try {
    await api(`/api/historical-imports/${item.id}/cancel`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({reason: 'Người dùng hủy sau khi xem preview.'}),
    });
    await refreshHistoricalBatch();
    state.historicalImport = null;
    $('#historical-preview').hidden = true;
    updateHistoricalSteps(null);
    await loadHistoricalImportHistory();
    toast('Đã hủy lượt import; không có dữ liệu lịch sử nào được kích hoạt.');
  } catch (error) { toast(error.message, true); }
}

async function loadHistoricalImportHistory(page = state.historicalHistoryPage) {
  if (state.importMode !== 'historical' || !state.activeReportingUnitId) return;
  ensureHistoricalExportPanel();
  const container = $('#historical-import-history');
  container.innerHTML = '<div class="empty-state">Đang tải lịch sử import…</div>';
  try {
    await api('/api/historical-imports/reconcile', {method: 'POST'});
    const result = await api(`/api/historical-imports?page=${page}&page_size=20`);
    state.historicalHistoryPage = result.page;
    state.historicalHistory = result.items || [];
    const activeBerthPeriods = result.activeBerthPeriods || [];
    renderHistoricalHistorySummary(result.summary);
    if ($('#historical-pl03-month') && !pl03PeriodValue()) {
      setPl03Period(state.historicalHistory.find(item => item.sourceKind === 'tos_berth_call' && item.reportingPeriod)?.reportingPeriod || '');
    }
    container.innerHTML = state.historicalHistory.length
      ? `<table class="data-table responsive-table"><thead><tr><th>Mã</th><th>Nguồn</th><th>Kỳ</th><th>Kết quả</th><th>Revision</th><th>Trạng thái</th><th></th></tr></thead><tbody>${state.historicalHistory.map(item => `<tr><td data-label="Mã">#${item.id}<br><small>${fmtDate(item.createdAt)}</small></td><td data-label="Nguồn"><strong>${esc(HISTORICAL_SOURCE_LABELS[item.sourceKind] || item.sourceKind)}</strong><br><small title="${esc(item.sourceFilename)}">${esc(item.sourceFilename)}</small></td><td data-label="Kỳ">${esc(historicalEffectivePeriod(item, activeBerthPeriods))}</td><td data-label="Kết quả">${historicalResultCell(item)}</td><td data-label="Revision">${historicalRevCell(item)}</td><td data-label="Trạng thái" class="historical-status"><span class="table-badge ${historicalStatusTone(item.status)}">${esc(HISTORICAL_STATUS_LABELS[item.status] || item.status)}</span></td><td data-label="Thao tác" class="historical-history-action"><button type="button" class="outline-button" data-open-historical-import="${item.id}">${item.status === 'PREVIEWED' ? 'Tiếp tục' : 'Xem'}</button></td></tr>`).join('')}</tbody></table>`
      : empty('Chưa có dữ liệu lịch sử', 'Chọn một file TOS hoặc PL.03 cũ để tạo preview đầu tiên.');
    $$('[data-open-historical-import]', container).forEach(button => button.onclick = () => openHistoricalImport(Number(button.dataset.openHistoricalImport)));
    renderHistoricalPagination($('#historical-history-pagination'), result, 'historical-history-page', loadHistoricalImportHistory);
  } catch (error) {
    container.innerHTML = empty('Không thể tải lịch sử import', error.message);
    toast(error.message, true);
  }
}

// Authenticated download: plain `location.href` navigation cannot carry the
// Bearer token, so the request would 401. Fetch the file through api() (which
// attaches the token and already returns a Blob for non-JSON responses), then
// trigger the browser's save dialog from an object URL.
async function downloadFile(path, filename) {
  const blob = await api(path);
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

async function exportReport(kind) {
  let from = $('#report-from').value || '1900-01-01';
  let to = $('#report-to').value || '2999-12-31';
  if (kind === 'appendix2') {
    const month = $('#report-month').value;
    if (!month) { toast('Vui lòng chọn tháng báo cáo PL.02.', true); return; }
    const [year, monthNumber] = month.split('-').map(Number);
    from = `${month}-01`;
    to = new Date(Date.UTC(year, monthNumber, 0)).toISOString().slice(0, 10);
  }
  try {
    await downloadFile(`/api/reports/${kind}?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`, `report_${kind}_${from}_${to}.xlsx`);
  } catch (error) { toast(error.message, true); }
}

async function loadReportAdjustments() {
  const month = $('#report-month').value;
  if (!month || !['PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role)) return;
  const items = await api(`/api/reports/appendix2/adjustments?report_month=${encodeURIComponent(month)}`);
  $('#report-adjustment-history').innerHTML = items.length
    ? `<table class="data-table responsive-table"><thead><tr><th>Thời gian</th><th>Chỉ tiêu</th><th>Delta</th><th>Lý do</th></tr></thead><tbody>${items.map(item => `<tr><td data-label="Thời gian">${fmtDate(item.created_at)}</td><td data-label="Chỉ tiêu">${item.metric === 'calls' ? 'Lượt tàu' : 'Lượt tàu khách'}</td><td data-label="Delta">${item.delta > 0 ? '+' : ''}${item.delta}</td><td data-label="Lý do">${esc(item.reason)}</td></tr>`).join('')}</tbody></table>`
    : 'Chưa có điều chỉnh trong tháng.';
}

async function saveReportAdjustment(event) {
  event.preventDefault();
  const data = values(event.currentTarget);
  try {
    await api('/api/reports/appendix2/adjustments', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({...data, delta:Number(data.delta)})});
    event.currentTarget.elements.delta.value = '';
    event.currentTarget.elements.reason.value = '';
    await loadReportAdjustments();
    toast('Đã ghi điều chỉnh PL.02 vào nhật ký audit.');
  } catch (error) { toast(error.message, true); }
}

async function loadIntegration() {
  try {
    const data = await api('/api/integrations/maritime-authority');
    const badge = $('#integration-status');
    badge.className = `state-badge ${data.connector.readyToSend ? 'ok' : 'pending'}`;
    badge.textContent = data.connector.readyToSend ? 'Sẵn sàng kết nối' : 'Chờ đặc tả API';
    $('#sync-jobs').innerHTML = data.jobs.length ? `<table class="data-table responsive-table"><thead><tr><th>Mã</th><th>Kỳ dữ liệu</th><th>Số bản ghi</th><th>Trạng thái</th><th>Thời gian</th></tr></thead><tbody>${data.jobs.map(job => `<tr><td data-label="Mã">SYNC-${job.id}</td><td data-label="Kỳ dữ liệu">${esc(job.report_from)} → ${esc(job.report_to)}</td><td data-label="Số bản ghi">${job.record_count}</td><td data-label="Trạng thái"><span class="table-badge draft">${esc(job.status)}</span></td><td data-label="Thời gian">${fmtDate(job.created_at)}</td></tr>`).join('')}</tbody></table>` : empty('Chưa có gói đồng bộ', 'Chọn kỳ báo cáo và chuẩn bị payload để kiểm tra trước khi kết nối API chính thức.');
  } catch (error) { toast(error.message, true); }
}

const ANALYTICS_KPIS = [['trips', 'Lượt tàu'], ['tons', 'Khối lượng (tấn)'], ['teu', 'TEU'], ['pax', 'Hành khách']];
const ANALYTICS_SOURCE_LABELS = {live:'LIVE · Phiếu đã duyệt', historical:'LỊCH SỬ · TOS', combined:'KẾT HỢP'};
const ANALYTICS_COVERAGE_LABELS = {COMPLETE:'Đầy đủ', PARTIAL:'Một phần', MISSING:'Thiếu dữ liệu', BLOCKED:'Đang khóa'};

function renderAnalyticsUnavailable() {
  $('#analytics-title').textContent = 'Thống kê sản lượng';
  $('#analytics-unavailable').hidden = false;
  $('#analytics-coverage').hidden = true;
  $('#analytics-combined-blocked').hidden = true;
  $('#kpi-grid').hidden = true;
  $('.analytics-split').hidden = true;
  $$('.period-switch button').forEach(button => {
    button.disabled = true;
    button.onclick = null;
  });
  $('#export-analytics').disabled = true;
}

function analyticsDelta(cur, prev) {
  const pct = prev ? ((cur - prev) / prev) * 100 : 0;
  const up = pct >= 0;
  return { up, txt: `${up ? '▲' : '▼'} ${Math.abs(pct).toFixed(1).replace('.', ',')}%` };
}

function renderAnalyticsCoverage(data) {
  const coverage = data.coverage || {status:'MISSING', periods:[], warnings:[]};
  const internal = ['PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role);
  $('#analytics-source-controls').hidden = !internal;
  $$('.analytics-source-switch button').forEach(button => {
    button.classList.toggle('active', button.dataset.source === data.source);
    button.setAttribute('aria-pressed', button.dataset.source === data.source ? 'true' : 'false');
    button.onclick = () => loadReportAnalytics(data.period, button.dataset.source);
  });
  const coveragePanel = $('#analytics-coverage');
  coveragePanel.hidden = data.source === 'live' && !internal;
  $('#analytics-coverage-status').textContent = ANALYTICS_COVERAGE_LABELS[coverage.status] || coverage.status;
  $('#analytics-coverage-status').className = `table-badge ${coverage.status === 'COMPLETE' ? 'submitted' : 'draft'}`;
  $('#analytics-coverage-title').textContent = (ANALYTICS_SOURCE_LABELS[data.source] || data.source).split(' · ')[0];
  coveragePanel.title = (coverage.warnings || []).join(' ');
  $('#analytics-coverage-periods').innerHTML = (coverage.periods || [])
    .filter(item => item.overlap || number(item.liveApproved) || number(item.historicalCalls) || number(item.historicalCargoRows))
    .map(item => {
      const facts = [];
      if (number(item.liveApproved)) facts.push(`LIVE ${number(item.liveApproved).toLocaleString('vi-VN')}`);
      if (number(item.historicalCalls)) facts.push(`TOS ${number(item.historicalCalls).toLocaleString('vi-VN')} lượt`);
      if (number(item.historicalCargoRows)) facts.push(`${number(item.historicalCargoRows).toLocaleString('vi-VN')} dòng`);
      return `<span class="coverage-period ${item.overlap ? 'overlap' : ''}"><strong>${esc(item.month)}</strong><span>${facts.join(' · ')}</span>${item.overlap ? '<b>ĐỐI SOÁT</b>' : ''}</span>`;
    }).join('');
}

async function loadReportAnalytics(period = 'month', source = state.analyticsSource) {
  try {
    const allowedSource = ['PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role) ? source : 'live';
    const data = await api(`/api/reports/analytics?period=${period}&source=${allowedSource}`);
    state.analyticsSource = data.source;
    $('#analytics-unavailable').hidden = true;
    $('#analytics-demo-notice').hidden = data.dataSource !== 'DEMO';
    renderAnalyticsCoverage(data);
    const blocked = data.combinedAllowed === false;
    $('#analytics-combined-blocked').hidden = !blocked;
    $('#kpi-grid').hidden = blocked;
    $('.analytics-split').hidden = blocked;
    $('#export-analytics').disabled = blocked;
    const fmt = value => number(value).toLocaleString('vi-VN');
    $$('.period-switch button').forEach(button => {
      button.classList.toggle('active', button.dataset.period === data.period);
      button.onclick = () => loadReportAnalytics(button.dataset.period, state.analyticsSource);
    });
    const meta = data.meta || {};
    $('#analytics-title').textContent = meta.analyticsTitle || '';
    $('#trend-title').textContent = meta.trendTitle || '';
    $('#trend-sub').textContent = meta.trendSub || '';
    $('#compare-sub').textContent = meta.compareSub || '';
    $('#kpi-grid').innerHTML = ANALYTICS_KPIS.map(([key, label]) => {
      const kpi = data.kpis[key] || { cur: 0, prev: 0 };
      if (kpi.cur === null || kpi.cur === undefined) {
        return `<article class="kpi-card incomplete"><p>${label.toUpperCase()}</p><div class="kpi-value"><strong>—</strong></div><small>Chưa đủ độ phủ để tính</small></article>`;
      }
      const delta = analyticsDelta(kpi.cur, kpi.prev);
      const prior = kpi.prev === null || kpi.prev === undefined ? 'Chưa đủ dữ liệu' : fmt(kpi.prev);
      return `<article class="kpi-card"><p>${label.toUpperCase()}</p><div class="kpi-value"><strong>${fmt(kpi.cur)}</strong>${kpi.prev === null || kpi.prev === undefined ? '' : `<span class="kpi-delta ${delta.up ? 'up' : 'down'}">${delta.txt}</span>`}</div><small>Cùng kỳ: ${prior}</small></article>`;
    }).join('');
    const trend = data.trend || { labels: [], cur: [], prev: [] };
    const max = Math.max(...trend.cur, ...trend.prev, 1);
    $('#trend-chart').innerHTML = trend.labels.map((label, i) => `<div class="trend-col"><div class="trend-bars"><span class="trend-bar cur" style="height:${Math.round((trend.cur[i] || 0) / max * 100)}%"></span><span class="trend-bar prev" style="height:${Math.round((trend.prev[i] || 0) / max * 100)}%"></span></div><small>${esc(label)}</small></div>`).join('');
    $('#compare-body').innerHTML = ANALYTICS_KPIS.map(([key, label]) => {
      const kpi = data.kpis[key] || { cur: 0, prev: 0 };
      if (kpi.cur === null || kpi.prev === null || kpi.cur === undefined || kpi.prev === undefined) {
        return `<tr><td>${label}</td><td>${kpi.cur == null ? '—' : fmt(kpi.cur)}</td><td>${kpi.prev == null ? '—' : fmt(kpi.prev)}</td><td class="muted">Chưa đủ dữ liệu</td></tr>`;
      }
      const delta = analyticsDelta(kpi.cur, kpi.prev);
      return `<tr><td>${label}</td><td>${fmt(kpi.cur)}</td><td>${fmt(kpi.prev)}</td><td class="compare-delta ${delta.up ? 'up' : 'down'}">${delta.txt}</td></tr>`;
    }).join('');
  } catch (error) {
    renderAnalyticsUnavailable();
    $('#analytics-unavailable').querySelector('p').textContent = error.message;
    toast(error.message, true);
  }
}

function exportAnalyticsReport() {
  const period = $('.period-switch button.active')?.dataset.period || 'month';
  downloadFile(`/api/reports/analytics/export?period=${period}&source=${state.analyticsSource}`, `bao_cao_tong_hop_${state.analyticsSource}_${period}_${new Date().toISOString().slice(0, 10)}.xlsx`)
    .catch(error => toast(error.message, true));
}

function fmtBytes(bytes) {
  if (!bytes) return '0 KB';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes, i = 0;
  while (value >= 1024 && i < units.length - 1) { value /= 1024; i += 1; }
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

async function loadBackupHistory() {
  try {
    const backups = await api('/api/admin/backups');
    $('#backup-history').innerHTML = backups.length ? `<table class="data-table responsive-table"><thead><tr><th>Tệp</th><th>Thời gian</th><th>Dung lượng</th><th>Toàn vẹn</th></tr></thead><tbody>${backups.map(item => `<tr><td data-label="Tệp">${esc(item.filename)}</td><td data-label="Thời gian">${fmtDate(item.createdAt)}</td><td data-label="Dung lượng">${fmtBytes(item.sizeBytes)}</td><td data-label="Toàn vẹn"><span class="table-badge ${item.integrityCheck === 'ok' ? 'submitted' : 'draft'}">${esc(item.integrityCheck || 'Không rõ')}</span></td></tr>`).join('')}</tbody></table>` : empty('Chưa có bản sao lưu', 'Bấm "Backup ngay" hoặc chờ tác vụ tự động lúc 2:00 sáng hằng ngày.');
  } catch (error) { toast(error.message, true); }
}

async function triggerBackup() {
  const button = $('#trigger-backup');
  button.disabled = true;
  const originalLabel = button.textContent;
  button.textContent = 'Đang sao lưu…';
  try {
    const result = await api('/api/admin/backups', {method: 'POST'});
    toast(`Đã tạo bản sao lưu ${result.filename}${result.pruned ? ` (đã dọn ${result.pruned} bản cũ)` : ''}.`);
    await loadBackupHistory();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; button.textContent = originalLabel; }
}

async function prepareSync() {
  try {
    const result = await api('/api/integrations/prepare-sync', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({from:$('#report-from').value,to:$('#report-to').value})});
    toast(`Đã chuẩn bị SYNC-${result.id} gồm ${result.recordCount} bản ghi. Chưa gửi ra ngoài.`);
    await loadIntegration();
  } catch (error) { toast(error.message, true); }
}

// ── Thông tin khách hàng / Tổ chức (PLATFORM_ADMIN) ──────────────────────────
async function loadOrganizations() {
  const table = $('#organizations-table');
  $('#main-content').setAttribute('aria-busy', 'true');
  try {
    state.organizations = await api('/api/organizations');
    renderOrganizations();
  } catch (error) {
    table.innerHTML = empty('Không tải được danh sách', error.message);
  } finally { $('#main-content').setAttribute('aria-busy', 'false'); }
}

function renderOrganizations() {
  const table = $('#organizations-table');
  if (!state.organizations.length) { table.innerHTML = empty('Chưa có tổ chức', 'Thêm tổ chức khách hàng đầu tiên để có thể cấp tài khoản Khách hàng.'); return; }
  table.innerHTML = `<table class="data-table responsive-table"><thead><tr><th>Tổ chức</th><th>Mã số thuế</th><th>Liên hệ</th><th aria-label="Thao tác"></th></tr></thead><tbody>${state.organizations.map(o => `<tr><td data-label="Tổ chức"><strong>${esc(o.name)}</strong>${o.address ? `<br><small>${esc(o.address)}</small>` : ''}</td><td data-label="Mã số thuế">${esc(o.tax_code || '—')}</td><td data-label="Liên hệ">${o.contact_name ? esc(o.contact_name) : '—'}${o.phone ? `<br><small>${esc(o.phone)}</small>` : ''}</td><td data-label="Thao tác" class="user-actions"><button type="button" class="table-link" data-edit-organization="${o.id}">Sửa</button></td></tr>`).join('')}</tbody></table>`;
  $$('[data-edit-organization]', table).forEach(button => button.onclick = () => openOrganization(Number(button.dataset.editOrganization)));
}

function openOrganization(orgId = null) {
  const form = $('#organization-form');
  form.reset();
  state.editingOrganization = orgId;
  const org = orgId ? state.organizations.find(o => o.id === orgId) : null;
  $('#organization-dialog-title').textContent = org ? 'Sửa tổ chức khách hàng' : 'Thêm tổ chức khách hàng';
  $('#save-organization').textContent = org ? 'Lưu thay đổi' : 'Lưu tổ chức';
  if (org) ['name', 'tax_code', 'address', 'contact_name', 'contact_role', 'phone', 'email'].forEach(key => { if (form.elements[key]) form.elements[key].value = org[key] || ''; });
  $('#organization-dialog').showModal();
  requestAnimationFrame(() => form.elements.name.focus());
}

async function submitOrganization(event) {
  event.preventDefault();
  const form = event.target;
  setSubmitting(form, event.submitter, true, 'Đang lưu…');
  const orgId = state.editingOrganization;
  try {
    const saved = await api(orgId ? `/api/organizations/${orgId}` : '/api/organizations', {
      method: orgId ? 'PUT' : 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(values(form)),
    });
    $('#organization-dialog').close();
    toast(orgId ? `Đã cập nhật ${saved.name}.` : `Đã thêm tổ chức ${saved.name}.`);
    await loadOrganizations();
  } catch (error) {
    toast(error.message, true);
  } finally { setSubmitting(form, event.submitter, false); }
}

// ── Quản lý người dùng (PLATFORM_ADMIN) ──────────────────────────────────────
const USER_ROLE_LABELS = { CUSTOMER: 'Khách hàng', PORT_STAFF: 'Nhân viên Cảng', PLATFORM_ADMIN: 'Platform Admin' };

async function loadUsers() {
  const table = $('#users-table');
  $('#main-content').setAttribute('aria-busy', 'true');
  try {
    const data = await api('/api/admin/users');
    state.users = data.items || [];
    renderUsers();
  } catch (error) {
    table.innerHTML = empty('Không tải được danh sách', error.message);
  } finally { $('#main-content').setAttribute('aria-busy', 'false'); }
}

function userScopeCell(item) {
  if (item.role === 'CUSTOMER') return esc(item.organization_name || '—');
  if (item.role === 'PORT_STAFF') return item.reporting_units.length ? item.reporting_units.map(u => esc(u.name)).join(', ') : '<span class="muted">Chưa cấp đơn vị</span>';
  return '<span class="muted">Toàn hệ thống</span>';
}

function renderUsers() {
  const table = $('#users-table');
  if (!state.users.length) { table.innerHTML = empty('Chưa có người dùng', 'Tạo tài khoản đầu tiên cho nhân viên hoặc khách hàng.'); return; }
  table.innerHTML = `<table class="data-table responsive-table"><thead><tr><th>Tài khoản</th><th>Vai trò</th><th>Phạm vi</th><th>Trạng thái</th><th aria-label="Thao tác"></th></tr></thead><tbody>${state.users.map(item => `<tr><td data-label="Tài khoản"><strong>${esc(item.username)}</strong><br><small>${esc(item.full_name || '—')}</small></td><td data-label="Vai trò">${esc(USER_ROLE_LABELS[item.role] || item.role)}</td><td data-label="Phạm vi">${userScopeCell(item)}</td><td data-label="Trạng thái"><span class="table-badge ${item.is_active ? 'submitted' : 'draft'}">${item.is_active ? 'Đang hoạt động' : 'Đã khóa'}</span></td><td data-label="Thao tác" class="user-actions"><button type="button" class="table-link" data-reset-user="${item.id}">Đặt lại mật khẩu</button>${item.id === state.currentUser?.id ? '' : ` · <button type="button" class="table-link ${item.is_active ? 'danger-link' : ''}" data-toggle-user="${item.id}">${item.is_active ? 'Khóa' : 'Mở khóa'}</button>`}</td></tr>`).join('')}</tbody></table>`;
  $$('[data-reset-user]', table).forEach(button => button.onclick = () => openResetPassword(Number(button.dataset.resetUser)));
  $$('[data-toggle-user]', table).forEach(button => button.onclick = () => toggleUserActive(Number(button.dataset.toggleUser)));
}

async function toggleUserActive(userId) {
  const item = state.users.find(u => u.id === userId);
  if (!item) return;
  const next = !item.is_active;
  if (!next && !confirm(`Khóa tài khoản "${item.username}"? Người dùng sẽ không đăng nhập được.`)) return;
  try {
    const updated = await api(`/api/admin/users/${userId}/active`, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ is_active: next }),
    });
    Object.assign(item, updated);
    renderUsers();
    toast(next ? `Đã mở khóa ${updated.username}.` : `Đã khóa ${updated.username}.`);
  } catch (error) { toast(error.message, true); }
}

function refreshUserFormScope(role) {
  const orgField = $('#user-org-field');
  const unitsField = $('#user-units-field');
  const orgSelect = orgField.querySelector('select');
  orgField.hidden = role !== 'CUSTOMER';
  orgSelect.required = role === 'CUSTOMER';
  unitsField.hidden = role !== 'PORT_STAFF';
}

async function openCreateUser() {
  const form = $('#user-form');
  form.reset();
  const orgSelect = $('#user-org-field select');
  const unitsList = $('#user-units-list');
  orgSelect.innerHTML = '<option value="">Đang tải…</option>';
  unitsList.innerHTML = '';
  refreshUserFormScope(form.elements.role.value);
  $('#user-dialog').showModal();
  requestAnimationFrame(() => form.elements.role.focus());
  try {
    const [orgs, units] = await Promise.all([
      api('/api/organizations'),
      api('/api/reporting-units'),
    ]);
    orgSelect.innerHTML = orgs.length
      ? '<option value="">— Chọn tổ chức —</option>' + orgs.map(o => `<option value="${o.id}">${esc(o.name)}</option>`).join('')
      : '<option value="">— Chưa có tổ chức, thêm ở tab Thông tin khách hàng —</option>';
    unitsList.innerHTML = (units.items || []).length
      ? (units.items || []).map(u => `<label class="user-unit-option"><input type="checkbox" name="reporting_unit_ids" value="${u.id}"><span>${esc(u.name)}</span></label>`).join('')
      : '<p class="muted">Chưa có đơn vị báo cáo nào. Có thể cấp sau.</p>';
  } catch (error) {
    orgSelect.innerHTML = '<option value="">Không tải được tổ chức</option>';
    toast(error.message, true);
  }
}

async function submitCreateUser(event) {
  event.preventDefault();
  const form = event.target;
  setSubmitting(form, event.submitter, true, 'Đang tạo…');
  const fd = new FormData(form);
  const role = fd.get('role');
  const payload = {
    username: (fd.get('username') || '').trim(),
    password: fd.get('password'),
    full_name: (fd.get('full_name') || '').trim(),
    email: (fd.get('email') || '').trim(),
    role,
  };
  if (role === 'CUSTOMER') payload.organization_id = fd.get('organization_id') ? Number(fd.get('organization_id')) : null;
  if (role === 'PORT_STAFF') payload.reporting_unit_ids = fd.getAll('reporting_unit_ids').map(Number);
  try {
    const created = await api('/api/admin/users', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
    });
    $('#user-dialog').close();
    toast(`Đã tạo tài khoản ${created.username}.`);
    await loadUsers();
  } catch (error) {
    toast(error.message, true);
  } finally { setSubmitting(form, event.submitter, false); }
}

function openResetPassword(userId) {
  const item = state.users.find(u => u.id === userId);
  if (!item) return;
  const form = $('#reset-password-form');
  form.reset();
  form.dataset.userId = String(userId);
  $('#reset-password-target').textContent = `Tài khoản: ${item.username}${item.full_name ? ` (${item.full_name})` : ''}`;
  $('#reset-password-dialog').showModal();
  requestAnimationFrame(() => form.elements.password.focus());
}

async function submitResetPassword(event) {
  event.preventDefault();
  const form = event.target;
  const userId = Number(form.dataset.userId);
  setSubmitting(form, event.submitter, true, 'Đang lưu…');
  try {
    await api(`/api/admin/users/${userId}/reset-password`, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ password: form.elements.password.value }),
    });
    $('#reset-password-dialog').close();
    toast('Đã đặt lại mật khẩu.');
  } catch (error) {
    toast(error.message, true);
  } finally { setSubmitting(form, event.submitter, false); }
}

async function init() {
  if (!window.__tanThuanRouteBound) {
    window.addEventListener('hashchange', route);
    window.__tanThuanRouteBound = true;
  }
  $('#menu-toggle').onclick = () => setSidebarOpen(!$('.sidebar').classList.contains('open'));
  // Trên mobile, chạm ra ngoài sidebar (kể cả vùng nhập liệu) sẽ đóng drawer.
  $('#sidebar-backdrop').onclick = () => setSidebarOpen(false);
  $('#main-content').addEventListener('pointerdown', () => {
    if ($('.sidebar').classList.contains('open')) setSidebarOpen(false);
  });
  $('#theme-toggle').onclick = () => { const root = document.documentElement; const next = root.dataset.theme === 'dark' ? 'light' : 'dark'; root.dataset.theme = next; localStorage.setItem('tanthuan-theme', next); };
  document.documentElement.dataset.theme = localStorage.getItem('tanthuan-theme') || 'dark';
  bindLoginForm();

  // Setup logout handler
  $('#logout-button').onclick = async () => {
    try {
      await api('/api/auth/logout', { method: 'POST' });
    } catch (_) {}
    localStorage.removeItem('token');
    if (state.currentUser?.username) localStorage.removeItem(reportingUnitStorageKey());
    state.currentUser = null;
    location.reload();
  };

  // Load current user profile first (authentication barrier)
  try {
    state.currentUser = await api('/api/auth/me');
    $('#user-display').innerHTML = `<span class="role-pill" title="${esc(state.currentUser.username)}">${esc(roleLabel(state.currentUser.role))}</span>`;
    $('#logout-button').style.display = 'inline-block';

    // Role-based UI visibility constraints
    const isCustomer = state.currentUser.role === 'CUSTOMER';
    const isAdmin = state.currentUser.role === 'PLATFORM_ADMIN';
    const isReviewer = state.currentUser.role === 'PORT_STAFF';

    const canCreateDeclaration = isCustomer || isAdmin;
    $$('[data-action="new-declaration"]').forEach(btn => { btn.hidden = !canCreateDeclaration; });
    // PLATFORM_ADMIN có toàn quyền: vừa lưu nháp, vừa xác nhận gửi thay mặt
    // khách hàng mà không cần đăng nhập tài khoản khách hàng.
    $('#submit-declaration').hidden = !(isCustomer || isAdmin);
    $('#save-draft').textContent = isAdmin ? 'Lưu phiếu' : 'Lưu nháp';
    const reviewStrip = $('.review-strip');
    reviewStrip.querySelector('strong').textContent = isAdmin ? 'Kiểm tra kỹ thông tin' : 'Kiểm tra trước khi xác nhận';
    reviewStrip.querySelector('p').textContent = isAdmin
      ? 'Dấu * là bắt buộc.'
      : 'Dấu * là bắt buộc. Nếu phiếu có lỗi, liên hệ nhân viên Cảng để được hỗ trợ.';
    const addVesselBtn = $('#add-vessel');
    if (addVesselBtn) addVesselBtn.hidden = isReviewer || isCustomer;
    const addCrewBtn = $('#add-crew');
    if (addCrewBtn) addCrewBtn.hidden = false;

    if (isCustomer) {
      $$('nav a[data-route]').forEach(link => {
        link.hidden = !['declarations', 'crew'].includes(link.dataset.route);
      });
    }

    const importNav = $('nav a[href="#import"]');
    if (importNav) {
      importNav.style.removeProperty('display');
      importNav.hidden = !(isReviewer || isAdmin);
    }

    const reportsNav = $('nav a[href="#reports"]');
    if (reportsNav) {
      reportsNav.style.removeProperty('display');
      reportsNav.hidden = isCustomer;
    }

    const portRegisterNav = $('nav a[href="#port-register"]');
    if (portRegisterNav) portRegisterNav.hidden = !(isReviewer || isAdmin);

    const organizationsNav = $('nav a[href="#organizations"]');
    if (organizationsNav) organizationsNav.hidden = !isAdmin;

    const usersNav = $('nav a[href="#users"]');
    if (usersNav) usersNav.hidden = !isAdmin;

    $('.data-nav').hidden = isCustomer;
    $('#import-vessels-card').hidden = !(isReviewer || isAdmin);
    $('#import-crew-card').hidden = !(isReviewer || isAdmin);
    $('#import-declaration-card').hidden = !isAdmin;

    const integrationActions = $('#integration-admin-actions');
    const integrationJobs = $('#sync-jobs');
    if (integrationActions) integrationActions.hidden = !isAdmin;
    if (integrationJobs) integrationJobs.hidden = !isAdmin;
    $('#report-adjustment-panel').hidden = !(isReviewer || isAdmin);

  } catch (err) {
    state.currentUser = null;
    $('#user-display').innerHTML = '';
    $('#logout-button').style.display = 'none';
    showLoginDialog();
    return;
  }

  try {
    if (!await loadReportingUnitContext()) return;
  } catch (error) {
    $('#api-state').className = 'state-badge pending';
    $('#api-state').textContent = 'Lỗi phạm vi';
    toast(error.message, true);
    return;
  }

  const savedDeclarationQuery = new URLSearchParams(location.search);
  ['q','movement_type','workflow_status','master_name','from','to'].forEach(key => { if (savedDeclarationQuery.get(key)) state.declarationFilter[key] = savedDeclarationQuery.get(key); });
  state.declarationPage = Number(savedDeclarationQuery.get('page') || 1);
  const filterControls = {q: 'declaration-search', movement_type: 'movement-filter', workflow_status: 'workflow-filter', master_name: 'master-filter', from: 'declaration-from', to: 'declaration-to'};
  Object.entries(filterControls).forEach(([key, id]) => { if (state.declarationFilter[key]) $(`#${id}`).value = state.declarationFilter[key]; });
  $$('[data-route-link]').forEach(button => button.onclick = () => location.hash = button.dataset.routeLink);
  $$('[data-action="new-declaration"]').forEach(button => button.onclick = () => openDeclaration());
  $('#add-vessel').onclick = () => openVessel();
  $('#add-port-vessel').onclick = () => openVessel(null, true);
  $('#vessel-search').addEventListener('input', () => { state.vesselPage = 1; renderVessels(); });
  $('#port-register-search').addEventListener('input', () => {
    state.portRegisterPage = 1;
    state.portRegisterSelected.clear();
    renderPortRegister();
  });
  $('#remove-selected-port-vessels').onclick = () => removePortRegisterItems([...state.portRegisterSelected]);
  $('#export-port-register').onclick = () => downloadFile('/api/port-vessel-register/export', `DU_LIEU_SA_LAN_${new Date().toISOString().slice(0, 10)}.xlsx`).catch(error => toast(error.message, true));
  let dashboardTimer;
  $('#dashboard-vessel-search').addEventListener('input', event => {
    clearTimeout(dashboardTimer);
    const query = event.target.value.trim();
    const sequence = ++state.dashboardSearchSequence;
    if (query.length < 2) {
      renderDashboardMatches([]);
      return;
    }
    dashboardTimer = setTimeout(() => searchDashboardVessels(query, sequence), 300);
  });
  $('#crew-search').addEventListener('input', renderCrew);
  $('#vessel-form').addEventListener('submit', saveVessel);
  $('#crew-form').addEventListener('submit', saveCrew);
  $('#declaration-form').addEventListener('submit', saveDeclaration);
  $('#workflow-form').addEventListener('submit', saveWorkflow);
  $('#my-profile-form')?.addEventListener('submit', saveMyProfile);
  $('#port-email-form')?.addEventListener('submit', savePortEmail);
  $('#smtp-form')?.addEventListener('submit', saveSmtp);
  $('#smtp-test-btn')?.addEventListener('click', sendSmtpTest);
  $('#report-adjustment-form').addEventListener('submit', saveReportAdjustment);
  $('#report-month').addEventListener('change', event => {
    $('#report-adjustment-form').elements.report_month.value = event.target.value;
    loadReportAdjustments().catch(error => toast(error.message, true));
  });

  $('#add-crew').onclick = () => openCrew();
  $('#add-organization').onclick = () => openOrganization();
  $('#organization-form').addEventListener('submit', submitOrganization);
  $('#add-user').onclick = () => openCreateUser();
  $('#user-form').elements.role.addEventListener('change', event => refreshUserFormScope(event.target.value));
  $('#user-form').addEventListener('submit', submitCreateUser);
  $('#reset-password-form').addEventListener('submit', submitResetPassword);
  $$('[data-close-dialog]').forEach(button => button.onclick = () => document.getElementById(button.dataset.closeDialog).close());
  let declarationTimer;
  ['declaration-search','master-filter'].forEach(id => $(`#${id}`).addEventListener('input', () => { clearTimeout(declarationTimer); declarationTimer = setTimeout(applyDeclarationFilters, 250); }));
  ['movement-filter','workflow-filter','declaration-from','declaration-to'].forEach(id => $(`#${id}`).addEventListener('change', applyDeclarationFilters));
  $('#clear-declaration-filter').onclick = () => { ['declaration-search','movement-filter','workflow-filter','master-filter','declaration-from','declaration-to'].forEach(id => $(`#${id}`).value = ''); applyDeclarationFilters(); };
  $('#import-vessels').onchange = event => previewImport(event.target, '/api/import/vessels', 'vessels');
  $('#import-declaration').onchange = event => previewImport(event.target, '/api/import/declaration', 'declaration');
  $('#import-crew').onchange = event => previewImport(event.target, '/api/import/crew', 'crew');
  $('#import-port-register').onchange = event => previewImport(event.target, '/api/import/port-vessel-register', 'vessels');
  $('#operational-import-tab').onclick = () => setImportMode('operational');
  $('#historical-import-tab').onclick = () => setImportMode('historical');
  $$('.import-mode-tabs [role="tab"]').forEach(tab => tab.onkeydown = event => {
    if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault();
    const next = tab.id === 'operational-import-tab' ? $('#historical-import-tab') : $('#operational-import-tab');
    next.focus();
    next.click();
  });
  $('#import-historical').onchange = event => previewHistoricalImport(event.target);
  $('#close-historical-preview').onclick = () => { $('#historical-preview').hidden = true; };
  $('#cancel-historical-import').onclick = cancelHistoricalImport;
  $('#keep-historical-existing').onclick = () => confirmHistoricalImport('KEEP_EXISTING');
  $('#confirm-historical-import').onclick = () => confirmHistoricalImport(
    state.historicalImport?.conflictingImportIds?.length ? 'ACTIVATE_NEW_REVISION' : null
  );
  $('#refresh-historical-history').onclick = () => loadHistoricalImportHistory(1);
  $('#close-port-import').onclick = cancelImport;
  $$('[data-report]').forEach(button => button.onclick = () => exportReport(button.dataset.report));
  $('#export-analytics').onclick = exportAnalyticsReport;
  $('#trigger-backup').onclick = triggerBackup;
  $('#prepare-sync').onclick = prepareSync;
  const today = new Date(); $('#report-to').value = today.toISOString().slice(0,10); $('#report-from').value = `${today.getFullYear()}-01-01`;
  $('#report-month').value = today.toISOString().slice(0, 7);
  $('#report-adjustment-form').elements.report_month.value = $('#report-month').value;
  if (['PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role)) loadReportAdjustments().catch(error => toast(error.message, true));
  try {
    const organizationRequest = ['PORT_STAFF', 'PLATFORM_ADMIN'].includes(state.currentUser?.role)
      ? api('/api/reporting-unit/organizations') : Promise.resolve({items: []});
    const [catalogs, vessels, crew, organizations] = await Promise.all([
      api('/api/catalogs'), api('/api/vessels'), api('/api/crew'), organizationRequest,
    ]);
    state.catalogs = catalogs;
    state.vessels = vessels;
    state.crew = crew;
    state.reportingUnitOrganizations = organizations.items || [];
    $('#api-state').className = 'state-badge ok'; $('#api-state').textContent = 'Đã kết nối';
  } catch (error) { $('#api-state').className = 'state-badge pending'; $('#api-state').textContent = 'Mất kết nối'; toast(error.message, true); }
  refreshPendingBadge();
  setInterval(refreshPendingBadge, 60000);
  route();
}

document.addEventListener('DOMContentLoaded', init);
