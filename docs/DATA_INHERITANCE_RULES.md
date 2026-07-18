# Canonical Data Inheritance Rules

1. Match vessels by `vessel_id`; use normalized registration only as a controlled legacy fallback.
2. A blank imported or form value cannot erase a validated canonical value.
3. Draft declarations may prefill current vessel/crew facts.
4. Approval freezes activity facts, `departure_berth`, `agent_ptnd_name` and `is_passenger_call` as the event snapshot.
5. Static appendix columns read current vessel master facts where the mapping permits; activity columns never read static capacity as production.
6. ATA overrides ETA; ATD overrides ETD. `declaration_date` is never an operating-date fallback for official reports.
7. Destination port cannot populate departure berth.
8. Unknown cargo/movement classification is rejected from official aggregation and surfaced for review; it cannot silently enter a default category.
9. All reads and writes retain tenant scope and role checks.
10. PL.01 and PL.03 start from canonical master rows. Absence of an approved
    declaration leaves activity blank; it does not remove the Salan row.

## PL.03 deterministic aggregation

- Grain: one row per `vessel_id`; legacy rows group by normalized registration.
- Order contributing declarations by operating arrival, then declaration id.
- Additive fields (tons, TEUs, empty TEUs, passenger counts) are summed by approved category/direction.
- Non-additive fields (cargo names, ports, dates, Đại lý PTND) keep distinct nonblank values in chronological order, joined with a line break in the same cell.
- Static vessel fields come from the current canonical vessel record.
- No declaration/cargo item may create a second row for the same canonical vessel.

## PL.02 manual adjustment

- Append-only record: tenant, report month, metric, signed delta, reason, actor and timestamp.
- Only PORT_STAFF or ADMIN may create an adjustment.
- The exporter shows base approved-event totals plus the sum of authorized deltas.
- Adjustments do not mutate declarations and are visible through an audit endpoint.
