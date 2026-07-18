# Canonical Data Index

| Entity/projection | Authoritative source | Key | Main consumers |
|---|---|---|---|
| Organization | operational DB | `organization_id` | tenant boundary, headers |
| Vessel | operational DB/import | `vessel_id`, normalized registration | Hồ sơ, Salan register, static appendix columns |
| Declaration / Port call | customer form/import + workflow | `declaration_id` | review, dashboard, all appendices |
| Cargo snapshot | declaration load/unload facts | declaration + direction | PL.01, PL.02, PL.03, dashboard |
| Crew snapshot | declaration crew links | declaration + crew | PL.01 and review |
| Report adjustment | authorized staff entry | month + metric + audit id | PL.02 only |
| Official appendix projection | derived, never persisted as truth | appendix + period | Cảng vụ submission |
| Analytical projection | derived | period + tenant | internal dashboard |

Read path: source/import → validation → canonical entity → approved snapshot → tenant/role projection → dashboard or official exporter.
