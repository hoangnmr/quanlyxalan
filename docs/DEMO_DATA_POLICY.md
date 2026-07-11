# Demo Data Policy

Local demonstration records are seeded only by `scripts/seed_demo_data.py` and
are owned by the sentinel organization tax code `DEMO-TANTHUAN-2026`.

- The seed script refuses to run if operational vessel, declaration or crew
  records already exist.
- The UI labels the dataset as **Dữ liệu minh họa**.
- On the first new vessel creation or vessel Excel import, the application
  removes only this sentinel dataset in the same database transaction. It does
  not delete any other organization or records.
- Demonstration records must never be exported as legal/production evidence.

Run locally after migration:

```powershell
python scripts/seed_demo_data.py
```
