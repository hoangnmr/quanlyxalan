const state = {
  catalogs: {}, vessels: [], declarations: [], organizations: [], crew: [],
  declarationFilter: {}, declarationPage: 1, declarationPaging: null, editingVessel: null, editingDeclaration: null, editingCrew: null, workflowDeclaration: null,
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
    $('#login-dialog').showModal();
    throw new Error('Vui lòng đăng nhập.');
  }
  const type = response.headers.get('content-type') || '';
  const body = type.includes('json') ? await response.json() : await response.blob();
  if (!response.ok) throw new Error(body.detail || body.error || 'Yêu cầu không thành công.');
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

function optionList(items = [], selected = '') {
  return `<option value="">Chọn</option>${items.map(item => `<option ${item === selected ? 'selected' : ''}>${esc(item)}</option>`).join('')}`;
}

function field(name, label, value = '', type = 'text', extra = '') {
  const required = extra.includes('required');
  return `<label>${required ? '* ' : ''}${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
}

function selectField(name, label, items, value = '', extra = '') {
  const required = extra.includes('required');
  return `<label>${required ? '* ' : ''}${label}<select name="${name}" ${extra}>${optionList(items, value)}</select></label>`;
}

function values(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function pageName(route) {
  return ({dashboard:'Tổng quan khai báo', declarations:'Phiếu khai báo', vessels:'Hồ sơ phương tiện', crew:'Danh sách thuyền viên', import:'Import dữ liệu Excel', reports:'Báo cáo Cảng vụ'})[route] || 'Tổng quan khai báo';
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
  if (name === 'reports') loadIntegration();
}

async function loadDashboard(query = '') {
  $('#main-content').setAttribute('aria-busy', 'true');
  try {
    const data = await api(`/api/dashboard${query ? `?q=${encodeURIComponent(query)}` : ''}`);
    const cards = [
      ['PHƯƠNG TIỆN', data.stats.vessels, 'Hồ sơ đang lưu'],
      ['PHIẾU NHÁP', data.stats.drafts, 'Chờ khách hoàn tất'],
      ['ĐÃ NỘP', data.stats.submitted, 'Có thể đưa vào báo cáo'],
      ['DỰ KIẾN ĐẾN HÔM NAY', data.stats.arrivingToday, 'Theo ETA đã khai'],
      ['CẢNH BÁO CHỨNG CHỈ', data.stats.certificateWarnings, 'Hết hạn hoặc còn dưới 30 ngày'],
    ];
    $('#stats').innerHTML = cards.map(card => `<article class="stat-card"><p>${card[0]}</p><strong>${card[1]}</strong><small>${card[2]}</small></article>`).join('');
    renderAttentionQueue(data.attention);
    if (state.currentUser?.role === 'ADMIN') {
      const admin = await api('/api/admin/operations-summary');
      const adminCards = [
        ['PHIẾU ĐÃ DUYỆT', admin.operations.approved, `${admin.operations.tons.toLocaleString('vi-VN')} tấn · ${admin.operations.teu.toLocaleString('vi-VN')} TEU`],
        ['CHỜ XỬ LÝ', admin.operations.pending, 'Theo các bước CV · QLC · BP'],
        ['CẢNH BÁO CHỨNG CHỈ', admin.fleet.certificateWarnings, `${admin.fleet.vessels} phương tiện`],
        ['IMPORT', admin.imports.jobs, `${admin.imports.rejectedRows} dòng bị từ chối`],
        ['BACKUP', admin.storage.backups, admin.storage.latestBackup || 'Chưa có backup'],
        ['AN NINH', admin.security.failedLogins, `${admin.security.disabledUsers} tài khoản bị khóa`],
      ];
      $('#admin-operations').hidden = false;
      $('#admin-operations-content').innerHTML = adminCards.map(card => `<article class="stat-card"><p>${card[0]}</p><strong>${card[1]}</strong><small>${esc(card[2])}</small></article>`).join('');
    } else {
      $('#admin-operations').hidden = true;
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

function renderDashboardMatches(items) {
  const container = $('#dashboard-search-results');
  if (!items.length) { container.innerHTML = ''; return; }
  container.innerHTML = items.map(v => `<article class="search-result-card"><strong>${esc(v.name)}</strong><small>${esc(v.registration_no)} · ${esc(v.vessel_type)}</small><span class="table-badge ${v.certificate_status === 'VALID' ? 'submitted' : 'draft'}">${certificateLabel(v.certificate_status)}</span></article>`).join('');
}

function certificateLabel(status) {
  return ({VALID:'Còn hạn',EXPIRING:'Sắp hết hạn',EXPIRED:'Đã hết hạn',UNKNOWN:'Chưa có hạn'})[status] || 'Chưa đối soát';
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
  $('#vessel-table').innerHTML = items.length ? `<table class="data-table responsive-table"><thead><tr><th>Phương tiện</th><th>Số đăng ký</th><th>Loại / Cấp</th><th>Trọng tải</th><th>Đăng kiểm</th><th></th></tr></thead><tbody>${items.map(v => `<tr><td data-label="Phương tiện"><strong>${esc(v.name)}</strong><br><small>${esc(v.organization_name || 'Chưa gán doanh nghiệp')}</small></td><td data-label="Số đăng ký">${esc(v.registration_no)}</td><td data-label="Loại / Cấp">${esc(v.vessel_type)} / ${esc(v.vessel_class)}</td><td data-label="Trọng tải">${number(v.deadweight_tons).toLocaleString('vi-VN')} tấn</td><td data-label="Đăng kiểm"><span class="table-badge ${v.certificate_status === 'VALID' ? 'submitted' : 'draft'}">${certificateLabel(v.certificate_status)}</span><br><small>${fmtDate(v.certificate_expiry_date)}</small></td><td data-label="Thao tác"><button data-verify-vessel="${v.id}">Đối soát</button> · <button data-edit-vessel="${v.id}">Chỉnh sửa</button></td></tr>`).join('')}</tbody></table>` : empty('Chưa có phương tiện', 'Thêm hồ sơ hoặc import file Excel mẫu.');
  $$('[data-edit-vessel]').forEach(button => button.onclick = () => openVessel(Number(button.dataset.editVessel)));
  $$('[data-verify-vessel]').forEach(button => button.onclick = () => verifyVessel(Number(button.dataset.verifyVessel)));
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
  return `<table class="data-table responsive-table"><thead><tr><th>Mã / Loại</th><th>Phương tiện</th><th>Hành trình</th><th>Thời gian</th><th>CV · QLC · BP</th><th>Trạng thái</th>${editable ? '<th></th>' : ''}</tr></thead><tbody>${items.map(d => `<tr><td data-label="Mã / Loại"><strong>${esc(d.reference_no)}</strong><br><small>${d.movement_type === 'DEPARTURE' ? 'Rời cảng' : 'Vào cảng'}${d.permit_no ? ` · ${esc(d.permit_no)}` : ''}</small></td><td data-label="Phương tiện">${esc(d.vessel_name)}<br><small>${esc(d.registration_no)} · ${esc(d.master_name)}</small></td><td data-label="Hành trình">${esc(d.last_port)} → ${esc(d.working_port)}${d.destination_port ? ` → ${esc(d.destination_port)}` : ''}</td><td data-label="Thời gian">${fmtDate(d.movement_type === 'DEPARTURE' ? d.etd : d.eta)}</td><td data-label="Duyệt"><span class="approval-dots">${approvalDot(d.cv_approval, 'CV')}${approvalDot(d.qlc_approval, 'QLC')}${approvalDot(d.bp_approval, 'BP')}</span></td><td data-label="Trạng thái"><span class="table-badge ${workflowTone(d.workflow_status)}">${workflowLabel(d.workflow_status)}</span></td>${editable ? `<td data-label="Thao tác">${['DRAFT','CHANGES_REQUESTED'].includes(d.workflow_status) ? `<button data-edit-declaration="${d.id}">Mở phiếu</button> · ` : ''}<button data-workflow="${d.id}">Chi tiết</button></td>` : ''}</tr>`).join('')}</tbody></table>`;
}

function approvalDot(status, label) { return `<span class="approval ${String(status).toLowerCase()}">${label}</span>`; }
function workflowLabel(status) { return ({DRAFT:'Nháp',PENDING_REVIEW:'Chờ CV',PENDING_QLC:'Chờ QLC',PENDING_BP:'Chờ BP',CHANGES_REQUESTED:'Cần bổ sung',APPROVED:'Đã duyệt',ISSUED:'Đã ban hành',REVOKED:'Đã thu hồi'})[status] || status; }
function workflowTone(status) { return ['APPROVED','ISSUED'].includes(status) ? 'submitted' : status === 'REVOKED' ? 'danger' : 'draft'; }

async function verifyVessel(id) {
  try {
    const result = await api(`/api/vessels/${id}/verify-registry`, {method:'POST'});
    toast(`${result.name}: ${certificateLabel(result.certificate_status)}. Chỉ đối soát ngày hết hạn nội bộ.`);
    await Promise.all([loadVessels(), loadDashboard()]);
  } catch (error) { toast(error.message, true); }
}

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
  const strip = $('#crew-warning-strip');
  strip.classList.toggle('visible', warnings.length > 0);
  strip.textContent = warnings.length ? `${warnings.length} chứng chỉ đã hết hạn hoặc sẽ hết hạn trong 30 ngày. Cần rà soát trước khi phân công chuyến.` : '';
  $('#crew-table').innerHTML = items.length ? `<table class="data-table responsive-table"><thead><tr><th>Họ tên</th><th>Chức danh</th><th>Phương tiện</th><th>Chứng chỉ</th><th>Hạn</th><th></th></tr></thead><tbody>${items.map(item => `<tr><td data-label="Họ tên"><strong>${esc(item.full_name)}</strong><br><small>${esc(item.phone || '')}</small></td><td data-label="Chức danh">${esc(item.crew_role)}</td><td data-label="Phương tiện">${esc(item.vessel_name || 'Chưa phân công')}<br><small>${esc(item.registration_no || '')}</small></td><td data-label="Chứng chỉ">${esc(item.professional_certificate_type)}<br><small>${esc(item.professional_certificate_no)}</small></td><td data-label="Hạn"><span class="table-badge ${item.certificate_status === 'VALID' ? 'submitted' : 'draft'}">${certificateLabel(item.certificate_status)}</span><br><small>${fmtDate(item.certificate_expiry_date)}</small></td><td data-label="Thao tác"><button data-edit-crew="${item.id}">Chỉnh sửa</button></td></tr>`).join('')}</tbody></table>` : empty('Chưa có Crew List', 'Thêm thuyền trưởng hoặc thuyền viên cùng chứng chỉ chuyên môn.');
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

async function openDeclaration(id = null) {
  if (!state.vessels.length) await loadVessels();
  if (!state.crew.length) await loadCrew();
  const draft = localStorage.getItem('tanthuan-declaration-draft');
  const existing = id ? state.declarations.find(item => item.id === id) : (draft ? JSON.parse(draft) : {});
  state.editingDeclaration = existing || {};
  const d = state.editingDeclaration;
  $('#declaration-fields').innerHTML = `
    <section class="form-section"><h3>A. Thông tin chung và phương tiện</h3><div class="section-grid">
      ${selectField('movement_type','Loại phiếu',['ARRIVAL','DEPARTURE'],d.movement_type || 'ARRIVAL','required')}
      ${field('company_name','Tên doanh nghiệp / Đại lý',d.company_name,'text','required class="wide-field"')}
      ${field('declaration_date','Ngày khai báo',d.declaration_date || new Date().toISOString().slice(0,10),'date','required')}
      <label>* Chọn hồ sơ phương tiện<select name="vessel_id" id="declaration-vessel" required><option value="">Chọn phương tiện</option>${state.vessels.map(v => `<option value="${v.id}" ${Number(d.vessel_id) === v.id ? 'selected' : ''}>${esc(v.name)} — ${esc(v.registration_no)}</option>`).join('')}</select></label>
      ${field('vessel_name','Tên phương tiện',d.vessel_name,'text','required')}
      ${field('registration_no','Số đăng ký',d.registration_no,'text','required')}
      ${selectField('vessel_type','Loại phương tiện',state.catalogs.vesselTypes,d.vessel_type,'required')}
      ${selectField('vessel_class','Cấp phương tiện',state.catalogs.vesselClasses,d.vessel_class,'required')}
      ${field('length_m','Chiều dài (m)',d.length_m,'number','step="0.01" min="0"')}
      ${field('deadweight_tons','Trọng tải toàn phần',d.deadweight_tons,'number','step="0.01" min="0"')}
      ${field('gross_tonnage','Dung tích (GT)',d.gross_tonnage,'number','step="0.01" min="0"')}
      ${field('certificate_expiry_date','Hạn GCN ATKT & BVMT',d.certificate_expiry_date,'date')}
      ${field('crew_count','Số thuyền viên',d.crew_count,'number','min="0"')}
      ${field('passenger_count','Số hành khách',d.passenger_count,'number','min="0"')}
    </div></section>
    <section class="form-section"><h3>B. Hành trình</h3><div class="section-grid">
      ${field('last_port','Cảng rời cuối cùng',d.last_port,'text','required list="ports-list"')}
      ${field('working_port','Cảng / cầu bến đến làm hàng',d.working_port,'text','required list="ports-list"')}
      ${field('destination_port','Cảng đích',d.destination_port,'text','list="ports-list"')}
      ${field('eta','Thời gian dự kiến đến',d.eta,'datetime-local','required')}
      ${field('etd','Thời gian dự kiến rời',d.etd,'datetime-local','required')}
      ${field('actual_arrival_at','Thời gian đến thực tế',d.actual_arrival_at,'datetime-local')}
      ${field('actual_departure_at','Thời gian rời thực tế',d.actual_departure_at,'datetime-local')}
      ${field('purpose','Mục đích chuyến / làm hàng',d.purpose,'text','class="wide-field"')}
      ${field('cargo_description','Mô tả hàng hóa tổng quát',d.cargo_description,'text','class="wide-field"')}
      <datalist id="ports-list"></datalist>
    </div></section>
    ${cargoFields('unload','C. Hàng hóa dỡ tại cảng',d.unload || {},false)}
    ${cargoFields('load','D. Hàng hóa xếp tại cảng',d.load || {},true)}
    <section class="form-section"><h3>E. Crew List đi theo chuyến</h3><div class="section-grid">
      <label class="wide-field">Chọn thuyền trưởng / thuyền viên<select name="crew_ids" multiple size="5">${state.crew.map(member => `<option value="${member.id}" ${(d.crew || []).some(item => item.id === member.id) ? 'selected' : ''}>${esc(member.full_name)} — ${esc(member.crew_role)} — ${certificateLabel(member.certificate_status)}</option>`).join('')}</select></label>
      <div class="attachment-field wide-field"><strong>Kiểm tra chứng chỉ trước khi nộp</strong><p>Thành viên sắp hết hạn hoặc đã hết hạn sẽ hiển thị cảnh báo trong Crew List và dashboard.</p></div>
    </div></section>
    <section class="form-section"><h3>F. Liên hệ và file đính kèm</h3><div class="section-grid">
      ${field('master_name','Họ tên thuyền trưởng',d.master_name,'text','required list="masters-list"')}
      ${field('master_phone','Số điện thoại thuyền trưởng',d.master_phone,'tel','required')}
      <label class="attachment-field wide-field">Đính kèm hình ảnh / PDF / Word / Excel<input name="attachments" type="file" multiple accept=".jpg,.jpeg,.png,.webp,.pdf,.doc,.docx,.xls,.xlsx"><small>Mỗi file tối đa 12 MB. File được lưu cùng phiếu khai báo.</small></label>
      <datalist id="masters-list"></datalist>
    </div></section>`;
  $('#declaration-vessel').onchange = fillFromVessel;
  ['unload','load'].forEach(prefix => $$(`[name^="${prefix}_cont"]`, $('#declaration-form')).forEach(input => input.addEventListener('input', () => calculateCargo(prefix))));
  $('#declaration-fields').addEventListener('input', rememberDraft);
  loadSuggestions();
  $('#declaration-dialog').showModal();
}

function fillFromVessel(event) {
  const vessel = state.vessels.find(v => v.id === Number(event.target.value));
  if (!vessel) return;
  const form = $('#declaration-form');
  const mapping = ['vessel_name:name','registration_no:registration_no','vessel_type:vessel_type','vessel_class:vessel_class','length_m:length_m','deadweight_tons:deadweight_tons','gross_tonnage:gross_tonnage','certificate_expiry_date:certificate_expiry_date','crew_count:min_crew'];
  mapping.forEach(pair => { const [target, source] = pair.split(':'); form.elements[target].value = vessel[source] ?? ''; });
  form.elements.company_name.value = vessel.organization_name || form.elements.company_name.value;
  rememberDraft();
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
  data.crew_ids = [...$('#declaration-form').elements.crew_ids.selectedOptions].map(option => Number(option.value));
  delete data.attachments;
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

function rememberDraft() {
  try { localStorage.setItem('tanthuan-declaration-draft', JSON.stringify(declarationData())); } catch (_) {}
}

async function saveDeclaration(event) {
  event.preventDefault();
  const form = $('#declaration-form');
  const submit = event.submitter?.value === 'submit';
  if (!form.reportValidity()) return;
  setSubmitting(form, event.submitter, true, submit ? 'Đang nộp…' : 'Đang lưu…');
  try {
    const result = await api(`/api/declarations?submit=${submit}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(declarationData())});
    const files = [...$('#declaration-form').elements.attachments.files];
    for (const file of files) {
      await api(`/api/declarations/${result.id}/attachments?filename=${encodeURIComponent(file.name)}`, {method:'POST', headers:{'Content-Type':file.type || 'application/octet-stream'}, body:file});
    }
    localStorage.removeItem('tanthuan-declaration-draft');
    $('#declaration-dialog').close();
    toast(`${submit ? 'Phiếu đã được nộp và khóa dữ liệu.' : 'Đã lưu phiếu nháp.'}${files.length ? ` Đã tải ${files.length} file.` : ''}`);
    await loadDeclarations();
    await loadDashboard();
  } catch (error) { toast(error.message, true); }
  finally { setSubmitting(form, event.submitter, false); }
}

async function loadSuggestions() {
  try {
    const [last, work, destination, masters] = await Promise.all(['last_port','working_port','destination_port','master_name'].map(name => api(`/api/suggestions?field=${name}`)));
    $('#ports-list').innerHTML = [...new Set([...last,...work,...destination])].map(value => `<option value="${esc(value)}">`).join('');
    $('#masters-list').innerHTML = masters.map(value => `<option value="${esc(value)}">`).join('');
  } catch (_) {}
}

async function openWorkflow(id) {
  const declaration = state.declarations.find(item => item.id === id);
  if (!declaration) return;
  state.workflowDeclaration = declaration;
  $('#workflow-title').textContent = `${declaration.reference_no} · ${declaration.vessel_name}`;
  $('#workflow-summary').innerHTML = `<article><small>LOẠI PHIẾU</small><strong>${declaration.movement_type === 'DEPARTURE' ? 'Rời cảng' : 'Vào cảng'}</strong></article><article><small>TRẠNG THÁI</small><strong>${workflowLabel(declaration.workflow_status)}</strong></article><article><small>GIẤY PHÉP</small><strong>${esc(declaration.permit_no || 'Chưa ban hành')}</strong></article><article><small>DUYỆT</small><span class="approval-dots">${approvalDot(declaration.cv_approval, 'CV')}${approvalDot(declaration.qlc_approval, 'QLC')}${approvalDot(declaration.bp_approval, 'BP')}</span></article>`;
  const events = await api(`/api/declarations/${id}/events`);
  $('#workflow-timeline').innerHTML = events.length ? events.map(event => `<article><span></span><div><strong>${workflowLabel(event.to_status)} · ${esc(event.actor_name)}</strong><small>${esc(event.actor_role)} · ${fmtDate(event.created_at)}</small><p>${esc(event.note || event.action)}</p></div></article>`).join('') : empty('Chưa có lịch sử', 'Dấu vết sẽ xuất hiện khi phiếu được xử lý.');

  // Dynamic action dropdown based on user role
  const select = $('#workflow-form select[name="action"]');
  const role = state.currentUser ? state.currentUser.role : '';
  let html = '<option value="">Chọn</option>';
  if (role === 'CV') {
    html += '<option value="CV_APPROVE">CV duyệt</option><option value="REQUEST_CHANGES">Yêu cầu bổ sung</option>';
  } else if (role === 'QLC') {
    html += '<option value="QLC_APPROVE">QLC duyệt</option><option value="REQUEST_CHANGES">Yêu cầu bổ sung</option>';
  } else if (role === 'BP') {
    html += '<option value="BP_APPROVE">BP duyệt</option><option value="ISSUE">Ban hành giấy phép</option><option value="REVOKE">Thu hồi giấy phép</option><option value="REQUEST_CHANGES">Yêu cầu bổ sung</option>';
  }
  select.innerHTML = html;

  // Hide workflow action form for customers / admins
  const showForm = ['CV', 'QLC', 'BP'].includes(role);
  $('#workflow-form').style.display = showForm ? 'block' : 'none';

  $('#workflow-dialog').showModal();
}

async function saveWorkflow(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = values(event.currentTarget);
  if (['REQUEST_CHANGES','REVOKE'].includes(data.action) && !data.note.trim()) return toast('Cần nhập lý do cho thao tác này.', true);
  setSubmitting(form, event.submitter, true, 'Đang ghi nhận…');
  try {
    await api(`/api/declarations/${state.workflowDeclaration.id}/workflow`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    event.currentTarget.reset();
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

async function importFile(input, path) {
  const file = input.files[0];
  if (!file) return;
  $('#import-result').innerHTML = 'Đang đọc và kiểm tra file…';
  try {
    const result = await api(path, {method:'POST', headers:{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, body:file});
    $('#import-result').innerHTML = `<div><strong>Import thành công</strong><p>Đã nhận ${result.accepted || 0} bản ghi.${result.rejected?.length ? ` Có ${result.rejected.length} dòng bị từ chối.` : ''}</p></div>`;
    toast('Đã map dữ liệu Excel vào hệ thống.');
    await Promise.all([loadVessels(), loadDeclarations(), loadDashboard()]);
  } catch (error) { $('#import-result').innerHTML = `<div><strong>Không thể import</strong><p>${esc(error.message)}</p></div>`; toast(error.message, true); }
  finally { input.value = ''; }
}

function exportReport(kind) {
  const from = $('#report-from').value || '1900-01-01';
  const to = $('#report-to').value || '2999-12-31';
  location.href = `/api/reports/${kind}?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;
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

async function prepareSync() {
  try {
    const result = await api('/api/integrations/prepare-sync', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({from:$('#report-from').value,to:$('#report-to').value})});
    toast(`Đã chuẩn bị SYNC-${result.id} gồm ${result.recordCount} bản ghi. Chưa gửi ra ngoài.`);
    await loadIntegration();
  } catch (error) { toast(error.message, true); }
}

async function init() {
  window.addEventListener('hashchange', route);
  $('#menu-toggle').onclick = () => $('.sidebar').classList.toggle('open');
  $('#theme-toggle').onclick = () => { const root = document.documentElement; const next = root.dataset.theme === 'dark' ? 'light' : 'dark'; root.dataset.theme = next; localStorage.setItem('tanthuan-theme', next); };
  document.documentElement.dataset.theme = localStorage.getItem('tanthuan-theme') || 'dark';

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
    $('#user-display').textContent = `${state.currentUser.full_name} (${state.currentUser.role})`;
    $('#logout-button').style.display = 'inline-block';

    // Role-based UI visibility constraints
    const isCustomer = state.currentUser.role === 'CUSTOMER';
    const isAdmin = state.currentUser.role === 'ADMIN';
    const isReviewer = ['CV', 'QLC', 'BP'].includes(state.currentUser.role);

    $$('[data-action="new-declaration"]').forEach(btn => btn.style.display = isReviewer ? 'none' : 'inline-block');
    const addVesselBtn = $('#add-vessel');
    if (addVesselBtn) addVesselBtn.style.display = isReviewer ? 'none' : 'inline-block';
    const addCrewBtn = $('#add-crew');
    if (addCrewBtn) addCrewBtn.style.display = isReviewer ? 'none' : 'inline-block';

    const importNav = $('nav a[href="#import"]');
    if (importNav) importNav.style.display = (isCustomer || isAdmin) ? 'block' : 'none';

    const reportsNav = $('nav a[href="#reports"]');
    if (reportsNav) reportsNav.style.display = 'block';

  } catch (err) {
    state.currentUser = null;
    $('#user-display').textContent = '';
    $('#logout-button').style.display = 'none';
    $('#login-dialog').showModal();
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

  const loginForm = $('#login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const res = await api('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(values(loginForm))
        });
        localStorage.setItem('token', res.access_token);
        $('#login-dialog').close();
        toast('Đăng nhập thành công');
        init(); // reload all data
      } catch (error) { toast(error.message, true); }
    });
  }

  $('#add-crew').onclick = () => openCrew();
  $$('[data-close-dialog]').forEach(button => button.onclick = () => document.getElementById(button.dataset.closeDialog).close());
  let declarationTimer;
  ['declaration-search','master-filter'].forEach(id => $(`#${id}`).addEventListener('input', () => { clearTimeout(declarationTimer); declarationTimer = setTimeout(applyDeclarationFilters, 250); }));
  ['movement-filter','workflow-filter','declaration-from','declaration-to'].forEach(id => $(`#${id}`).addEventListener('change', applyDeclarationFilters));
  $('#clear-declaration-filter').onclick = () => { ['declaration-search','movement-filter','workflow-filter','master-filter','declaration-from','declaration-to'].forEach(id => $(`#${id}`).value = ''); applyDeclarationFilters(); };
  $('#import-vessels').onchange = event => importFile(event.target, '/api/import/vessels');
  $('#import-declaration').onchange = event => importFile(event.target, '/api/import/declaration');
  $$('[data-report]').forEach(button => button.onclick = () => exportReport(button.dataset.report));
  $('#prepare-sync').onclick = prepareSync;
  const today = new Date(); $('#report-to').value = today.toISOString().slice(0,10); $('#report-from').value = `${today.getFullYear()}-01-01`;
  try {
    [state.catalogs, state.vessels, state.organizations, state.crew] = await Promise.all([api('/api/catalogs'), api('/api/vessels'), api('/api/organizations'), api('/api/crew')]);
    $('#api-state').className = 'state-badge ok'; $('#api-state').textContent = 'Đã kết nối';
  } catch (error) { $('#api-state').className = 'state-badge pending'; $('#api-state').textContent = 'Mất kết nối'; toast(error.message, true); }
  route();
}

document.addEventListener('DOMContentLoaded', init);
