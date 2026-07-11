# Project Knowledge

Place `.md` files in this folder to inject project-specific context into CVF-governed AI runs.

## How it works

1. Add `.md` files describing your project's specs, decisions, or domain terms.
2. Run `scripts/ingest_cvf_downstream_knowledge.ps1` to index them into `knowledge/_index.json`.
3. CVF-governed `/api/execute` calls that include your `knowledgeCollectionId` will automatically
   retrieve relevant chunks and inject them into the AI system prompt.

## What to put here

- Architecture decisions and rationale
- Domain terminology and definitions
- Project specs, requirements, or acceptance criteria
- Process guides or runbooks your team follows

## What NOT to put here

- Secrets, API keys, or credentials (never - governance enforcement will reject these)
- Binary files or non-markdown formats (not supported in this wave)

## Reference

W116-T1 Downstream Knowledge Pipeline - `docs/roadmaps/CVF_W116_T1_DOWNSTREAM_KNOWLEDGE_PIPELINE_ROADMAP_2026-04-23.md`
