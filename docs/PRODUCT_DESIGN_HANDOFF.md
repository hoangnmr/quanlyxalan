# Cong thong tin khai bao PTTND - Product Design Handoff

## 1. Website Goal

Build a company-hosted web application for TIEN-TAN THUAN PORT customers to maintain
inland-waterway vessel profiles, submit one declaration per port call, reuse
prior data, import the existing Excel forms, and produce periodic Appendix 1,
2, and 3 reports for the Maritime Administration.

## 2. Target Users

- Customer declarant: maintains company/vessel data and submits port-call forms.
- Port operations reviewer: reviews declarations and exports periodic reports.
- System administrator: maintains controlled lists and operational settings.

## 3. Required Pages And Flows

1. Operations dashboard with current declarations and exception counts.
2. Vessel directory based on `Ho_so_phuong_tien_thuy_noi_dia.xlsx`.
3. Guided declaration form based on
   `Phieu_khai_bao_PTTND_truoc_khi_den_cang.xlsx`.
4. Excel import with deterministic field mapping and row-level results.
5. Appendix 1 daily plan, Appendix 2 monthly/cumulative summary, and Appendix 3
   detailed port-call export.
6. Audit history for create, edit, submit, and import actions.
7. Crew List with professional certificate expiry warnings.
8. Images/PDF/Word/Excel attachments stored with each declaration.
9. Connector-ready Maritime Authority synchronization with prepared payloads.

## 4. CVF Web Design DNA

Style mode: Ops / Industrial. Use a compact operational shell, clear state
labels, dense tables, visible required fields, and restrained motion. All
component colors use theme tokens in dark and light modes. The product accent
is port teal, remapped through CVF accent roles.

## 5. UX Direction

- Vietnamese-first labels with short operational language.
- Select lists for vessel type, vessel class, shell material, cargo type, and
  cargo movement type.
- Selecting a vessel copies the latest profile into a declaration snapshot.
- Recent port, master, company, and cargo values are suggested from saved data.
- Browser draft recovery protects an unfinished declaration from accidental
  refreshes.
- Derived container totals and TEU values are read-only and deterministic.

## 6. Protected Constraints

- Frontend and backend stay in separate directories.
- SQLite is the initial durable store; deployment must use a persistent volume.
- No AI decides legal validity or approval status.
- A submitted declaration is a customer assertion, not a Maritime
  Administration approval.
- Original source documents remain in the sibling `QD05_06` project.
- Secrets and production customer data must not be committed.

## 7. Build Instructions

- Python standard-library backend and static frontend, with no Node dependency.
- API writes use transactions, server-side validation, and an audit trail.
- Excel import accepts the two operator-provided workbook shapes.
- Report generation derives only from stored declaration snapshots.
- Keep production authentication and external integrations explicitly pending.

## 8. Acceptance Checklist

- [x] Product scope and source forms mapped.
- [x] Frontend/backend boundary selected.
- [x] SQLite persistence selected.
- [x] Vessel CRUD and reusable company data work.
- [x] Declaration draft and submit flow work.
- [x] TEU formulas match the source workbook.
- [x] Excel import reports accepted and rejected rows.
- [x] Appendix 1/2/3 exports are available.
- [x] Desktop and mobile layouts are usable.
- [x] API and CVF workspace checks pass.
- [x] Crew List and certificate warning flow work.
- [x] Attachment upload flow works with allowed file types.
- [x] Maritime Authority sync jobs remain preview-only until configured.
