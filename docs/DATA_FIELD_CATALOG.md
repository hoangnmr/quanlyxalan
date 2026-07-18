# Canonical Field Catalog — Appendix tranche

| Field | Type | Owner | Rule | Consumers |
|---|---|---|---|---|
| `declaration_date` | ISO date | Declaration | creation metadata; never period membership | UI/audit |
| `eta`, `etd` | ISO datetime | Declaration | estimates | UI; fallback only |
| `actual_arrival_at`, `actual_departure_at` | nullable ISO datetime | Declaration | actual values; arrival/departure precedence | dashboard, PL.01–03 |
| `working_port` | text | Declaration snapshot | arrival/cargo-working position | PL.01/I, PL.03/AE |
| `departure_berth` | text | Declaration snapshot | departure position; never destination fallback | PL.01/K |
| `destination_port` | text | Declaration snapshot | next destination | PL.03/AF |
| `agent_ptnd_name` | text | Declaration snapshot | customer-declared Đại lý PTND | PL.03/AI |
| `is_passenger_call` | boolean | Declaration snapshot | explicit passenger call classification | PL.02/O |
| `passenger_capacity` | nullable integer | Vessel | design capacity; blank when unknown | PL.01/H |
| `passenger_count` | nullable/recorded integer | Declaration snapshot | actual passengers | PL.01/O, PL.02/P, PL.03/AA:AB |
| `crew_count` | nullable/recorded integer | Declaration snapshot | actual crew | PL.01/O |
| cargo tons/TEUs/empty TEUs | numeric snapshot | Declaration cargo | sum only after valid classification | PL.01–03/dashboard |
| `workflow_status` | enum | Declaration workflow | only `APPROVED` is eligible | all official reports |

Missing is distinct from measured zero. Export cells stay blank when no eligible fact exists; a recorded zero remains numeric zero only where the source explicitly represents a measured/applicable fact.
