const state = {
  catalogs: {}, vessels: [], declarations: [], crew: [],
  declarationFilter: {}, declarationPage: 1, declarationPaging: null, dashboardCertificateWarnings: 0, editingVessel: null, editingDeclaration: null, editingCrew: null, workflowDeclaration: null,
  wizardStep: 1, wizardMaxStep: 1, declarationVesselMode: 'existing', declarationNewCrew: [],
  pendingImport: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value = '') => String(value ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const number = value => Number(value || 0);
const fmtDate = value => value ? new Intl.DateTimeFormat('vi-VN', {dateStyle:'short', timeStyle: value.includes('T') ? 'short' : undefined}).format(new Date(value)) : '—';

async function api(path, options = {}) {
  const token = localStorage.getItem('token');
  if (token) {
    options.headers = { ...options.headers, 'Authorization': `Bearer ${token}` };
  }
  const response = await fetch(path, options);
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
      : details || 'Yêu cầu không thành công.';
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
      $('#login-dialog').close();
      toast('Đăng nhập thành công.');
      init();
    } catch (error) {
      setLoginFeedback(error.message || 'Không thể đăng nhập. Vui lòng thử lại.');
    } finally { setSubmitting(form, event.submitter, false); }
  });
}

function optionList(items = [], selected = '') {
  return `<option value="">Chọn</option>${items.map(item => `<option ${item === selected ? 'selected' : ''}>${esc(item)}</option>`).join('')}`;
}

const LAYOUT_CLASSES = ['wide-field', 'span-2', 'span-3'];

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

function values(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function pageName(route) {
  return ({dashboard:'Tổng quan khai báo', declarations:'Phiếu khai báo', vessels:'Hồ sơ phương tiện', crew:'Danh sách thuyền viên', import:'Import dữ liệu Excel', reports:'Báo cáo hoạt động Cảng'})[route] || 'Tổng quan khai báo';
}

function roleLabel(role) {
  return ({CUSTOMER:'User', PORT_STAFF:'Port staff', ADMIN:'Admin'})[role] || role;
}

function route() {
  const name = location.hash.replace('#', '') || 'dashboard';
  $$('.page').forEach(page => page.classList.toggle('active', page.dataset.page === name));
  $$('nav a').forEach(link => link.classList.toggle('active', link.dataset.route === name));
  $('#page-context').textContent = pageName(name);
  $('.sidebar').classList.remove('open');
  requestAnimationFrame(() => $('#main-content').focus({ preventScroll: true }));
  if (name === 'dashboard') loadDashboard();
  if (name === 'vessels') loadVessels();
  if (name === 'declarations') loadDeclarations();
  if (name === 'crew') loadCrew();
  if (name === 'reports') {
    loadReportAnalytics($('.period-switch button.active')?.dataset.period || 'month');
    if (state.currentUser?.role === 'ADMIN') loadIntegration();
  }
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
    if (state.currentUser?.role === 'ADMIN') {
      const admin = await api('/api/admin/operations-summary');
      const adminCards = [
        ['PHIẾU ĐÃ DUYỆT', admin.operations.approved, `${admin.operations.tons.toLocaleString('vi-VN')} tấn · ${admin.operations.teu.toLocaleString('vi-VN')} TEU`],
        ['CHỜ CẢNG XỬ LÝ', admin.operations.pending, 'Nhân viên Cảng xem xét hồ sơ'],
        ['CẢNH BÁO CHỨNG CHỈ', admin.fleet.certificateWarnings, `${admin.fleet.vessels} phương tiện`],
        ['IMPORT', admin.imports.jobs, `${admin.imports.rejectedRows} dòng bị từ chối`],
        ['BACKUP', admin.storage.backups, admin.storage.latestBackup || 'Chưa có backup'],
        ['AN NINH', admin.security.failedLogins, `${admin.security.disabledUsers} tài khoản bị khóa`],
      ];
      $('#admin-operations').hidden = false;
      $('#admin-operations-content').innerHTML = adminCards.map(card => `<article class="stat-card"><p>${card[0]}</p><strong>${card[1]}</strong><small>${esc(card[2])}</small></article>`).join('');
      $('#admin-backup').hidden = false;
      loadBackupHistory();
    } else {
      $('#admin-operations').hidden = true;
      $('#admin-backup').hidden = true;
    }
    $('#recent-table').innerHTML = declarationTable(data.recent);
    renderDashboardMatches(data.matches || []);
  } catch (error) { toast(error.message, true); }
  finally { $('#main-content').setAttribute('aria-busy', 'false'); }
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
  const control = $('#in-app-certificate-reminders');
  control.checked = state.currentUser?.notification_preferences?.in_app_certificate_reminders !== false;
  const reminder = $('#certificate-reminder');
  const showReminder = control.checked && certificateWarnings > 0;
  reminder.hidden = !showReminder;
  reminder.textContent = showReminder ? `Có ${certificateWarnings} phương tiện có chứng chỉ hết hạn hoặc sắp hết hạn trong 30 ngày.` : '';
}

async function saveNotificationPreferences(event) {
  const control = event.currentTarget;
  control.disabled = true;
  try {
    const preferences = await api('/api/notification-preferences', {
      method: 'PUT', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({in_app_certificate_reminders: control.checked}),
    });
    state.currentUser.notification_preferences = preferences;
    renderNotificationPreferences(state.dashboardCertificateWarnings);
    toast(preferences.in_app_certificate_reminders ? 'Đã bật nhắc hạn chứng chỉ trong ứng dụng.' : 'Đã tắt nhắc hạn chứng chỉ trong ứng dụng.');
  } catch (error) {
    control.checked = !control.checked;
    toast(error.message, true);
  } finally { control.disabled = false; }
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
  $('#vessel-count').textContent = `${items.length} phương tiện`;
  $('#vessel-table').innerHTML = items.length ? `<table class="data-table responsive-table record-table vessel-record-table"><colgroup><col style="width:26%"><col style="width:13%"><col style="width:17%"><col style="width:10%"><col style="width:13%"><col style="width:15%"><col style="width:6%"></colgroup><thead><tr><th>Phương tiện</th><th>Số đăng ký</th><th>Loại / Cấp</th><th>Trọng tải</th><th>Hạn đăng kiểm</th><th>Trạng thái</th><th aria-label="Thao tác"></th></tr></thead><tbody>${items.map(v => `<tr><td data-label="Phương tiện"><strong>${esc(v.name)}</strong><br><small>${esc(v.organization_name || 'Chưa gán doanh nghiệp')}</small></td><td data-label="Số đăng ký">${esc(v.registration_no)}</td><td data-label="Loại / Cấp">${esc(v.vessel_type)} / ${esc(v.vessel_class)}</td><td data-label="Trọng tải">${number(v.deadweight_tons).toLocaleString('vi-VN')} tấn</td><td data-label="Hạn đăng kiểm" class="date-cell">${fmtDate(v.certificate_expiry_date)}</td><td data-label="Trạng thái"><span class="table-badge ${v.certificate_status === 'VALID' ? 'submitted' : 'draft'}">${certificateLabel(v.certificate_status)}</span></td><td data-label="Thao tác" class="action-cell"><button class="table-icon-button" data-edit-vessel="${v.id}" title="Chỉnh sửa ${esc(v.name)}" aria-label="Chỉnh sửa ${esc(v.name)}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"></path></svg></button></td></tr>`).join('')}</tbody></table>` : empty('Chưa có phương tiện', 'Thêm hồ sơ hoặc import file Excel mẫu.');
  $$('[data-edit-vessel]').forEach(button => button.onclick = () => openVessel(Number(button.dataset.editVessel)));
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
  } catch (error) { toast(error.message, true); }
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
  return `${approvalLegend}<table class="data-table responsive-table"><thead><tr><th>Mã / Loại</th><th>Phương tiện</th><th>Hành trình</th><th>Thời gian</th><th class="approval-heading">Tiến trình</th><th>Trạng thái</th>${editable ? '<th></th>' : ''}</tr></thead><tbody>${items.map(d => `<tr><td data-label="Mã / Loại"><strong>${esc(d.reference_no)}</strong><br><small>${d.movement_type === 'DEPARTURE' ? 'Rời cảng' : 'Vào cảng'}</small></td><td data-label="Phương tiện">${esc(d.vessel_name)}<br><small>${esc(d.registration_no)} · ${esc(d.master_name)}</small></td><td data-label="Hành trình">${esc(d.last_port)} → ${esc(d.working_port)}${d.destination_port ? ` → ${esc(d.destination_port)}` : ''}</td><td data-label="Thời gian">${fmtDate(d.movement_type === 'DEPARTURE' ? d.etd : d.eta)}</td><td data-label="Tiến trình duyệt"><span class="approval-dots">${approvalDot(d.port_approval, 'Cảng')}</span></td><td data-label="Trạng thái"><span class="table-badge ${workflowTone(d.workflow_status)}">${workflowLabel(d.workflow_status)}</span></td>${editable ? `<td data-label="Thao tác">${['DRAFT','CHANGES_REQUESTED'].includes(d.workflow_status) ? `<button data-edit-declaration="${d.id}">Mở phiếu</button> · ` : ''}<button data-workflow="${d.id}">Chi tiết</button></td>` : ''}</tr>`).join('')}</tbody></table>`;
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
  const unassigned = state.crew.filter(item => !item.vessel_id);
  const messages = [];
  if (warnings.length) messages.push(`${warnings.length} chứng chỉ đã hết hạn hoặc sẽ hết hạn trong 30 ngày. Cần rà soát trước khi phân công chuyến.`);
  if (unassigned.length) messages.push(`${unassigned.length} thuyền viên chưa gán phương tiện — sẽ không hiện trong phiếu khai báo của tàu nào cho đến khi được gán.`);
  const strip = $('#crew-warning-strip');
  strip.classList.toggle('visible', messages.length > 0);
  strip.textContent = messages.join(' ');
  $('#crew-table').innerHTML = items.length ? `<table class="data-table responsive-table record-table crew-record-table"><colgroup><col style="width:16%"><col style="width:14%"><col style="width:23%"><col style="width:20%"><col style="width:11%"><col style="width:11%"><col style="width:5%"></colgroup><thead><tr><th>Họ tên</th><th>Chức danh</th><th>Phương tiện</th><th>Chứng chỉ</th><th>Thời hạn</th><th>Trạng thái</th><th aria-label="Thao tác"></th></tr></thead><tbody>${items.map(item => `<tr><td data-label="Họ tên"><strong>${esc(item.full_name)}</strong><br><small>${esc(item.phone || '')}</small></td><td data-label="Chức danh">${esc(item.crew_role)}</td><td data-label="Phương tiện">${esc(item.vessel_name || 'Chưa phân công')}<br><small>${esc(item.registration_no || '')}</small></td><td data-label="Chứng chỉ">${esc(item.professional_certificate_type)}<br><small>${esc(item.professional_certificate_no)}</small></td><td data-label="Thời hạn" class="date-cell">${fmtDate(item.certificate_expiry_date)}</td><td data-label="Trạng thái"><span class="table-badge ${item.certificate_status === 'VALID' ? 'submitted' : 'draft'}">${certificateLabel(item.certificate_status)}</span></td><td data-label="Thao tác" class="action-cell"><button class="table-icon-button" data-edit-crew="${item.id}" title="Chỉnh sửa ${esc(item.full_name)}" aria-label="Chỉnh sửa ${esc(item.full_name)}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"></path></svg></button></td></tr>`).join('')}</tbody></table>` : empty('Chưa có danh sách thuyền viên', 'Thêm thuyền trưởng hoặc thuyền viên cùng chứng chỉ chuyên môn.');
  $$('[data-edit-crew]').forEach(button => button.onclick = () => openCrew(Number(button.dataset.editCrew)));
}

function openCrew(id = null) {
  const item = id ? state.crew.find(row => row.id === id) : {};
  state.editingCrew = item || {};
  $('#crew-fields').innerHTML = `
    ${field('full_name','Họ và tên',item.full_name,'text','required class="span-2"')}
    ${selectField('crew_role','Chức danh',['Thuyền trưởng','Máy trưởng','Thuyền phó','Máy phó','Thủy thủ','Thợ máy','Khác'],item.crew_role,'required')}
    ${field('phone','Số điện thoại',item.phone,'tel')}
    ${field('identity_no','CCCD / Hộ chiếu',item.identity_no)}
    <label>Phương tiện<select name="vessel_id"><option value="">Chưa phân công</option>${state.vessels.map(v => `<option value="${v.id}" ${Number(item.vessel_id) === v.id ? 'selected' : ''}>${esc(v.name)} — ${esc(v.registration_no)}</option>`).join('')}</select></label>
    ${field('professional_certificate_type','Loại chứng chỉ chuyên môn',item.professional_certificate_type,'text','required')}
    ${field('professional_certificate_no','Số chứng chỉ',item.professional_certificate_no,'text','required')}
    ${field('certificate_issue_date','Ngày cấp',item.certificate_issue_date,'date')}
    ${field('certificate_expiry_date','Ngày hết hạn',item.certificate_expiry_date,'date','required')}
    <label class="span-3">Ghi chú<textarea name="notes">${esc(item.notes || '')}</textarea></label>`;
  $('#crew-dialog').showModal();
}

async function saveCrew(event) {
  event.preventDefault();
  const form = $('#crew-form');
  const data = values(form);
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

function openVessel(id = null) {
  const v = id ? state.vessels.find(item => item.id === id) : {};
  state.editingVessel = v || {};
  $('#vessel-fields').innerHTML = `
    ${field('organization_name','Doanh nghiệp / Chủ phương tiện',v.organization_name || '', 'text', 'required class="span-2"')}
    ${field('name','Tên phương tiện',v.name,'text','required')}
    ${field('registration_no','Số đăng ký',v.registration_no,'text','required')}
    ${field('registry_or_imo','Số đăng kiểm / IMO',v.registry_or_imo)}
    ${selectField('vessel_type','Loại phương tiện / Công dụng',state.catalogs.vesselTypes,v.vessel_type,'required')}
    ${selectField('vessel_class','Cấp phương tiện',state.catalogs.vesselClasses,v.vessel_class,'required')}
    ${selectField('shell_material','Vật liệu vỏ',state.catalogs.shellMaterials,v.shell_material)}
    ${field('build_year','Năm đóng',v.build_year,'number','min="1800" max="2100"')}
    ${field('length_m','Chiều dài Lmax (m)',v.length_m,'number','step="0.01" min="0"')}
    ${field('width_m','Chiều rộng B (m)',v.width_m,'number','step="0.01" min="0"')}
    ${field('side_height_m','Chiều cao mạn (m)',v.side_height_m,'number','step="0.01" min="0"')}
    ${field('draft_m','Mớn nước đầy tải (m)',v.draft_m,'number','step="0.01" min="0"')}
    ${field('deadweight_tons','Trọng tải toàn phần (tấn)',v.deadweight_tons,'number','step="0.01" min="0"')}
    ${field('gross_tonnage','Dung tích (GT)',v.gross_tonnage,'number','step="0.01" min="0"')}
    ${field('engine_power_cv','Tổng công suất máy (CV)',v.engine_power_cv,'number','step="0.01" min="0"')}
    ${field('cargo_capacity_tons','Sức chở hàng (tấn)',v.cargo_capacity_tons,'number','step="0.01" min="0"')}
    ${field('container_capacity_teu','Sức chở container (TEU)',v.container_capacity_teu,'number','step="1" min="0"')}
    ${field('passenger_capacity','Sức chở khách',v.passenger_capacity,'number','min="0"')}
    ${field('min_crew','Định biên thuyền viên tối thiểu',v.min_crew,'number','min="0"')}
    ${field('safety_certificate_no','Số GCN ATKT & BVMT',v.safety_certificate_no)}
    ${field('certificate_issue_date','Ngày cấp GCN',v.certificate_issue_date,'date')}
    ${field('certificate_expiry_date','Ngày hết hạn GCN',v.certificate_expiry_date,'date')}
    <label class="span-3">Ghi chú<textarea name="notes">${esc(v.notes || '')}</textarea></label>`;
  $('#vessel-dialog').showModal();
}

async function saveVessel(event) {
  event.preventDefault();
  const form = $('#vessel-form');
  const data = values(form);
  data.organization = {name: data.organization_name};
  delete data.organization_name;
  if (state.editingVessel?.id) {
    data.id = state.editingVessel.id;
    data.version = state.editingVessel.version;
  }
  setSubmitting(form, event.submitter, true, 'Đang lưu…');
  try {
    await api('/api/vessels', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    $('#vessel-dialog').close();
    toast('Đã lưu hồ sơ phương tiện.');
    await loadVessels();
  } catch (error) { toast(error.message, true); }
  finally { setSubmitting(form, event.submitter, false); }
}

function cargoFields(prefix, title, current = {}, load = false) {
  return `<section class="form-section"><h3>${title}</h3><div class="section-grid">
    ${selectField(`${prefix}_cargo_type`,'Loại hàng',state.catalogs.cargoTypes,current.cargo_type)}
    ${selectField(`${prefix}_movement_type`,'Loại hình',load ? state.catalogs.loadMovements : state.catalogs.unloadMovements,current.movement_type)}
    ${field(`${prefix}_cargo_name`,'Tên hàng',current.cargo_name,'text','class="wide-field"')}
    ${field(`${prefix}_cont20_full`,'20 ft có hàng',current.cont20_full,'number','min="0"')}
    ${field(`${prefix}_cont20_empty`,'20 ft rỗng',current.cont20_empty,'number','min="0"')}
    ${field(`${prefix}_cont40_full`,'40 ft có hàng',current.cont40_full,'number','min="0"')}
    ${field(`${prefix}_cont40_empty`,'40 ft rỗng',current.cont40_empty,'number','min="0"')}
    ${field(`${prefix}_total`,'Tổng container',current.total_containers || 0,'number','readonly class="derived"')}
    ${field(`${prefix}_teu`,'Quy đổi TEU',current.teu || 0,'number','readonly class="derived"')}
    ${field(`${prefix}_empty_teu`,'TEU rỗng',current.empty_teu || 0,'number','readonly class="derived"')}
    ${field(`${prefix}_tons`,'Khối lượng (tấn)',current.tons,'number','min="0" step="0.01"')}
  </div></section>`;
}

function crewChecklistHtml(vesselId, selectedIds = []) {
  if (!vesselId) return '<p class="muted">Chọn phương tiện ở bước 1 để xem danh sách thuyền viên.</p>';
  const pool = state.crew.filter(member => Number(member.vessel_id) === Number(vesselId));
  if (!pool.length) return '<p class="muted">Chưa có thuyền viên gán cho phương tiện này. Hãy cập nhật Danh sách thuyền viên trước khi tạo phiếu.</p>';
  return `<ul class="crew-checklist" role="group" aria-label="Chọn thuyền viên đi theo phương tiện">${pool.map(member => {
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
  return state.crew.find(member => Number(member.vessel_id) === Number(vesselId) && member.crew_role.trim().toLowerCase() === 'thuyền trưởng');
}

function refreshCrewOptions(vesselId) {
  const container = $('#declaration-crew-container');
  if (!container) return;
  const currentlySelected = [...container.querySelectorAll('[name="crew_ids"]:checked')].map(input => Number(input.value));
  const captain = captainForVessel(vesselId);
  if (captain && !currentlySelected.includes(captain.id)) currentlySelected.push(captain.id);
  container.innerHTML = crewChecklistHtml(vesselId, currentlySelected);
  const form = $('#declaration-form');
  form.elements.master_name.value = captain?.full_name || '';
  form.elements.master_phone.value = captain?.phone || '';
  const summary = $('#assigned-captain');
  if (summary) summary.textContent = captain ? `${captain.full_name}${captain.phone ? ` · ${captain.phone}` : ''}` : 'Chưa gán Thuyền trưởng cho phương tiện này.';
}

const DECLARATION_STEPS = [
  { label: 'Phương tiện' },
  { label: 'Hành trình' },
  { label: 'Hàng hóa' },
  { label: 'Thuyền trưởng & thuyền viên' },
  { label: 'Đính kèm' },
  { label: 'Xem lại & Gửi' },
];

function newCrewRowTemplate(role = 'Thủy thủ') {
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
      <label class="wide-field">${index === 0 ? '* Thuyền trưởng — Họ tên' : 'Họ tên thuyền viên'}<input data-crew-field="full_name" data-crew-row="${index}" value="${esc(row.full_name)}" ${index === 0 ? 'required' : ''}></label>
      ${index === 0
        ? `<input type="hidden" data-crew-field="crew_role" data-crew-row="0" value="Thuyền trưởng">`
        : `<label>Chức danh<select data-crew-field="crew_role" data-crew-row="${index}">${['Máy trưởng','Thuyền phó','Máy phó','Thủy thủ','Thợ máy','Khác'].map(r => `<option ${row.crew_role === r ? 'selected' : ''}>${r}</option>`).join('')}</select></label>`}
      <label>${index === 0 ? '* Số điện thoại' : 'Số điện thoại'}<input data-crew-field="phone" data-crew-row="${index}" value="${esc(row.phone)}" type="tel" ${index === 0 ? 'required' : ''}></label>
      <label>${index === 0 ? '* Loại chứng chỉ chuyên môn' : 'Loại chứng chỉ chuyên môn'}<input data-crew-field="professional_certificate_type" data-crew-row="${index}" value="${esc(row.professional_certificate_type)}" ${index === 0 ? 'required' : ''}></label>
      <label>${index === 0 ? '* Số chứng chỉ' : 'Số chứng chỉ'}<input data-crew-field="professional_certificate_no" data-crew-row="${index}" value="${esc(row.professional_certificate_no)}" ${index === 0 ? 'required' : ''}></label>
      <label>${index === 0 ? '* Hạn chứng chỉ' : 'Hạn chứng chỉ'}<input type="date" data-crew-field="certificate_expiry_date" data-crew-row="${index}" value="${esc(row.certificate_expiry_date)}" ${index === 0 ? 'required' : ''}></label>
      ${index > 0 ? `<button type="button" class="ghost-button" data-remove-crew-row="${index}">Xóa</button>` : ''}
    </div>`).join('');
  return `${rows}<button type="button" class="outline-button" id="add-new-crew-row">+ Thêm thuyền viên</button>`;
}

function reviewSummaryHtml(d) {
  const isNew = state.declarationVesselMode === 'new';
  const captainName = isNew ? state.declarationNewCrew[0]?.full_name : d.master_name;
  const captainPhone = isNew ? state.declarationNewCrew[0]?.phone : d.master_phone;
  const crewContainer = $('#declaration-crew-container');
  const checkedCrew = crewContainer
    ? $$('input[name="crew_ids"]:checked', crewContainer).length
    : 0;
  const crewTotal = isNew ? state.declarationNewCrew.length : (checkedCrew || (d.crew_ids || []).length);
  return `<section class="form-section"><h3>F. Xem lại & Gửi</h3><div class="section-grid">
    <div class="attachment-field wide-field"><strong>Phương tiện</strong><p>${esc(d.vessel_name || '')} — ${esc(d.registration_no || '')}${isNew ? ' (hồ sơ mới)' : ''}</p></div>
    <div class="attachment-field wide-field"><strong>Thuyền trưởng</strong><p>${captainName ? `${esc(captainName)}${captainPhone ? ` · ${esc(captainPhone)}` : ''}` : 'Chưa có thông tin'}</p></div>
    <div class="attachment-field"><strong>Thuyền viên đi theo</strong><p>${crewTotal} người</p></div>
    <div class="attachment-field"><strong>Hành trình</strong><p>${esc(d.last_port || '')} → ${esc(d.working_port || '')}${d.destination_port ? ` → ${esc(d.destination_port)}` : ''}</p></div>
  </div>
  <p class="muted">Kiểm tra kỹ thông tin trước khi bấm “Xác nhận & gửi”. Sau khi gửi, thông tin được khóa trong khi Cảng xem xét.</p></section>`;
}

function renderDeclarationWizard() {
  const d = state.editingDeclaration;
  const isNew = state.declarationVesselMode === 'new';
  const assignedCaptain = d.vessel_id ? captainForVessel(d.vessel_id) : null;
  const masterName = isNew ? '' : (assignedCaptain?.full_name || d.master_name || '');
  const masterPhone = isNew ? '' : (assignedCaptain?.phone || d.master_phone || '');

  $('#declaration-fields').innerHTML = `
    ${wizardNavHtml()}
    <div id="step-error-summary" class="step-error-summary" role="alert" tabindex="-1" hidden></div>
    <input name="master_name" type="hidden" value="${esc(masterName)}">
    <input name="master_phone" type="hidden" value="${esc(masterPhone)}">
    <div class="wizard-step" data-step="1" ${state.wizardStep === 1 ? '' : 'hidden'}>
      <section class="form-section"><h3>A. Thông tin chung và phương tiện</h3><div class="section-grid">
        ${selectField('movement_type','Loại phiếu',['ARRIVAL','DEPARTURE'],d.movement_type || 'ARRIVAL','required')}
        ${field('company_name','Tên doanh nghiệp / Đại lý',d.company_name,'text','required class="wide-field"')}
        ${field('declaration_date','Ngày khai báo',d.declaration_date || new Date().toISOString().slice(0,10),'date','required')}
        <div class="vessel-mode-toggle wide-field" role="radiogroup" aria-label="Nguồn hồ sơ phương tiện">
          <label><input type="radio" name="vessel_mode" value="existing" ${isNew ? '' : 'checked'}> Phương tiện đã có hồ sơ</label>
          <label><input type="radio" name="vessel_mode" value="new" ${isNew ? 'checked' : ''}> + Khai phương tiện mới (vãng lai)</label>
        </div>
        <label id="declaration-vessel-label" ${isNew ? 'hidden' : ''}>* Chọn hồ sơ phương tiện<select name="vessel_id" id="declaration-vessel" ${isNew ? '' : 'required'}><option value="">Chọn phương tiện</option>${state.vessels.map(v => `<option value="${v.id}" ${Number(d.vessel_id) === v.id ? 'selected' : ''}>${esc(v.name)} — ${esc(v.registration_no)}</option>`).join('')}</select></label>
        <div id="vessel-suggestion" class="wide-field" ${isNew ? 'hidden' : ''}></div>
        ${field('vessel_name','Tên phương tiện',d.vessel_name,'text',isNew ? 'required' : 'required readonly class="locked-field"')}
        ${field('registration_no','Số đăng ký',d.registration_no,'text',isNew ? 'required' : 'required readonly class="locked-field"')}
        ${selectField('vessel_type','Loại phương tiện',state.catalogs.vesselTypes,d.vessel_type,isNew ? 'required' : 'required data-locked="true" tabindex="-1" class="locked-field"')}
        ${selectField('vessel_class','Cấp phương tiện',state.catalogs.vesselClasses,d.vessel_class,isNew ? 'required' : 'required data-locked="true" tabindex="-1" class="locked-field"')}
        ${field('length_m','Chiều dài (m)',d.length_m,'number',isNew ? 'step="0.01" min="0"' : 'step="0.01" min="0" readonly class="locked-field"')}
        ${field('deadweight_tons','Trọng tải toàn phần',d.deadweight_tons,'number',isNew ? 'step="0.01" min="0"' : 'step="0.01" min="0" readonly class="locked-field"')}
        ${field('gross_tonnage','Dung tích (GT)',d.gross_tonnage,'number',isNew ? 'step="0.01" min="0"' : 'step="0.01" min="0" readonly class="locked-field"')}
        ${field('certificate_expiry_date','Hạn GCN ATKT & BVMT',d.certificate_expiry_date,'date',isNew ? '' : 'readonly class="locked-field"')}
        ${field('crew_count','Số thuyền viên tối thiểu',d.crew_count,'number',isNew ? 'min="0"' : 'min="0" readonly class="locked-field"')}
        ${field('passenger_count','Số hành khách',d.passenger_count,'number','min="0"')}
        <div class="record-lock-note wide-field" ${isNew ? 'hidden' : ''}><strong>Thông tin hồ sơ phương tiện chỉ đọc</strong><span>Chọn đúng phương tiện để hệ thống tự điền. Khi hồ sơ thay đổi, Quản trị viên cập nhật tại mục Hồ sơ phương tiện.</span></div>
        <p class="muted wide-field" ${isNew ? '' : 'hidden'}>Hồ sơ phương tiện mới sẽ được lưu khi phiếu được xác nhận gửi, để lần sau có thể chọn lại.</p>
      </div></section>
    </div>
    <div class="wizard-step" data-step="2" ${state.wizardStep === 2 ? '' : 'hidden'}>
      <section class="form-section"><h3>B. Hành trình</h3><div class="section-grid">
        ${field('last_port','Cảng rời cuối cùng',d.last_port,'text','required list="ports-list"')}
        ${field('working_port','Cảng / cầu bến đến làm hàng',d.working_port,'text','required list="ports-list"')}
        ${field('destination_port','Cảng đích',d.destination_port,'text','list="ports-list"')}
        ${field('eta','Thời gian dự kiến đến',d.eta,'datetime-local','required')}
        ${field('etd','Thời gian dự kiến rời',d.etd,'datetime-local','required')}
        ${field('actual_arrival_at','Thời gian đến thực tế',d.actual_arrival_at,'datetime-local')}
        ${field('actual_departure_at','Thời gian rời thực tế',d.actual_departure_at,'datetime-local')}
        <datalist id="ports-list"></datalist>
      </div></section>
    </div>
    <div class="wizard-step" data-step="3" ${state.wizardStep === 3 ? '' : 'hidden'}>
      ${cargoFields('unload','C. Hàng hóa dỡ tại cảng',d.unload || {},false)}
      ${cargoFields('load','D. Hàng hóa xếp tại cảng',d.load || {},true)}
    </div>
    <div class="wizard-step" data-step="4" ${state.wizardStep === 4 ? '' : 'hidden'}>
      <section class="form-section"><h3>E. Thuyền trưởng và thuyền viên</h3><div class="section-grid">
        <div class="wide-field" id="declaration-crew-container" ${isNew ? 'hidden' : ''}>${isNew ? '' : crewChecklistHtml(d.vessel_id, [...(d.crew || []).map(item => item.id), ...(d.crew_ids || []), ...(assignedCaptain ? [assignedCaptain.id] : [])])}</div>
        ${isNew
          ? `<div class="wide-field">${newCrewRowsHtml()}</div>`
          : `<div class="attachment-field wide-field"><strong>Thuyền trưởng theo phương tiện</strong><p id="assigned-captain">${masterName ? `${esc(masterName)}${masterPhone ? ` · ${esc(masterPhone)}` : ''}` : 'Chưa gán Thuyền trưởng cho phương tiện này.'}</p><small>Thuyền trưởng được lấy tự động từ Danh sách thuyền viên theo ID phương tiện.</small></div>`}
      </div></section>
    </div>
    <div class="wizard-step" data-step="5" ${state.wizardStep === 5 ? '' : 'hidden'}>
      <section class="form-section"><h3>Đính kèm hồ sơ</h3><div class="section-grid">
        <label class="attachment-field wide-field">Đính kèm hình ảnh / PDF / Word / Excel<input name="attachments" type="file" multiple accept=".jpg,.jpeg,.png,.webp,.pdf,.doc,.docx,.xls,.xlsx"><small>Mỗi file tối đa 12 MB. File được lưu cùng phiếu khai báo.</small></label>
      </div></section>
    </div>
    <div class="wizard-step" data-step="6" ${state.wizardStep === 6 ? '' : 'hidden'}>
      ${reviewSummaryHtml(d)}
    </div>`;

  const container = $('#declaration-fields');
  const declarationVessel = $('#declaration-vessel');
  if (declarationVessel) declarationVessel.onchange = fillFromVessel;
  ['unload','load'].forEach(prefix => $$(`[name^="${prefix}_cont"]`, $('#declaration-form')).forEach(input => input.addEventListener('input', () => calculateCargo(prefix))));
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
  $('[data-wizard-back]', container)?.addEventListener('click', () => goToWizardStep(state.wizardStep - 1));
  $('[data-wizard-next]', container)?.addEventListener('click', () => goToWizardStep(state.wizardStep + 1));
  $$('[data-wizard-dot]', container).forEach(dot => dot.addEventListener('click', () => {
    const target = Number(dot.dataset.wizardDot);
    if (target <= state.wizardMaxStep) goToWizardStep(target);
  }));

  const submitButton = $('#submit-declaration');
  if (submitButton) submitButton.disabled = state.wizardStep !== DECLARATION_STEPS.length;
}

function calculateCargo(prefix) {
  const form = $('#declaration-form');
  const a = number(form.elements[`${prefix}_cont20_full`].value), b = number(form.elements[`${prefix}_cont20_empty`].value), c = number(form.elements[`${prefix}_cont40_full`].value), d = number(form.elements[`${prefix}_cont40_empty`].value);
  form.elements[`${prefix}_total`].value = a + b + c + d;
  form.elements[`${prefix}_teu`].value = a + b + (c + d) * 2;
  form.elements[`${prefix}_empty_teu`].value = b + d * 2;
}

function declarationData() {
  const data = values($('#declaration-form'));
  // Blank optional number/date inputs arrive as "" via FormData, which the backend's
  // numeric fields reject outright — drop them so the schema's own default applies.
  Object.keys(data).forEach(key => { if (data[key] === '') delete data[key]; });
  data.crew_ids = [...$('#declaration-form').querySelectorAll('[name="crew_ids"]:checked')].map(input => Number(input.value));
  delete data.attachments;
  delete data.vessel_mode;
  ['unload','load'].forEach(prefix => {
    data[prefix] = {cargo_type:data[`${prefix}_cargo_type`],movement_type:data[`${prefix}_movement_type`],cargo_name:data[`${prefix}_cargo_name`],cont20_full:data[`${prefix}_cont20_full`],cont20_empty:data[`${prefix}_cont20_empty`],cont40_full:data[`${prefix}_cont40_full`],cont40_empty:data[`${prefix}_cont40_empty`],tons:data[`${prefix}_tons`]};
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
        const savedCrew = await api('/api/crew', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ ...row, vessel_id: newVessel.id })});
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
    toast(`${submit ? 'Phiếu đã được xác nhận gửi đến Cảng.' : 'Đã lưu phiếu nháp.'}${files.length ? ` Đã tải ${files.length} file.` : ''}`);
    await loadDeclarations();
    await loadDashboard();
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

  // The port-side confirmation gate is a single action for PORT_STAFF.
  const select = $('#workflow-form select[name="action"]');
  const role = state.currentUser ? state.currentUser.role : '';
  select.innerHTML = role === 'PORT_STAFF'
    ? '<option value="">Chọn</option><option value="PORT_APPROVE">Xác nhận hoàn tất</option><option value="REQUEST_CHANGES">Yêu cầu bổ sung</option>'
    : '<option value="">Chọn</option>';

  // Hide workflow action form for customers / admins / read-only reviewers
  $('#workflow-form').style.display = role === 'PORT_STAFF' ? 'block' : 'none';

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
    toast('Đã ghi nhận thao tác và cập nhật timeline.');
    await loadDeclarations();
    await openWorkflow(state.workflowDeclaration.id);
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
  const container = $('#import-result');
  container.classList.toggle('empty-state', isEmptyPlaceholder);
  container.innerHTML = html;
}

async function previewImport(input, path, kind) {
  const file = input.files[0];
  if (!file) return;
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
  let bodyHtml;
  if (kind === 'vessels') {
    const rows = preview.rows || [];
    warningCount = rows.filter(row => row.missingFields?.length).length;
    bodyHtml = rows.length
      ? `<table class="data-table responsive-table"><thead><tr><th>Dòng</th><th>Tên phương tiện</th><th>Số đăng ký</th><th>Kiểm tra</th></tr></thead><tbody>${rows.map(row => `<tr><td data-label="Dòng">${row.sourceRow}</td><td data-label="Tên phương tiện">${esc(row.name || '—')}</td><td data-label="Số đăng ký">${esc(row.registration_no || '—')}</td><td data-label="Kiểm tra">${row.missingFields?.length ? `<span class="table-badge danger">Thiếu: ${esc(row.missingFields.join(', '))}</span>` : '<span class="table-badge submitted">Hợp lệ</span>'}</td></tr>`).join('')}</tbody></table>`
      : empty('Không tìm thấy dòng dữ liệu', 'Kiểm tra lại file có đúng mẫu và còn dữ liệu hay không.');
  } else {
    const row = preview.row || {};
    const missing = preview.missingFields || [];
    warningCount = missing.length ? 1 : 0;
    bodyHtml = `<div class="attachment-field"><strong>${esc(row.vessel_name || '—')} · ${esc(row.registration_no || '—')}</strong><p>${esc(row.last_port || '—')} → ${esc(row.working_port || '—')}</p><small>${missing.length ? `Thiếu: ${esc(missing.join(', '))}` : 'Đủ dữ liệu bắt buộc.'}</small></div>`;
  }
  const mapping = preview.mapping;
  setImportResult(`
    ${mapping ? `<div class="import-mapping-note"><strong>Đã tự nhận diện cấu trúc</strong><span>Sheet: ${esc(mapping.sheet || '—')} · Mapping: theo nhãn cột</span></div>` : ''}
    ${warningCount ? `<div class="warning-strip visible">${kind === 'vessels' ? `Có ${warningCount} dòng thiếu dữ liệu bắt buộc — các dòng này sẽ bị bỏ qua nếu bạn tiếp tục.` : 'File thiếu dữ liệu bắt buộc — không thể import cho đến khi bổ sung.'}</div>` : ''}
    ${bodyHtml}
    <div class="modal-actions">
      <button type="button" class="ghost-button" id="cancel-import">Huỷ</button>
      <button type="button" class="primary-button" id="confirm-import" ${kind === 'declaration' && warningCount ? 'disabled' : ''}>Xác nhận import</button>
    </div>`);
  $('#cancel-import').onclick = cancelImport;
  $('#confirm-import').onclick = confirmImport;
}

function cancelImport() {
  state.pendingImport = null;
  $('#import-vessels').value = '';
  $('#import-declaration').value = '';
  setImportResult('Chưa có file nào được import trong phiên này.', true);
}

async function confirmImport() {
  const {path, file} = state.pendingImport;
  const button = $('#confirm-import');
  button.disabled = true;
  button.textContent = 'Đang import…';
  try {
    const result = await api(path, {method:'POST', headers:IMPORT_FILE_HEADERS, body:file});
    setImportResult(`<div><strong>Import thành công</strong><p>Đã nhận ${result.accepted || 0} bản ghi.${result.rejected?.length ? ` Có ${result.rejected.length} dòng bị từ chối.` : ''}</p>${result.rejected?.length ? `<ul>${result.rejected.map(item => `<li>Dòng ${item.sourceRow}: ${esc(item.error)}</li>`).join('')}</ul>` : ''}</div>`);
    toast('Đã map dữ liệu Excel vào hệ thống.');
    state.pendingImport = null;
    $('#import-vessels').value = '';
    $('#import-declaration').value = '';
    await Promise.all([loadVessels(), loadDeclarations(), loadDashboard()]);
  } catch (error) {
    setImportResult(`<div><strong>Không thể import</strong><p>${esc(error.message)}</p></div>`);
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
  const from = $('#report-from').value || '1900-01-01';
  const to = $('#report-to').value || '2999-12-31';
  try {
    await downloadFile(`/api/reports/${kind}?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`, `report_${kind}_${from}_${to}.xlsx`);
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

function renderAnalyticsUnavailable() {
  $('#analytics-title').textContent = 'Thống kê sản lượng';
  $('#analytics-unavailable').hidden = false;
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

async function loadReportAnalytics(period = 'month') {
  try {
    const data = await api(`/api/reports/analytics?period=${period}`);
    $('#analytics-unavailable').hidden = true;
    $('#analytics-demo-notice').hidden = data.dataSource !== 'DEMO';
    $('#kpi-grid').hidden = false;
    $('.analytics-split').hidden = false;
    $('#export-analytics').disabled = false;
    const fmt = value => number(value).toLocaleString('vi-VN');
    $$('.period-switch button').forEach(button => {
      button.classList.toggle('active', button.dataset.period === data.period);
      button.onclick = () => loadReportAnalytics(button.dataset.period);
    });
    const meta = data.meta || {};
    $('#analytics-title').textContent = meta.analyticsTitle || '';
    $('#trend-title').textContent = meta.trendTitle || '';
    $('#trend-sub').textContent = meta.trendSub || '';
    $('#compare-sub').textContent = meta.compareSub || '';
    $('#kpi-grid').innerHTML = ANALYTICS_KPIS.map(([key, label]) => {
      const kpi = data.kpis[key] || { cur: 0, prev: 0 };
      const delta = analyticsDelta(kpi.cur, kpi.prev);
      return `<article class="kpi-card"><p>${label.toUpperCase()}</p><div class="kpi-value"><strong>${fmt(kpi.cur)}</strong><span class="kpi-delta ${delta.up ? 'up' : 'down'}">${delta.txt}</span></div><small>Cùng kỳ: ${fmt(kpi.prev)}</small></article>`;
    }).join('');
    const trend = data.trend || { labels: [], cur: [], prev: [] };
    const max = Math.max(...trend.cur, ...trend.prev, 1);
    $('#trend-chart').innerHTML = trend.labels.map((label, i) => `<div class="trend-col"><div class="trend-bars"><span class="trend-bar cur" style="height:${Math.round((trend.cur[i] || 0) / max * 100)}%"></span><span class="trend-bar prev" style="height:${Math.round((trend.prev[i] || 0) / max * 100)}%"></span></div><small>${esc(label)}</small></div>`).join('');
    $('#compare-body').innerHTML = ANALYTICS_KPIS.map(([key, label]) => {
      const kpi = data.kpis[key] || { cur: 0, prev: 0 };
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
  downloadFile(`/api/reports/analytics/export?period=${period}`, `bao_cao_tong_hop_${period}_${new Date().toISOString().slice(0, 10)}.xlsx`)
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

async function init() {
  if (!window.__tanThuanRouteBound) {
    window.addEventListener('hashchange', route);
    window.__tanThuanRouteBound = true;
  }
  $('#menu-toggle').onclick = () => $('.sidebar').classList.toggle('open');
  $('#theme-toggle').onclick = () => { const root = document.documentElement; const next = root.dataset.theme === 'dark' ? 'light' : 'dark'; root.dataset.theme = next; localStorage.setItem('tanthuan-theme', next); };
  document.documentElement.dataset.theme = localStorage.getItem('tanthuan-theme') || 'dark';
  bindLoginForm();

  // Setup logout handler
  $('#logout-button').onclick = async () => {
    try {
      await api('/api/auth/logout', { method: 'POST' });
    } catch (_) {}
    localStorage.removeItem('token');
    state.currentUser = null;
    location.reload();
  };

  // Load current user profile first (authentication barrier)
  try {
    state.currentUser = await api('/api/auth/me');
    const displayName = state.currentUser.full_name?.trim() || state.currentUser.username;
    $('#user-display').innerHTML = `<span class="role-pill">${esc(roleLabel(state.currentUser.role))}</span><strong>${esc(displayName)}</strong><small>@${esc(state.currentUser.username)}</small>`;
    $('#logout-button').style.display = 'inline-block';

    // Role-based UI visibility constraints
    const isCustomer = state.currentUser.role === 'CUSTOMER';
    const isAdmin = state.currentUser.role === 'ADMIN';
    const isReviewer = state.currentUser.role === 'PORT_STAFF';

    $$('[data-action="new-declaration"]').forEach(btn => btn.style.display = isCustomer ? 'inline-block' : 'none');
    const addVesselBtn = $('#add-vessel');
    if (addVesselBtn) addVesselBtn.style.display = isReviewer ? 'none' : 'inline-block';
    const addCrewBtn = $('#add-crew');
    if (addCrewBtn) addCrewBtn.style.display = isReviewer ? 'none' : 'inline-block';

    const importNav = $('nav a[href="#import"]');
    if (importNav) importNav.style.display = (isCustomer || isAdmin) ? 'block' : 'none';

    const reportsNav = $('nav a[href="#reports"]');
    if (reportsNav) reportsNav.style.display = 'block';

    const integrationActions = $('#integration-admin-actions');
    const integrationJobs = $('#sync-jobs');
    if (integrationActions) integrationActions.hidden = !isAdmin;
    if (integrationJobs) integrationJobs.hidden = !isAdmin;

  } catch (err) {
    state.currentUser = null;
    $('#user-display').innerHTML = '';
    $('#logout-button').style.display = 'none';
    showLoginDialog();
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
  $('#vessel-search').addEventListener('input', renderVessels);
  let dashboardTimer;
  $('#dashboard-vessel-search').addEventListener('input', event => { clearTimeout(dashboardTimer); const query = event.target.value.trim(); dashboardTimer = setTimeout(() => loadDashboard(query.length >= 2 ? query : ''), 220); });
  $('#crew-search').addEventListener('input', renderCrew);
  $('#vessel-form').addEventListener('submit', saveVessel);
  $('#crew-form').addEventListener('submit', saveCrew);
  $('#declaration-form').addEventListener('submit', saveDeclaration);
  $('#workflow-form').addEventListener('submit', saveWorkflow);
  $('#in-app-certificate-reminders').addEventListener('change', saveNotificationPreferences);

  $('#add-crew').onclick = () => openCrew();
  $$('[data-close-dialog]').forEach(button => button.onclick = () => document.getElementById(button.dataset.closeDialog).close());
  let declarationTimer;
  ['declaration-search','master-filter'].forEach(id => $(`#${id}`).addEventListener('input', () => { clearTimeout(declarationTimer); declarationTimer = setTimeout(applyDeclarationFilters, 250); }));
  ['movement-filter','workflow-filter','declaration-from','declaration-to'].forEach(id => $(`#${id}`).addEventListener('change', applyDeclarationFilters));
  $('#clear-declaration-filter').onclick = () => { ['declaration-search','movement-filter','workflow-filter','master-filter','declaration-from','declaration-to'].forEach(id => $(`#${id}`).value = ''); applyDeclarationFilters(); };
  $('#import-vessels').onchange = event => previewImport(event.target, '/api/import/vessels', 'vessels');
  $('#import-declaration').onchange = event => previewImport(event.target, '/api/import/declaration', 'declaration');
  $$('[data-report]').forEach(button => button.onclick = () => exportReport(button.dataset.report));
  $('#export-analytics').onclick = exportAnalyticsReport;
  $('#trigger-backup').onclick = triggerBackup;
  $('#prepare-sync').onclick = prepareSync;
  const today = new Date(); $('#report-to').value = today.toISOString().slice(0,10); $('#report-from').value = `${today.getFullYear()}-01-01`;
  try {
    [state.catalogs, state.vessels, state.crew] = await Promise.all([api('/api/catalogs'), api('/api/vessels'), api('/api/crew')]);
    $('#api-state').className = 'state-badge ok'; $('#api-state').textContent = 'Đã kết nối';
  } catch (error) { $('#api-state').className = 'state-badge pending'; $('#api-state').textContent = 'Mất kết nối'; toast(error.message, true); }
  route();
}

document.addEventListener('DOMContentLoaded', init);
