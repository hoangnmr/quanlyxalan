const state = {
  catalogs: {}, vessels: [], declarations: [], organizations: [],
  declarationFilter: '', editingVessel: null, editingDeclaration: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value = '') => String(value ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const number = value => Number(value || 0);
const fmtDate = value => value ? new Intl.DateTimeFormat('vi-VN', {dateStyle:'short', timeStyle: value.includes('T') ? 'short' : undefined}).format(new Date(value)) : '—';

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const type = response.headers.get('content-type') || '';
  const body = type.includes('json') ? await response.json() : await response.blob();
  if (!response.ok) throw new Error(body.error || 'Yêu cầu không thành công.');
  return body;
}

function toast(message, error = false) {
  const node = document.createElement('div');
  node.className = `toast${error ? ' error' : ''}`;
  node.textContent = message;
  $('#toast-region').append(node);
  setTimeout(() => node.remove(), 4200);
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
  return ({dashboard:'Tổng quan khai báo', declarations:'Phiếu khai báo', vessels:'Hồ sơ phương tiện', import:'Import dữ liệu Excel', reports:'Báo cáo Cảng vụ'})[route] || 'Tổng quan khai báo';
}

function route() {
  const name = location.hash.replace('#', '') || 'dashboard';
  $$('.page').forEach(page => page.classList.toggle('active', page.dataset.page === name));
  $$('nav a').forEach(link => link.classList.toggle('active', link.dataset.route === name));
  $('#page-context').textContent = pageName(name);
  $('.sidebar').classList.remove('open');
  if (name === 'dashboard') loadDashboard();
  if (name === 'vessels') loadVessels();
  if (name === 'declarations') loadDeclarations();
}

async function loadDashboard() {
  try {
    const data = await api('/api/dashboard');
    const cards = [
      ['PHƯƠNG TIỆN', data.stats.vessels, 'Hồ sơ đang lưu'],
      ['PHIẾU NHÁP', data.stats.drafts, 'Chờ khách hoàn tất'],
      ['ĐÃ NỘP', data.stats.submitted, 'Có thể đưa vào báo cáo'],
      ['DỰ KIẾN ĐẾN HÔM NAY', data.stats.arrivingToday, 'Theo ETA đã khai'],
    ];
    $('#stats').innerHTML = cards.map(card => `<article class="stat-card"><p>${card[0]}</p><strong>${card[1]}</strong><small>${card[2]}</small></article>`).join('');
    $('#recent-table').innerHTML = declarationTable(data.recent);
  } catch (error) { toast(error.message, true); }
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
  $('#vessel-table').innerHTML = items.length ? `<table class="data-table"><thead><tr><th>Phương tiện</th><th>Số đăng ký</th><th>Loại / Cấp</th><th>Trọng tải</th><th>Hạn GCN</th><th></th></tr></thead><tbody>${items.map(v => `<tr><td><strong>${esc(v.name)}</strong><br><small>${esc(v.organization_name || 'Chưa gán doanh nghiệp')}</small></td><td>${esc(v.registration_no)}</td><td>${esc(v.vessel_type)} / ${esc(v.vessel_class)}</td><td>${number(v.deadweight_tons).toLocaleString('vi-VN')} tấn</td><td>${fmtDate(v.certificate_expiry_date)}</td><td><button data-edit-vessel="${v.id}">Chỉnh sửa</button></td></tr>`).join('')}</tbody></table>` : empty('Chưa có phương tiện', 'Thêm hồ sơ hoặc import file Excel mẫu.');
  $$('[data-edit-vessel]').forEach(button => button.onclick = () => openVessel(Number(button.dataset.editVessel)));
}

async function loadDeclarations() {
  try {
    state.declarations = await api(`/api/declarations${state.declarationFilter ? `?status=${state.declarationFilter}` : ''}`);
    $('#declaration-count').textContent = `${state.declarations.length} phiếu`;
    $('#declaration-table').innerHTML = declarationTable(state.declarations, true);
    $$('[data-edit-declaration]').forEach(button => button.onclick = () => openDeclaration(Number(button.dataset.editDeclaration)));
  } catch (error) { toast(error.message, true); }
}

function declarationTable(items = [], editable = false) {
  if (!items.length) return empty('Chưa có phiếu khai báo', 'Tạo phiếu đầu tiên từ một hồ sơ phương tiện.');
  return `<table class="data-table"><thead><tr><th>Mã phiếu</th><th>Phương tiện</th><th>Hành trình</th><th>ETA</th><th>Hàng dỡ / xếp</th><th>Trạng thái</th>${editable ? '<th></th>' : ''}</tr></thead><tbody>${items.map(d => `<tr><td><strong>${esc(d.reference_no)}</strong></td><td>${esc(d.vessel_name)}<br><small>${esc(d.registration_no)}</small></td><td>${esc(d.last_port)} → ${esc(d.working_port)}</td><td>${fmtDate(d.eta)}</td><td>${number(d.unload?.teu)} / ${number(d.load?.teu)} TEU</td><td><span class="table-badge ${d.status === 'SUBMITTED' ? 'submitted' : 'draft'}">${d.status === 'SUBMITTED' ? 'Đã nộp' : 'Nháp'}</span></td>${editable ? `<td>${d.status === 'DRAFT' ? `<button data-edit-declaration="${d.id}">Mở phiếu</button>` : 'Đã khóa'}</td>` : ''}</tr>`).join('')}</tbody></table>`;
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
  const data = values($('#vessel-form'));
  data.organization = {name: data.organization_name};
  delete data.organization_name;
  if (state.editingVessel?.id) data.id = state.editingVessel.id;
  try {
    await api('/api/vessels', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    $('#vessel-dialog').close();
    toast('Đã lưu hồ sơ phương tiện.');
    await loadVessels();
  } catch (error) { toast(error.message, true); }
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
  const draft = localStorage.getItem('tanthuan-declaration-draft');
  const existing = id ? state.declarations.find(item => item.id === id) : (draft ? JSON.parse(draft) : {});
  state.editingDeclaration = existing || {};
  const d = state.editingDeclaration;
  $('#declaration-fields').innerHTML = `
    <section class="form-section"><h3>A. Thông tin chung và phương tiện</h3><div class="section-grid">
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
      <datalist id="ports-list"></datalist>
    </div></section>
    ${cargoFields('unload','C. Hàng hóa dỡ tại cảng',d.unload || {},false)}
    ${cargoFields('load','D. Hàng hóa xếp tại cảng',d.load || {},true)}
    <section class="form-section"><h3>E. Liên hệ</h3><div class="section-grid">
      ${field('master_name','Họ tên thuyền trưởng',d.master_name,'text','required list="masters-list"')}
      ${field('master_phone','Số điện thoại thuyền trưởng',d.master_phone,'tel','required')}
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
  ['unload','load'].forEach(prefix => {
    data[prefix] = {cargo_type:data[`${prefix}_cargo_type`],movement_type:data[`${prefix}_movement_type`],cargo_name:data[`${prefix}_cargo_name`],cont20_full:data[`${prefix}_cont20_full`],cont20_empty:data[`${prefix}_cont20_empty`],cont40_full:data[`${prefix}_cont40_full`],cont40_empty:data[`${prefix}_cont40_empty`],tons:data[`${prefix}_tons`]};
    Object.keys(data).filter(key => key.startsWith(`${prefix}_`)).forEach(key => delete data[key]);
  });
  if (state.editingDeclaration?.id) data.id = state.editingDeclaration.id;
  return data;
}

function rememberDraft() {
  try { localStorage.setItem('tanthuan-declaration-draft', JSON.stringify(declarationData())); } catch (_) {}
}

async function saveDeclaration(event) {
  event.preventDefault();
  const submit = event.submitter?.value === 'submit';
  if (!$('#declaration-form').reportValidity()) return;
  try {
    await api(`/api/declarations?submit=${submit}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(declarationData())});
    localStorage.removeItem('tanthuan-declaration-draft');
    $('#declaration-dialog').close();
    toast(submit ? 'Phiếu đã được nộp và khóa dữ liệu.' : 'Đã lưu phiếu nháp.');
    await loadDeclarations();
    await loadDashboard();
  } catch (error) { toast(error.message, true); }
}

async function loadSuggestions() {
  try {
    const [last, work, destination, masters] = await Promise.all(['last_port','working_port','destination_port','master_name'].map(name => api(`/api/suggestions?field=${name}`)));
    $('#ports-list').innerHTML = [...new Set([...last,...work,...destination])].map(value => `<option value="${esc(value)}">`).join('');
    $('#masters-list').innerHTML = masters.map(value => `<option value="${esc(value)}">`).join('');
  } catch (_) {}
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

async function init() {
  window.addEventListener('hashchange', route);
  $('#menu-toggle').onclick = () => $('.sidebar').classList.toggle('open');
  $('#theme-toggle').onclick = () => { const root = document.documentElement; const next = root.dataset.theme === 'dark' ? 'light' : 'dark'; root.dataset.theme = next; localStorage.setItem('tanthuan-theme', next); };
  document.documentElement.dataset.theme = localStorage.getItem('tanthuan-theme') || 'dark';
  $$('[data-route-link]').forEach(button => button.onclick = () => location.hash = button.dataset.routeLink);
  $$('[data-action="new-declaration"]').forEach(button => button.onclick = () => openDeclaration());
  $('#add-vessel').onclick = () => openVessel();
  $('#vessel-search').addEventListener('input', renderVessels);
  $('#vessel-form').addEventListener('submit', saveVessel);
  $('#declaration-form').addEventListener('submit', saveDeclaration);
  $$('[data-close-dialog]').forEach(button => button.onclick = () => document.getElementById(button.dataset.closeDialog).close());
  $$('[data-filter-status]').forEach(button => button.onclick = () => { state.declarationFilter = button.dataset.filterStatus; $$('[data-filter-status]').forEach(item => item.classList.toggle('active', item === button)); loadDeclarations(); });
  $('#import-vessels').onchange = event => importFile(event.target, '/api/import/vessels');
  $('#import-declaration').onchange = event => importFile(event.target, '/api/import/declaration');
  $$('[data-report]').forEach(button => button.onclick = () => exportReport(button.dataset.report));
  const today = new Date(); $('#report-to').value = today.toISOString().slice(0,10); $('#report-from').value = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-01`;
  try {
    [state.catalogs, state.vessels, state.organizations] = await Promise.all([api('/api/catalogs'), api('/api/vessels'), api('/api/organizations')]);
    $('#api-state').className = 'state-badge ok'; $('#api-state').textContent = 'Đã kết nối';
  } catch (error) { $('#api-state').className = 'state-badge pending'; $('#api-state').textContent = 'Mất kết nối'; toast(error.message, true); }
  route();
}

document.addEventListener('DOMContentLoaded', init);
