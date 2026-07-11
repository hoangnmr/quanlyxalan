# Report Golden Dataset — KBCV 1.0

This synthetic dataset verifies the approved mapping without customer data.

- Workflow: APPROVED.
- ETA/ETD: 08:00 / 18:00.
- ATA/ATD: 09:15 / 19:30.
- Unload: Hàng A, Nhập khẩu, 12 tons, two 20-foot full containers = 2 TEU.
- Load: Hàng B, Xuất khẩu, 20 tons, one 40-foot full container = 2 TEU.

Expected output:

- Appendix 1 uses ATA/ATD instead of ETA/ETD.
- Appendix 3 emits separate unload and load rows.
- Detail totals are `12.0 tấn / 2.0 TEU` and `20.0 tấn / 2.0 TEU`.
- Draft, pending, change-requested and revoked records remain excluded.

Automated evidence:
`test_approved_report_golden_mapping_uses_actual_times_and_cargo_rows`.
