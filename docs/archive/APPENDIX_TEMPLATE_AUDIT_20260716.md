# Đối chiếu 3 Phụ lục Excel (templates/) với code xuất báo cáo — 2026-07-16

## Mục tiêu

Kiểm tra xem cấu trúc bảng (số cột, tiêu đề, merge cells, thứ tự dữ liệu) do
backend sinh ra khi xuất Excel cho 3 báo cáo hoạt động Cảng có khớp với 3 file
mẫu phụ lục do Cảng vụ Hàng hải ban hành hay không:

- `templates/Phụ lục 1.docx` — Kế hoạch hoạt động của phương tiện thủy nội địa
- `templates/Phụ lục 2.docx` — Khối lượng hàng hóa, lượt tàu, hành khách thông qua cảng
- `templates/Phụ lục 3.xlsx` — Báo cáo chi tiết phương tiện thủy nội địa ra, vào cảng biển

Đối tượng code tương ứng: [backend/xlsx_io.py](../backend/xlsx_io.py) (hàm dựng
workbook) và [backend/app.py](../backend/app.py) (hàm dựng `rows` dữ liệu +
endpoint `GET /api/reports/{kind}`).

## Phương pháp

Không có công cụ/skill đọc spreadsheet chuyên dụng khả dụng trong phiên làm
việc này (skill "Spreadsheets" không tồn tại trong danh sách skill được cấp).
Thay vì suy đoán nội dung từ tên file, đã đọc **toàn bộ** nội dung gốc bằng
script Python, không lấy mẫu:

1. **File `.docx`** (`Phụ lục 1.docx`, `Phụ lục 2.docx`): dùng thư viện
   `python-docx`. Duyệt hết `document.paragraphs` (in mọi đoạn có text) và hết
   `document.tables` — với mỗi bảng in `rows x cols` rồi in **từng hàng, từng
   ô theo đúng vị trí** (không bỏ ô trống ở giữa, không rút gọn).
2. **File `.xlsx`** (`Phụ lục 3.xlsx`): dùng thư viện `openpyxl`
   (`data_only=True`). Liệt kê tên tất cả sheet trước, sau đó với mỗi sheet in
   `ws.dimensions`, `max_row`, `max_column` để biết chắc phạm vi dữ liệu thật
   (tránh bỏ sót dòng/cột do vùng in hoặc sheet ẩn), rồi in toàn bộ ô có giá trị
   theo chỉ số hàng/cột tuyệt đối, cộng với danh sách đầy đủ `merged_cells.ranges`.
3. Do lỗi encoding console (`cp1252` không encode được tiếng Việt), toàn bộ
   output được ghi ra file `.txt` với `encoding="utf-8"` rồi đọc lại bằng công
   cụ đọc file, thay vì in thẳng ra terminal — đảm bảo không mất/méo ký tự có dấu.
4. Sau khi có nội dung gốc đầy đủ, đọc code sinh workbook
   (`_make_appendix1_xlsx`, `_make_appendix2_xlsx`, `_make_appendix3_xlsx` trong
   `xlsx_io.py`) và code dựng dữ liệu (`_appendix1_rows`, `_appendix2_rows`,
   `_appendix3_rows`, `_cargo_column_start` trong `app.py`), đối chiếu **thủ
   công từng cột** giữa template và code — không chạy thử export thực tế trong
   lượt kiểm tra này (xem mục "Chưa kiểm chứng" bên dưới).

## Kết quả quét nguyên văn từng phụ lục

### Phụ lục 1.docx

- 5 đoạn văn bản (tiêu đề, số văn bản kèm theo, tên báo cáo, dòng "Ngày…", tên
  doanh nghiệp, ghi chú container).
- 1 bảng, **8 hàng x 16 cột**. 3 hàng đầu là header lồng nhau (merge dọc/ngang),
  hàng 4 là header con cuối cùng, hàng 5-8 là hàng dữ liệu mẫu trống (1, 2, 3, …).
- Thứ tự 16 cột header (hàng cuối, đã "phẳng hóa" các nhóm merge):

  ```
  1  TT
  2  Tên
  3  Số đăng ký
  4  Cấp phương tiện
  5  Công dụng
  6  Ngày hết hạn GCNATKT&BVMT
  7  Lượng hàng (tấn/ teu)        ← con của "Khả năng khai thác"
  8  Sức chở (khách)              ← con của "Khả năng khai thác"
  9  Đến — Vị trí (Cảng/cầu)
  10 Đến — Thời gian (ngày, giờ)
  11 Rời — Vị trí (Cảng/cầu)
  12 Rời — Thời gian (ngày, giờ)
  13 Hàng dỡ (loại, số lượng)
  14 Hàng xếp (loại, số lượng)
  15 Số thuyền viên/ Hành khách
  16 Tên và số điện thoại thuyền trưởng
  ```

### Phụ lục 2.docx

- 4 đoạn văn bản (tiêu đề, số văn bản kèm theo, tên báo cáo 2 dòng, "Tháng …").
- 1 bảng, **8 hàng x 16 cột**. Hàng 4 là số thứ tự cột (A, B, 1..14), hàng 5-7
  là 3 dòng dữ liệu mẫu ("I. Bến cảng biển", "- Bến cảng…", "- ………"), hàng 8 là
  "Tổng".
- Thứ tự 16 cột header (đã phẳng hóa):

  ```
  1  STT
  2  Chỉ tiêu
  3  Container — Thực hiện tháng báo cáo — Tấn
  4  Container — Thực hiện tháng báo cáo — TEUs
  5  Container — Lũy kế đến tháng báo cáo — Tấn
  6  Container — Lũy kế đến tháng báo cáo — TEUs
  7  Hàng khô — Thực hiện tháng báo cáo — Tấn
  8  Hàng khô — Lũy kế đến tháng báo cáo — Tấn
  9  Hàng lỏng — Thực hiện tháng báo cáo — Tấn
  10 Hàng lỏng — Lũy kế đến tháng báo cáo — Tấn
  11 Hàng XNK — Thực hiện tháng báo cáo — Tấn
  12 Hàng XNK — Lũy kế đến tháng báo cáo — Tấn
  13 Lượt tàu — Thực hiện tháng báo cáo — Lượt
  14 Lượt tàu — Lũy kế đến tháng báo cáo — Lượt
  15 Hành khách — Lượt tàu khách — Lượt
  16 Hành khách — Lượt khách — Lượt
  ```

  Lưu ý: tiêu đề gốc ghi "Tháng báo cáo" (báo cáo THÁNG), khác PL1/PL3 vốn
  không có kỳ cố định trong tên cột.

### Phụ lục 3.xlsx

- 1 sheet ("Sheet"), `dimensions=A1:AI16`, `max_row=16`, `max_col=35` (cột A→AI).
- Header 3 tầng (hàng 5, 6, 7), hàng 9 là số thứ tự cột (1..34, cột A không đánh
  số), hàng 10-14 là 5 dòng dữ liệu mẫu, hàng 15-16 là chữ ký người lập/thủ trưởng.
- 35 cột, nhóm cột 9-26 (0-indexed 8-25) là nhóm "Hàng hóa" chia 7 phân nhóm:

  ```
  cột(1-idx)  9-11   Xuất khẩu:        Tấn, Teus, Teus Rỗng
  cột(1-idx)  12-14  Nhập khẩu:        Tấn, Teus, Teus Rỗng
  cột(1-idx)  15-17  Nội địa đến:      Tấn, Teus, Tues Rỗng
  cột(1-idx)  18-20  Nội địa rời:      Tấn, Teus, Tues Rỗng
  cột(1-idx)  21-22  Chuyển tải:       Tấn, Tues        (không có cột Rỗng)
  cột(1-idx)  23-24  Quá cảnh(bốc dỡ): Tấn, Tues        (không có cột Rỗng)
  cột(1-idx)  25-26  Quá cảng(không bốc dỡ): Tấn, Teus  (không có cột Rỗng)
  cột(1-idx)  27-28  Hành khách (Lượt): Đến cảng, Rời cảng
  cột(1-idx)  29     Tên hàng
  cột(1-idx)  30     Cảng rời cuối cùng
  cột(1-idx)  31     Cảng đến (Cảng làm hàng)
  cột(1-idx)  32     Cảng đích
  cột(1-idx)  33     Ngày đến cảng
  cột(1-idx)  34     Ngày rời cảng
  cột(1-idx)  35     Đại lý PTND
  ```

  (0-indexed tương ứng để so với code: cột 9 = index 8, … — code dùng
  0-indexed `row[i]` trong danh sách 35 phần tử.)

## Đối chiếu với code

### Phụ lục 1 — `_make_appendix1_xlsx` + `_appendix1_rows`

- Số cột: template 16, code 16 (`A1:P4` merges, ghi tới cột P). **Khớp.**
- Thứ tự 16 cột dữ liệu trong `_appendix1_rows` (app.py:2520-2540): TT, tên,
  số đăng ký, cấp PT, công dụng, ngày hết hạn GCN, `capacity`, sức chở khách,
  vị trí đến, thời gian đến, vị trí rời, thời gian rời, hàng dỡ, hàng xếp,
  "crew/pax", thuyền trưởng — **khớp thứ tự** với 16 cột template.
- Khác biệt cần xác nhận: template tách cột 7 = "Lượng hàng (tấn/ teu)" thuần
  số, còn code gộp `capacity` thành 1 chuỗi text dạng
  `"<capacity_tons> tấn / <capacity_teu:g> TEU"` (app.py:2510-2517) — chuỗi
  ghép chữ thay vì giá trị số/tách cột. Có thể chấp nhận được nếu chủ ý hiển
  thị gộp, nhưng lệch với ý đồ "1 cột = 1 đơn vị" của mẫu gốc.
- Tiêu đề cột 6 code ghi "Ngày hết hạn GCNATKT & BVMT" — mẫu gốc ghi
  "Ngày / hết hạn GCNATKT&BVMT" (docx tách dòng bằng "/"); chỉ khác cách trình
  bày, không phải khác cột.

### Phụ lục 2 — `_make_appendix2_xlsx` + `_appendix2_rows`

- Số cột: template 16, code 16 (`A1:P1`/`P3` merges). **Khớp.**
- Thứ tự 14 cột số liệu trong `_appendix2_rows` (app.py:2574-2582):
  `container_tons(TH), container_teu(TH), container_tons(LK), container_teu(LK),
  dry_tons(TH), dry_tons(LK), liquid_tons(TH), liquid_tons(LK),
  foreign_tons(TH), foreign_tons(LK), calls(TH), calls(LK),
  passenger_calls(TH), passengers(TH)` — so với 14 cột template (cột 3-16):
  Container Tấn/TEU (TH), Container Tấn/TEU (LK), Hàng khô TH/LK, Hàng lỏng
  TH/LK, Hàng XNK TH/LK, Lượt tàu TH/LK, Lượt tàu khách, Lượt khách.
  **Khớp thứ tự và nhóm 1:1.**
- Không phát hiện lệch cột ở phụ lục này.

### Phụ lục 3 — `_make_appendix3_xlsx` + `_appendix3_rows`

- Cách dựng khác hẳn PL1/PL2: `_make_appendix3_xlsx` **load chính file mẫu**
  `templates/Phụ lục 3.xlsx` bằng `openpyxl.load_workbook` rồi chèn/xóa dòng dữ
  liệu tại vị trí hàng 10 trở đi, giữ nguyên toàn bộ header/merge/style gốc.
  Đây là cách ít rủi ro lệch cấu trúc nhất trong 3 phụ lục vì không viết lại
  header thủ công.
- Rủi ro duy nhất nằm ở **mapping dữ liệu vào đúng cột nhóm hàng hóa**, xử lý ở
  `_cargo_column_start` (app.py:2590-2606), trả về cột bắt đầu (0-indexed) theo
  `movement_type` sau khi chuẩn hóa qua `import_match_key`:

  ```
  XUATKHAU     → 8   (đúng, cột 9 1-indexed = Xuất khẩu)
  NHAPKHAU     → 11  (đúng, cột 12 1-indexed = Nhập khẩu)
  NOIDIADEN    → 14  (đúng, cột 15 1-indexed = Nội địa đến)
  NOIDIAROI    → 17  (đúng, cột 18 1-indexed = Nội địa rời)
  CHUYENTAI    → 20  (đúng, cột 21 1-indexed = Chuyển tải)
  QUACANH + (BOCDO hoặc XEPDO) → 22  (đúng, cột 23 1-indexed = Quá cảnh bốc dỡ)
  QUACANH hoặc QUACANG (else)  → 24  (đúng, cột 25 1-indexed = Quá cảng không bốc dỡ)
  default (không khớp gì)      → 14  (mặc định rơi vào "Nội địa đến" — có thể
                                       che giấu dữ liệu sai nếu movement_type
                                       thực tế không khớp bất kỳ pattern nào)
  ```

  `empty_teu` (cột "Teus Rỗng"/"Tues Rỗng") chỉ được ghi khi
  `cargo_start in {8, 11, 14, 17}` (app.py:2632) — đúng vì chỉ 4 nhóm đầu
  (Xuất khẩu, Nhập khẩu, Nội địa đến, Nội địa rời) có cột con thứ 3 trong mẫu;
  3 nhóm còn lại (Chuyển tải, Quá cảnh bốc dỡ, Quá cảng không bốc dỡ) chỉ có
  2 cột con (Tấn + Teus/Tues), khớp với code không ghi `empty_teu` cho các
  nhóm này.

## Kết luận tổng hợp

| Phụ lục | Số cột | Thứ tự header | Thứ tự dữ liệu | Ghi chú |
|---|---|---|---|---|
| PL1 | 16/16 khớp | Khớp | Khớp | Cột "Lượng hàng" bị gộp thành chuỗi text tấn+TEU thay vì giữ nguyên dạng số như mẫu |
| PL2 | 16/16 khớp | Khớp | Khớp | Không phát hiện lệch |
| PL3 | 35/35 khớp (dùng lại chính template) | Khớp (không viết lại) | Khớp theo `_cargo_column_start`, đã đối chiếu từng nhánh | Nhánh `default → 14` của `_cargo_column_start` là fallback im lặng, nên xác nhận có luôn khớp với dữ liệu `movement_type` thực tế hay không |

## Chưa kiểm chứng (giới hạn của lượt audit này)

Lượt kiểm tra này **chỉ đối chiếu tĩnh** (đọc mã nguồn + đọc file mẫu), **chưa**:

1. Chạy thử `GET /api/reports/appendix{1,2,3}` với dữ liệu thật/dữ liệu mẫu rồi
   mở file .xlsx sinh ra để so từng ô bằng mắt hoặc bằng script diff tự động.
2. Kiểm tra `import_match_key` chuẩn hóa các giá trị `movement_type`/`cargo_type`
   thực tế đang lưu trong DB có luôn khớp đúng 1 trong các nhánh
   `_cargo_column_start` hay bị rơi vào nhánh mặc định (return 14) một cách
   không mong muốn.
3. Kiểm tra style/merge cells sau khi `_make_appendix3_xlsx` xóa/chèn dòng có
   thực sự giữ đúng format của mẫu gốc khi số dòng dữ liệu khác 5 (trường hợp
   `desired_rows > 5` dùng `insert_rows`, cần xác nhận style của dòng mới có
   copy đúng từ `source_row = 10`).

Nên chạy thử export thực tế và so sánh file kết quả với 3 file mẫu gốc trước
khi kết luận "đã chuẩn 100%".
