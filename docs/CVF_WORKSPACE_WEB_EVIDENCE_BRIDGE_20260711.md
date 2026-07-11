# CVF Workspace-To-Web Evidence Bridge

> Date: 2026-07-11
> Record ID: W114-CP6-BRIDGE-20260711-Khai-bao-Cang-vu
> Status: PASS
> Project: d:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu
> CVF Core: D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\.Controlled-Vibe-Framework-CVF
> CVF Core Commit: a78b35c

## 1. Purpose

This receipt lets a downstream workspace point to CVF Web live governance proof without copying, storing, or printing provider API keys inside the downstream project.

It bridges three evidence layers:

1. workspace enforcement artifacts in this downstream project;
2. optional secret-free live readiness visibility from the operator environment;
3. CVF core/web release evidence that must be run from the CVF core repository.

## 2. Workspace Enforcement

- Workspace doctor status: PASS
- Doctor command:

~~~powershell
powershell -ExecutionPolicy Bypass -File "D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\.Controlled-Vibe-Framework-CVF\scripts\check_cvf_workspace_agent_enforcement.ps1" -ProjectPath "d:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu" -CheckLiveReadiness
~~~

- Optional live readiness summary: live_key_available=false
- Raw provider key values: NOT PRINTED
- Provider keys copied into downstream project: NO

## 3. CVF Web Live Governance Proof Reference

Run release-quality governance proof from the CVF core repository:

~~~bash
python scripts/run_cvf_release_gate_bundle.py --json
~~~

Latest attached result:

~~~text
PASS
~~~

Canonical CVF evidence references:

- docs/assessments/CVF_W114_T1_NONCODER_OUTCOME_EVIDENCE_PACK_2026-04-23.md
- docs/assessments/CVF_W114_T1_NONCODER_OUTCOME_EVIDENCE_RAW_2026-04-23.json
- docs/assessments/CVF_W114_T1_WEB_BENEFIT_VISIBILITY_ASSESSMENT_2026-04-23.md
- docs/roadmaps/CVF_W114_T1_NONCODER_VALUE_MAXIMIZATION_AND_EVIDENCE_ROADMAP_2026-04-22.md

## 4. Claim Boundary

This downstream project may claim:

- the workspace is agent-enforcement-ready when the doctor status is PASS;
- live provider readiness was checked secret-free only if -CheckLiveReadiness was used;
- CVF Web governance proof is inherited by reference to the CVF core release gate and evidence records.

This downstream project must not claim:

- that provider API keys are stored or distributed by .cvf/;
- that workspace doctor pass proves provider connectivity;
- that mock UI checks prove governance behavior;
- that Web is the full CVF runtime.

## 5. Doctor Output

~~~text
CVF Workspace Agent Enforcement Doctor
=======================================
Project: d:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu


  Check                                              Status
  -------------------------------------------------- ------
  Project folder exists                              [PASS]
  Project isolated from CVF core                     [PASS]
  .cvf/manifest.json exists                          [PASS]
  .cvf/manifest.json is valid                        [PASS]
  .cvf/policy.json exists                            [PASS]
  Live governance evidence mandatory                 [PASS]
  AGENTS.md exists                                   [PASS]
  Bootstrap log exists                               [PASS]
  CVF core path reachable                            [PASS]
  Workspace rules file exists                        [PASS]
  CVF core origin is public remote                   [PASS]
  Public workspace kit is complete                   [PASS]
  CVF public core matches origin/main                [PASS]
  CVF public core worktree clean                     [PASS]
  CVF core commit matches manifest                   [PASS]
  Required docs referenced by manifest exist         [PASS]
  knowledge/ folder present (optional)               [PASS]

CVF Live Governance Readiness (optional, secret-free)
====================================================
  live_key_available: false
  provider_lane:      none
  key_name:           none
  source:             none
  raw_key_value:      NOT PRINTED
  release_gate:       python scripts/run_cvf_release_gate_bundle.py --json
  note: Missing live key does not fail workspace enforcement doctor.

  RESULT: PASS (17/17 checks passed)
  This workspace is agent-enforcement-ready.
~~~
