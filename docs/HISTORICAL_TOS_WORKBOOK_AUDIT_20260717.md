# Historical TOS and PL.03 Workbook Audit

Status: **AUDIT COMPLETED — OWNER TIME DECISION RECORDED; H0 NOT CLOSED**

Audit execution date: 2026-07-18

Requested artifact date: 2026-07-17

Project: `Khai-bao-Cang-vu-recovery-ux`

Phase: INTAKE

Risk: R2 read-only workbook audit

## 1. Executive summary

Five supplied workbooks, six worksheets and every used-range row/column were
inspected read-only with the bundled Spreadsheets runtime and
`@oai/artifact-tool`. Thirteen local PNG renders collectively cover 100% of the
used ranges; the 1,068-row cargo sheet was split into eight contiguous vertical
render bands because a single 2,273 × 20,638 bitmap exceeded the renderer's
allocation limit. Formula discovery and formula-error scans found **no formulas
and no formula errors** in any workbook.

The TOS source contract is structurally clear:

- `Berth XL 07.2026.xlsx` has 40 call rows. `E=Ten tau`, `H=Ma ben`,
  `T=ATB`, and `W=ATD` are confirmed by the actual row-1 headers. `B=Nam` and
  `C=Chuyen` are independent join components. Each row contains the full call;
  there are no separate arrival/departure rows.
- `CHI TIET XL THANG 07.2026.xlsx` has 1,067 cargo rows. The actual columns are
  `C=Kich co`, `E=F/E`, `Q=Ten sa lan | Nam | Chuyen`, `R=Trong luong`,
  `T=Hang noi/ ngoai`, and `W=Phuong an`. All six fields are stored as text.
- All 1,067 cargo rows and all 38 distinct cargo call keys exact-match one
  Berth key. Berth has 40 distinct keys, so two Berth calls have no cargo row.
  There are no duplicate Berth keys, no ambiguous cargo joins and no unmatched
  cargo rows in this sample.
- The standalone Salan register has 59 business rows. Of 40 Berth rows, 10
  match the register name exactly, 26 match only after controlled
  case/space/accent/punctuation normalization, four remain unmatched, and none
  are ambiguous in this sample.
- Both PL.03 workbooks use 35 physical columns `A:AI`, identical header-cell
  content for rows 5–9, identical 48 header merges and the same physical column
  order. They are **not interchangeable presentation versions**: the filled
  workbook has 73 report rows, different widths, hidden `AA:AB`, a hidden
  `DU LIEU` sheet and dynamic footer rows 84–85; the template has five empty
  reserved rows, visible `AA:AB` and footer rows 15–16.
- `PL.03/B=Ten PTTND`, `AG=Ngay den cang`, `AH=Ngay roi cang`, and
  `AI=Dai ly PTND` are confirmed from the real merged header. All 73 filled
  PL.03 rows have text arrival values, 64 have text departure values, and all
  73 have blank `AI`; an agent value cannot be inferred from these sources.

The strongest blocker is reconciliation. Of 40 Berth rows, 33 have at least
one normalized PL.03 name candidate, but only one has a unique arrival match at
minute precision and none matches both arrival and departure minutes. Eighteen
rows remain ambiguous among repeated PL.03 names. Only the one unique
arrival-matched call could be used for a cargo-cell comparison: three of four
comparable cells matched and one differed. Therefore the audit confirms exact
column positions and a safe candidate parser contract, but it does **not**
prove that the supplied filled PL.03 was derived directly from Berth ATB/ATD or
that TOS can reproduce the official PL.03 without an owner-approved
reconciliation rule.

H0 remains open under the historical roadmap because representative historical
PL.01 and PL.02 workbooks were not supplied, HDEC-01–HDEC-09 are not all
closed, the TOS weight unit is not stated in its header, and the time mismatch
above is unresolved. No code, schema, migration, database, API, UI or source
workbook was changed.

## 2. Workbook, sheet and checksum inventory

| Workbook | Size (bytes) | SHA-256 | Sheet | State | Used range | Data rows |
|---|---:|---|---|---|---|---:|
| `Berth XL 07.2026.xlsx` | 16,607 | `C116C62F859EA4C22BAC50C54761790B22F81E2135D1F634CDE676CCF5C920B7` | `Sheet1` | visible | `A1:Z41` | 40 |
| `CHI TIET XL THANG 07.2026.xlsx` | 145,730 | `98DE9781C661C614F5ED34D156E041B2FC2DE1D84339EDC92B5D91CD0F8087E3` | `Sheet1` | visible | `A1:AE1068` | 1,067 |
| `BC THANG 7.26 -PL3.xlsx` | 35,164 | `73E08450ACB4847F6B8A9D6882205AF43631BED843CED11D9A8BD6EEBF51032B` | `BAO CAO` | visible | `A1:AI85` | 73 report rows |
| same | same | same | `DU LIEU` | hidden | `A1:N65` | 59 business rows |
| `DU_LIEU_SA_LAN_T7.26.xlsx` | 20,001 | `75D91E2EA3DD3E3382AE57C320B2DC159952F786890E2D8777977B120A0BE71C` | `Sheet2` | visible | `A1:N65` | 59 business rows |
| `Phụ lục 3.xlsx` | 13,468 | `95DDAF05A1B08E4981C3EF465B7379BAC7EC91BE84B36068DE8E569D71333A22` | `Sheet` | visible | `A1:AI16` | 5 blank reserved rows |

The hidden `DU LIEU` value matrix and the standalone Salan matrix differ in one
non-business ordinal cell only: `A60` is 59 in the embedded copy and 60 in the
standalone copy. The other 909 compared cells are equal after artifact import.
The two files still have separate checksums and must retain separate source
provenance/version receipts.

## 3. Header and used-range audit

### 3.1 Berth XL 07.2026

| Property | Result |
|---|---|
| Sheet / used range | `Sheet1`, `A1:Z41` |
| Header / data | row 1; rows 2–41 |
| Merged cells | none |
| Hidden rows / columns / sheets | none |
| Formulas / formula errors | 0 / 0 |
| Source types | all populated cells are shared-string text with General format |
| Date/time fields | `T=ATB` and `W=ATD` are text, not Excel datetime or numeric serial |
| Missing ATB / ATD | one blank ATB and one blank ATD among 40 rows |
| Entirely blank data columns | `L=ICD CT`, `Q=ETC`, `Z=Ghi chu`; no explicit non-default blank-cell styles |

Confirmed headers include `B=Nam`, `C=Chuyen`, `E=Ten tau`,
`F=Im-Voy. NO.`, `G=Out-Voy. NO.`, `H=Ma ben`, `S=ATA`, `T=ATB`,
and `W=ATD`. ATB remains a distinct field from ATA. All 40 normalized
`name + year + voyage` keys are unique. No key appears at multiple berth codes
in this sample.

The artifact render shows dense date columns `N:W` with visible clipping or
overflow at the source widths. This is a source-presentation issue only; the
underlying text values were inspected directly and are not truncated in the
audit data.

### 3.2 CHI TIET XL THANG 07.2026

| Property | Result |
|---|---|
| Sheet / used range | `Sheet1`, `A1:AE1068` |
| Header / data | row 1; rows 2–1068 |
| Merged cells | none |
| Hidden columns | `H:P` (`Chuyen nhap` through `FPOD`) |
| Hidden rows | 634, 834 and 1026; each contains 24 nonblank cells and must be parsed |
| Formulas / formula errors | 0 / 0 |
| Source types | every populated cell is shared-string text with General format |
| Key fields | `C`, `E`, `Q`, `R`, `T`, `W` are all text; none is blank, numeric zero or an Excel error |
| Entirely blank data columns | `L`, `M`, `N`, `AA`, `AD`, `AE` |

The actual key header is one physical column:
`Q=Ten sa lan | Nam | Chuyen`. It must be split on exactly two pipe
delimiters into three raw components. The parser must keep the complete raw
cell and each component. Columns `R` and `S` are respectively
`Trong luong` and `SealNo`; merged-header drift is not present.

The weight cells are text, although all 1,067 values in this sample are strict
decimal tokens. Their aggregate is 7,894.83 in the source's unstated unit.
There are no blanks, zeroes or invalid numeric tokens in this sample. The
header does not say `tan`; mapping these values to PL.03 `Tan` remains an owner
decision.

### 3.3 BC THANG 7.26 -PL3

| Property | `BAO CAO` | `DU LIEU` |
|---|---|---|
| State / used range | visible, `A1:AI85` | hidden, `A1:N65` |
| Header / data | merged header rows 5–9; report rows 10–82; footer 84–85 | header row 1; business rows 2–60; formatted blanks 61–65 |
| Merged cells | 52 total; 48 in rows 1–9 | none |
| Hidden rows / columns | columns `AA:AB` hidden; no hidden rows | none inside the hidden sheet |
| Formulas / formula errors | 0 / 0 | 0 / 0 |

The 73 report rows have the following populated-column profile:

- `A:G`: 73 nonblank; `H`: 67 nonblank;
- cargo measures: `L=6`, `O=20`, `P=17`, `R=15`, `S=15`, `U=3`;
- `AG=73`, `AH=64`;
- `I,J,K,M,N,Q,T,V:AF,AI` are blank for all 73 rows but retain report
  formatting where cells are instantiated.

Reported `AG` and `AH` values are shared-string text in the observed
`dd/MM/yyyy - HH:mm` shape, not native Excel datetimes. Some cells carry a
built-in date style, but the cell payload remains text. `AI` is a formatted
blank report column and is not the vessel-name source.

### 3.4 DU_LIEU_SA_LAN_T7.26

| Property | Result |
|---|---|
| Sheet / used range | `Sheet2`, `A1:N65` |
| Header / data | row 1; rows 2–60; formatted blanks 61–65 |
| Merged / hidden / formulas | no merges, no hidden rows/columns/sheets, no formulas |
| Identity | `B=TEN PHUONG TIEN`, `C=SO DANG KY` |
| Relevant static facts | `D:H` map to type, class, length, deadweight and capacity |
| Mixed types | numeric/static columns mix native numbers and text; certificate-date column `K` contains 57 text dates, one numeric date serial and one business-row blank |

Name normalization was evaluated in tiers while retaining raw source values:

1. trim and collapse whitespace;
2. Unicode NFKC plus uppercase;
3. Vietnamese accent removal, `D`/`Đ` folding and punctuation/hyphen removal.

The broad tier must only produce candidates. It must never auto-select when
there are zero or multiple registration candidates.

### 3.5 Phụ lục 3.xlsx

The template uses `A1:AI16`, merged header rows 5–9, five reserved data rows
10–14 and footer rows 15–16. It has 52 merges, including the same 48 header
merges as the filled workbook. All reserved cells `B10:AI14` are blank but
formatted. No column or sheet is hidden.

## 4. Exact source-to-target mapping

The machine-readable contract is
`docs/historical_tos_mapping_draft.json`. It enumerates source letter, one-based
index, actual header, target fact/field, appendix column, transform,
blank/zero rule, confidence and unresolved decision without embedding any real
vessel, registration, contact or cargo row.

| Source workbook | Sheet | Header row | Source column/cell | Source header | Data type | Target fact | Target appendix/column | Transform | Blank/zero rule | Confidence |
|---|---|---:|---|---|---|---|---|---|---|---|
| Berth | Sheet1 | 1 | B | Nam | text | call year | join key | trim; validate year; retain raw | blank invalid; not zero | High |
| Berth | Sheet1 | 1 | C | Chuyen | text | voyage | join key | retain leading zeroes; separate numeric-normalized candidate | blank invalid | High |
| Berth | Sheet1 | 1 | E | Ten tau | text | vessel identity | PL.03/B candidate | raw + controlled normalization | blank invalid; ambiguity blocks | High |
| Berth | Sheet1 | 1 | H | Ma ben | text | initial arrival/departure berth | PL.01/I,K | copy to both initial fields with provenance | preserve blank | High |
| Berth | Sheet1 | 1 | T | ATB | text datetime | actual berthing time | PL.01/J; PL.03/AG | strict `dd/MM/yyyy HH:mm:ss`; keep ATB label/raw | preserve blank; no ATA rename | High position / unresolved reconciliation |
| Berth | Sheet1 | 1 | W | ATD | text datetime | actual departure | PL.01/L; PL.03/AH | strict parse; retain raw | preserve blank | High position / unresolved reconciliation |
| Detail | Sheet1 | 1 | C | Kich co | text code | size and TEU factor | PL.02/PL.03 TEU metrics | prefix 20=1; 40=2; other=review | unknown is missing, not 0 | High |
| Detail | Sheet1 | 1 | E | F/E | text enum | fullness | full/empty metric choice | accept explicit F/E only | blank unresolved | High |
| Detail | Sheet1 | 1 | Q | Ten sa lan \| Nam \| Chuyen | text composite | name/year/voyage | join key | exactly three trimmed components; retain raw | malformed rejects join | High |
| Detail | Sheet1 | 1 | R | Trong luong | numeric-looking text | cargo weight | PL.02/PL.03 tons candidate | strict decimal parse; unit separate | blank/0/invalid distinct | Medium; unit open |
| Detail | Sheet1 | 1 | T | Hang noi/ ngoai | text enum | trade scope | PL.03 category family | map approved dictionary only | blank unresolved | High |
| Detail | Sheet1 | 1 | W | Phuong an | text enum | movement direction candidate | load/unload family | candidate map documented below | unknown excluded | Medium; owner approval open |
| Salan | Sheet2 | 1 | B | TEN PHUONG TIEN | text | vessel link candidate | PL.03/B | exact then controlled normalized lookup | ambiguity blocks | High |
| Salan | Sheet2 | 1 | C | SO DANG KY | text | registration | PL.03/C | retain raw; normalize only for lookup | preserve blank | High |
| Salan | Sheet2 | 1 | D:H | type/class/length/deadweight/capacity | mixed | historical static facts | PL.03/D:H | preserve raw/profile multiplicity; no live overwrite | blank/0 distinct | High |
| Filled/template PL.03 | BAO CAO/Sheet | 5–9 | A:H | direct and merged headers | mixed | reported row/static facts | PL.03/A:H | map by physical column plus template version | preserve blanks/zeroes | High |
| same | same | 5–9 | I:Z | hierarchical cargo headers | mixed | reported cargo metrics | PL.03/I:Z | per-column dictionary below; preserve historical spelling | blank is missing; 0 measured | High |
| same | same | 5–9 | AA:AB | passenger arrivals/departures | mixed | reported passenger metrics | PL.03/AA:AB | parse even when columns hidden | blank/0 distinct | High |
| same | same | 5–9 | AC:AF | cargo/port text | text | reported descriptors | PL.03/AC:AF | retain exactly as reported | preserve blank | High |
| same | same | 5–9 | AG | Ngay den cang | text datetime | reported arrival | PL.03/AG | parse observed text; retain raw | preserve blank | High direct / ATB equivalence open |
| same | same | 5–9 | AH | Ngay roi cang | text datetime | reported departure | PL.03/AH | parse observed text; retain raw | preserve blank | High direct / ATD equivalence open |
| same | same | 5–9 | AI | Dai ly PTND | text/blank | reported agent | PL.03/AI | never infer from vessel/company | preserve blank | High |

### PL.03 physical cargo-column dictionary

| Column | Observed hierarchical header | Canonical fact code |
|---|---|---|
| I | Hang hoa > Xuat khau > Tan | `export_tons_reported` |
| J | Hang hoa > Xuat khau > Teus | `export_full_teu_reported` |
| K | Hang hoa > Xuat khau > Teus Rong | `export_empty_teu_reported` |
| L | Hang hoa > Nhap khau > Tan | `import_tons_reported` |
| M | Hang hoa > Nhap khau > Teus | `import_full_teu_reported` |
| N | Hang hoa > Nhap khau > Teus Rong | `import_empty_teu_reported` |
| O | Hang hoa > Noi dia den > Tan | `domestic_inbound_tons_reported` |
| P | Hang hoa > Noi dia den > Teus | `domestic_inbound_full_teu_reported` |
| Q | Hang hoa > Noi dia den > Tues Rong | `domestic_inbound_empty_teu_reported` |
| R | Hang hoa > Noi dia roi > Tan | `domestic_outbound_tons_reported` |
| S | Hang hoa > Noi dia roi > Teus | `domestic_outbound_full_teu_reported` |
| T | Hang hoa > Noi dia roi > Tues Rong | `domestic_outbound_empty_teu_reported` |
| U | Hang hoa > Chuyen tai > Tan | `transshipment_tons_reported` |
| V | Hang hoa > Chuyen tai > Tues | `transshipment_teu_reported` |
| W | Hang hoa > Qua canh (boc do) > Tan | `transit_handled_tons_reported` |
| X | Hang hoa > Qua canh (boc do) > Tues | `transit_handled_teu_reported` |
| Y | Hang hoa > Qua cang (khong boc do) > Tan | `transit_not_handled_tons_reported` |
| Z | Hang hoa > Qua cang (khong boc do) > Teus | `transit_not_handled_teu_reported` |

The spellings above are the exact historical workbook labels, including
`Teus`, `Tues`, `Tues Rong` and `Qua cang`. Canonical metric codes may use the
approved `TEUs`, `TEUs Rong` and `Qua canh`, but raw headers and detected
template version must remain in provenance.

## 5. Join-key analysis and match coverage

### Berth to cargo detail

Candidate exact key:

`trim(Berth!E) + trim(Berth!B) + trim(Berth!C)`

against the three trimmed components of `Detail!Q`.

Controlled normalized key:

- Unicode NFKC, uppercase and whitespace collapse for names;
- a broader accent/punctuation-folded name only for candidate lookup;
- four-digit year validation;
- voyage raw retained, with a separate leading-zero-insensitive comparison
  component.

| Measure | Result |
|---|---:|
| Berth rows / normalized call keys | 40 / 40 |
| Detail rows / normalized call keys | 1,067 / 38 |
| Exact detail-row matches | 1,067 (100%) |
| Normalized-only detail-row matches | 0 |
| Unmatched / ambiguous / malformed detail rows | 0 / 0 / 0 |
| Exact distinct detail-call matches | 38 (100%) |
| Berth calls without cargo detail | 2 |
| Cargo rows per call | min 4; max 100; average 28.08 |
| Duplicate Berth key / duplicate key across multiple berths | 0 / 0 |

Cardinality in this sample is one Berth call to many cargo rows. No cargo row
maps to multiple Berth rows. A production parser must still fail closed if a
future normalized key maps to multiple Berth rows; it must not select the first
candidate.

### Berth to Salan register

| Match class | Berth rows |
|---|---:|
| Exact name | 10 |
| Controlled normalized name only | 26 |
| Unmatched | 4 |
| Ambiguous | 0 |
| Normalized register names with multiple registrations | 0 |

All raw names and registrations must remain attached to their source cells.
The broad normalization is evidence for a manual link candidate, not authority
to overwrite a canonical Salan record.

## 6. Distinct-value dictionary

### Container size (`Detail!C`)

| Raw code | Rows | TEU treatment |
|---|---:|---|
| `40HC` | 669 | 2 |
| `20GP` | 203 | 1 |
| `40RH` | 120 | 2 |
| `40GP` | 59 | 2 |
| `40DC` | 8 | 2 |
| `20DC` | 7 | 1 |
| `20RH` | 1 | 1 |

No 45-foot or unknown-prefix value occurs in this sample. The parser must not
generalize beyond approved 20- and 40-foot prefixes; every other prefix enters
review.

### Full/empty (`Detail!E`)

| Raw value | Rows |
|---|---:|
| `E` | 761 |
| `F` | 306 |

F/E remains independent from `Phuong an`.

### Domestic/foreign (`Detail!T`)

| Raw value | Rows |
|---|---:|
| `Hang noi` | 1,067 |

No foreign variant is present, so foreign/import/export mapping needs a golden
fixture or another real sample before acceptance.

### Movement method (`Detail!W`)

| Raw value | Rows | Candidate direction |
|---|---:|---|
| `Ha bai` | 640 | unload |
| `Lay Nguyen` | 296 | load |
| `Tra rong` | 123 | unload |
| `Cap rong` | 8 | load |

These direction rules are owner-supplied baseline candidates. They are not a
replacement for F/E or domestic/foreign classification.

## 7. PL.03 template-version comparison

| Property | Filled July report | Blank template | Conclusion |
|---|---|---|---|
| Physical columns | 35 (`A:AI`) | 35 (`A:AI`) | equal |
| Header cells rows 5–9 | identical | identical | equal historical header schema |
| Header merges | 48 | 48 | equal |
| Total merges | 52 | 52 | equal; footer merges move with footer |
| Used range | `A1:AI85` | `A1:AI16` | dynamic report length |
| Business rows | 73 | 0; five placeholders | different role |
| Footer | rows 84–85 | rows 15–16 | dynamic position required |
| Passenger columns | `AA:AB` hidden | visible | presentation-version difference |
| Embedded register | hidden `DU LIEU` | absent | source/version difference |
| Column widths | report-specific, including wider vessel name | narrower template defaults | do not identify version by column count alone |
| Header spelling | `Teus`, `Tues`, `Qua cang` variants | same | historical variant conflicts with approved corrected labels |

Recommended detected versions:

- `pl03_historical_35col_filled_2026_07_v1` for the supplied filled report;
- `pl03_historical_35col_blank_v1` for the supplied blank template.

Version detection must use checksum plus header matrix, merge set, hidden-column
state and presence/absence of the hidden register sheet. It must not assume
that every 35-column workbook is the same version.

## 8. Reconciliation totals

The following are source-derived aggregate facts only. Weight is shown in the
source's unstated unit and must not be labelled `tan` until confirmed.

| Direction | F/E | Trade | Cargo rows | TEU | Weight | Blank weight | Zero weight | Invalid weight |
|---|---|---|---:|---:|---:|---:|---:|---:|
| load | E | domestic | 79 | 149 | 351.40 | 0 | 0 | 0 |
| load | F | domestic | 225 | 443 | 2,984.37 | 0 | 0 | 0 |
| unload | E | domestic | 682 | 1,189 | 2,415.78 | 0 | 0 | 0 |
| unload | F | domestic | 81 | 142 | 2,143.28 | 0 | 0 | 0 |
| **Total** |  |  | **1,067** | **1,923** | **7,894.83** | **0** | **0** | **0** |

Other reconciliation counts:

- Berth call rows: 40;
- detail call keys with cargo: 38;
- successfully joined detail call keys: 38;
- unmatched/ambiguous detail calls: 0/0;
- filled PL.03 report rows: 73;
- Berth-to-PL.03 classification: seven with no normalized name candidate,
  fourteen with one name candidate but no arrival-minute match, one unique
  arrival-minute match, and eighteen ambiguous among repeated names;
- no Berth row matches both PL.03 arrival and departure minutes;
- the one uniquely arrival-matched call has four comparable candidate cargo
  cells: three exact and one different.

The PL.03 row count and time evidence show a scope or derivation difference;
global TOS totals must not be compared directly to all 73 PL.03 rows as if both
sources covered an identical call population.

### Appendix fillability from supplied sources

| Classification | Columns/facts |
|---|---|
| Can fill with high positional confidence | PL.01/I and K initial berth from Berth/H; PL.01/J from ATB; PL.01/L from ATD; PL.03/B from Berth name; PL.03/C:H after an unambiguous register link; direct import of every reported PL.03/A:AI cell as a historical fact |
| Can fill only after confirmation/reconciliation | PL.02/PL.03 tonnage because TOS weight unit is unstated; PL.02/PL.03 category measures from movement/trade/F-E rules; PL.03/AG:AH reconstructed from Berth because supplied historical values do not reconcile; registration/static facts for four unmatched Berth rows |
| Absent from TOS and must remain blank | PL.03/AI agent; PL.03/AC cargo-name summary if not explicitly derived by an approved rule; PL.03/AD:AF port descriptors not present in the audited key columns; passenger values; any authority/signature facts; separate departure berth when it differs from the single Berth/H code |

Missing values must never become numeric zero.

## 9. Data-quality findings

1. **Major — time reconciliation:** the historical PL.03 times do not support a
   direct `ATB -> AG` and `ATD -> AH` reconstruction claim for this sample.
2. **Major — historical template labels:** both PL.03 files contain mixed
   `Teus`/`Tues`, `Tues Rong` and `Qua cang` spellings, while the approved
   canonical labels are `TEUs`, `TEUs Rong` and `Qua canh`.
3. **Major — unstated weight unit:** `Detail!R` is numeric-looking text under
   `Trong luong`, with no unit in the header.
4. **Major — hidden data:** detail columns `H:P` and rows 634, 834 and 1026
   contain data. A visible-row-only or visible-column-only parser would lose
   records or join context.
5. **Major — incomplete vessel linkage:** four of 40 Berth rows do not match the
   supplied register after controlled normalization.
6. **Major — agent unavailable:** all 73 filled PL.03 `AI` cells are blank; no
   source supports agent inference.
7. **Moderate — presentation variants:** the filled PL.03 hides `AA:AB`, widens
   columns and shifts the footer; a fixed-row or visible-column parser will
   fail.
8. **Moderate — register-copy ordinal drift:** the embedded and standalone
   register copies differ at `A60` while the remaining compared cells match.
9. **Moderate — mixed date storage:** Berth/detail/PL.03 operational dates are
   text; the Salan certificate column mixes text and one numeric date serial.
10. **Moderate — source visual clipping:** dense Berth dates and long detail
    notes overflow or clip at source widths. Values remain extractable, but a
    screenshot is not sufficient extraction evidence.
11. **Coverage gap:** this sample contains only domestic cargo and 20/40-foot
    size prefixes; it does not prove foreign, 45-foot or invalid-size handling.

## 10. Owner-confirmed baseline decisions

- Berth vessel name links to the Salan register, with raw identity preserved.
- PL.03 vessel name is column B (`Ten PTTND`); `AI` remains
  `Dai ly PTND`.
- A single Berth code initially populates both PL.01/I and PL.01/K, with
  provenance, until Port staff performs a controlled split correction.
- ATB is not ATA. For historical TOS, retain the source label ATB and map the
  confirmed report intent `ATB -> PL.01/J and PL.03/AG` only after the
  reconciliation exception is resolved; `ATD -> PL.01/L and PL.03/AH` follows
  the same evidence boundary.
- TOS history creates neither a Declaration nor an `APPROVED` state and does
  not overwrite vessel master or live data.
- 20-foot containers equal 1 TEU and 40-foot containers equal 2 TEU. Other
  sizes require review.
- `Tra rong`/`Ha bai` are candidate unload methods;
  `Lay Nguyen`/`Cap rong` are candidate load methods.
- F/E and domestic/foreign remain independent classification dimensions.
- Blank, numeric zero and invalid data are different states.

## 11. Decisions still required

| ID / issue | Required decision |
|---|---|
| HDEC-01 | Supply representative historical PL.01 and PL.02 variants when available; deferred and not a blocker to bounded TOS DESIGN |
| HDEC-06 | Confirm old PL.01 planned/actual semantics |
| HDEC-07 | Confirm PL.02 selected-month versus YTD storage/reconciliation for real historical files |
| TOS-PL03-LABEL-01 | Version the observed misspelled historical headers separately from the approved canonical template |

### 11.1 Owner disposition after audit — 2026-07-18

- `TOS-PL03-TIME-01` is **CLOSED**. The owner confirmed that the supplied
  filled PL.03 used inaccurate ETA-derived time and is not the authority for
  historical operating timestamps.
- TOS `ATB` is the authoritative arrival/berthing time for reconstructed
  historical PL.01/J and PL.03/AG; TOS `ATD` is authoritative for PL.01/L and
  PL.03/AH.
- Existing PL.03 AG/AH values remain immutable legacy reported facts with raw
  provenance. They do not overwrite TOS ATB/ATD and their mismatch is expected,
  not a parser failure.
- At audit completion, the 73-row PL.03 versus 40-row Berth scope difference
  remained open. It is dispositioned in section 11.2 without assuming row
  equivalence.

### 11.2 Owner disposition of remaining TOS baseline — 2026-07-18

- `TOS-WEIGHT-01` is **CLOSED**. Detail/R is tonnes per container. All weight,
  including empty-container shell weight such as `4.00`, contributes to report
  tonnes because the container shell is transported cargo. F/E independently
  selects full-versus-empty TEU columns.
- `TOS-METHOD-01` is **CLOSED**. `Trả rỗng`/`Hạ bãi` are unload;
  `Lấy nguyên`/`Cấp rỗng` are load. Size, F/E and domestic/foreign remain
  independent dimensions.
- `TOS-PL03-SCOPE-01` is **CLOSED AS A REPRODUCTION BLOCKER**. The supplied
  PL.03 is a manually prepared legacy summary whose scope/accuracy is not
  authoritative. Preserve it as reported provenance; do not require TOS code
  to reproduce its 73 rows.
- Reporting month is determined by ATB. Blank ATB enters review and does not
  silently fall back to filename, ATA or ATD.
- For matched live/TOS calls, TOS wins for actual time, berth and cargo; live
  retains declaration-only facts. Count the call once and review uncertain
  matches.
- New/updated overlapping TOS files require an explicit PORT_STAFF or
  explicit-context PLATFORM_ADMIN
  keep-existing or activate-new-revision choice. Never silently overwrite.
- Retain historical data, provenance and controlled source receipt at least
  five years; user-exported copies are an additional retention channel.

### 11.3 Owner multi-port disposition — 2026-07-18

- `HDEC-02` is **CLOSED**. The product is designed for multiple ports; Cảng Tân
  Thuận is the first tenant and must not be hardcoded as the only reporting
  unit.
- Government PL report contracts and canonical report facts are shared and
  versioned across ports. Port identity, official header details and source
  system configuration are tenant-scoped data/configuration, not separate
  report implementations.
- Every workbook, import job, staged row, accepted fact, revision, report and
  export belongs to exactly one tenant/reporting unit selected by the
  authenticated context. Ownership is never inferred from the filename.
- One import job cannot silently mix reporting units. Suspected mixed-unit
  content must be split into separate batches or held for explicit review.
- TOS layouts may differ by port or vendor. Detect them through versioned
  structural adapters while mapping into the same canonical reporting model.
- PORT_STAFF access remains tenant-local; PLATFORM_ADMIN must select an explicit
  port context. Any cross-port operation needs
  a separate, explicit platform-level authorization and tenant switch.

## 12. Proposed parser contract and golden fixtures

### Parser contract

1. Identify a workbook by checksum, sheet set, header matrix, merge set and
   hidden-state signature before reading rows.
2. Read hidden rows and hidden columns. Never base parsing on rendered
   visibility.
3. Preserve `source_file_checksum`, filename, size, sheet, source row, source
   cell, raw value, detected mapping version and blank/zero state for every
   mapped fact.
4. Parse Berth and detail rows independently, then join by exact raw components.
   Use controlled normalized keys only for candidate lookup. Multiple
   candidates are an error requiring review.
5. Retain raw dates. Parse Berth `dd/MM/yyyy HH:mm:ss` and PL.03
   `dd/MM/yyyy - HH:mm` as separate versioned formats; do not rename ATB as
   ATA.
6. Preserve cargo size code, F/E, trade and movement method independently.
   Derived direction and TEU are separate facts with a mapping-version receipt.
7. Preserve weight raw text and parse state, then parse approved strict decimal
   tokens as tonnes. Include both full- and empty-container weight in report
   tonnes; use F/E only to select full-versus-empty TEU columns.
8. Import reported PL.03 rows as immutable report facts. Do not reconstruct
   declarations, approval state or master records.
9. Treat footer position as dynamic and data rows as numeric STT rows beginning
   at row 10, not as a fixed row count.
10. Accept historical header variants only through an explicit version map;
    keep the observed header text even when a canonical metric code corrects
    spelling.

### Minimum sanitized golden fixtures

- exact 1:N Berth/detail join with leading-zero voyage preservation;
- normalized vessel-name candidate caused by case/space/accent/hyphen changes;
- unmatched and ambiguous register link;
- duplicate Berth key at one berth and across two berths;
- hidden detail row and hidden `H:P` values;
- blank ATB, blank ATD and malformed date text;
- valid 20/40 size, unsupported 45/other size and blank size;
- F/E independent from movement method;
- domestic and foreign category cases;
- all four movement methods plus unknown value;
- weight blank, measured zero, decimal, invalid text and unit-not-confirmed;
- PL.03 35-column historical spelling variant and approved corrected-label
  variant;
- hidden `AA:AB`, blank AI, dynamic footer and a missing departure time;
- PL.03 time mismatch, multiple same-name rows and manual reconciliation;
- embedded/standalone register ordinal drift;
- duplicate checksum, corrected revision and overlap-blocked combined view.

## 13. Local render evidence — do not commit

All renders contain real operational or personal data and remain under:

`outputs/historical-tos-workbook-audit-20260718/renders/`

| Workbook / sheet | Render coverage |
|---|---|
| Berth / Sheet1 | `Berth_XL_07.2026__Sheet1__used-range.png` — `A1:Z41` |
| Detail / Sheet1 | parts 01–08 — `A1:AE150`, `A151:AE300`, `A301:AE450`, `A451:AE600`, `A601:AE750`, `A751:AE900`, `A901:AE1050`, `A1051:AE1068` |
| Filled PL.03 / BAO CAO | `BC_THANG_7.26_-PL3__BAO_CAO__used-range.png` — `A1:AI85` |
| Filled PL.03 / DU LIEU | `BC_THANG_7.26_-PL3__DU_LIEU__used-range.png` — `A1:N65` |
| Salan / Sheet2 | `DU_LIEU_SA_LAN_T7.26__Sheet2__used-range.png` — `A1:N65` |
| Blank PL.03 / Sheet | `Phu_luc_3__Sheet__used-range.png` — `A1:AI16` |

Artifact-tool inspect/formula/style outputs and the private raw-value audit JSON
also remain under `outputs/historical-tos-workbook-audit-20260718/` and must not
be committed.

## Completion decision

- Workbooks fully inspected: all five required workbooks; six sheets.
- Locked or unreadable workbooks: none. Read locks were handled without closing
  the user's Excel process or changing a source file.
- Source workbooks modified: none.
- Formula scan: pass, with zero formulas and zero detected formula errors.
- Full used-range visual pass: complete across 13 renders. Hidden detail rows
  and hidden columns were structurally inspected even though a normal render
  intentionally suppresses them.
- Sanitization: this report and the JSON draft contain no raw operational row,
  vessel name, registration, phone number or person name.
- H0: **not closed**.
- Parser DESIGN: Codex may begin a bounded TOS/PL.03 parser design using the
  exact physical positions and fail-closed contracts in these artifacts. It
  may not finalize H1, implement schema/parser/dashboard, or claim production
  readiness until the open decisions and missing PL.01/PL.02 samples are
  resolved and approved.
