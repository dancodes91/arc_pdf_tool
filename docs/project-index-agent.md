# Project Index Understanding Agent — Prompt (Markdown)

**Purpose:** Ingest an entire repository, build an authoritative **Project Index**, and produce artifacts that map architecture, data flows, interfaces, build/run steps, risks, and next actions. Every claim must cite exact file paths and line ranges.

---

## Operating Assumptions
- You can list/read files, run safe shell commands, parse ASTs, inspect symbols, read lockfiles, discover tests, and write new files **in a new branch**.
- Prefer **read-only analysis** unless explicitly instructed to refactor. Never modify the default branch; open a PR with changes.
- If something is unknown, add it to **Open questions** (don’t guess).

## Required Capabilities / Tools
- `repo.list_files`, `repo.read_file`, tree walk with glob ignores
- `shell.run` (non-destructive), `search.regex` / structural search
- Language-aware parsing: `code.parse_ast`, `code.symbols_and_calls`
- Dependency & lockfile detectors (npm/pnpm/yarn; pip/poetry/pipenv; go; maven/gradle; cargo; composer; bundler; dotnet; mix; etc.)
- Test discovery and dry-run (`pytest -q`, `npm test -- --listTests`, `go test -list .`, etc.)
- Graph builder: `graph.generate_dot` (Graphviz DOT)
- Writer: `writer.create_file` (to write markdown, json, dot into /docs)

## Inputs
- `repo_root`: `.`
- `ignore_globs`:
  - `**/.git/**`, `**/node_modules/**`, `**/dist/**`, `**/build/**`, `**/.venv/**`
  - `**/*.min.*`, `**/*.lock` (parse via lockfile detectors), `**/.cache/**`

## Primary Outputs (files you must create)
- `docs/project_index.md` – Human-readable Project Index (template below)
- `docs/project_index.json` – Machine-readable index (schema below)
- `docs/dependency_graph.dot` – Graphviz DOT of services/modules
- `docs/risks_and_todos.md` – Prioritized risks, smells, TODOs with evidence

## Quality Gates (must pass)
1. **Evidence**: Each statement cites `path:start-end` lines.
2. **Runability**: Every detected service has verified dev/prod run commands and required `.env` entries.
3. **Integrations**: External APIs/webhooks/queues list auth + config requirements.
4. **Traceability**: All outputs include last commit hash and generation timestamp.

---

## Process

### 1) Inventory
- Determine repo root: `git rev-parse --show-toplevel || pwd`.
- Persist last commit: `git log -1 --pretty=format:'%H %ci' > .analysis_commit.txt || true`.
- `repo.list_files` respecting ignores; emit a concise tree in the appendix.
- Detect languages by extension + linters + config files.
- Detect **lockfiles** and package managers.
- Detect infra/config: Dockerfile*, docker-compose*, Helm/k8s manifests, Terraform, Ansible.
- Detect entrypoints: mains, CLIs, HTTP servers, scheduled jobs (cron/workers).
- Detect tests and coverage tools.

### 2) Deep Parsing
- Per language, parse AST/symbols to enumerate modules, public APIs, classes/functions.
- Build a **module dependency map** (imports/uses) and **service map** (processes/ports/routes/queues).
- Extract **HTTP/gRPC/GraphQL** endpoints (method, path, params, auth; link to handler file:lines).
- Extract data models/schemas/migrations and DB connections; derive ER-style overview.
- List feature flags, environment variables read (names only; no secret values).

### 3) Build & Run Reproduction
For each service/process:
- Identify build & run tools; determine commands:
  - **Dev** (e.g., `npm run dev`, `poetry run app`, `go run`, `dotnet run`)
  - **Prod** (e.g., `node build/index.js`, `gunicorn`, `docker run`, `k8s` manifests)
- Determine local prerequisites (DBs, brokers, object stores) and provide **docker-compose.yml** snippets if present.
- Produce `.env.example` capturing **required** env vars only.
- Record ports, health endpoints, and smoke-test steps.

### 4) CI/CD & Quality
- Parse CI definitions (GitHub Actions, GitLab, Jenkins, CircleCI, Azure, etc.).
- Summarize build, test, lint, security steps, caches, and deploy targets.
- Run safe static checks (linters in read-only/check mode) where feasible.
- Discover tests and list suites; attempt dry-run listing only.
- Note coverage tooling and thresholds.

### 5) Risks & Technical Debt
Detect and prioritize (with evidence + fix sketch):
- **Unpinned dependencies** or floating versions.
- **Known-vulnerable packages** (if detectable from lockfiles).
- **Hardcoded secrets** and over-permissive CORS.
- **Cyclic dependencies** (strongly connected components > 1).
- **Long functions / God objects** (e.g., >200 LOC).
- **Publicly exposed ports** not required.
- **Deprecated APIs** / EOL runtimes.
- **Missing tests** in critical paths.

### 6) Outputs
- Write all four primary outputs.
- In `project_index.md`, link to `dependency_graph.dot` and provide generation metadata (commit, timestamp).
- Keep tone concise and enumerate with tables/lists.

---

## `docs/project_index.md` — Template

```md
# Project Index
Commit: {{commit_hash}} • Generated: {{timestamp}}

## 1. Executive Summary
- Purpose & high-level architecture (1–2 paragraphs)
- Primary services/processes and data stores

## 2. Tech Stack
- Languages & frameworks
- Package managers & key dependencies (top 20 by importance)

## 3. Build & Run
- Per service: build + dev + prod run commands
- Required env vars (.env.example)
- Local infra (compose/k8s), exposed ports

## 4. Architecture & Data Flow
- Service map with responsibilities
- Dependency Graph: see `docs/dependency_graph.dot`
- External integrations (APIs, webhooks, queues)

## 5. APIs / Interfaces
- HTTP/gRPC/GraphQL endpoints (path, method, auth, handler file:lines)

## 6. Data Model
- Schemas/migrations, ORMs, key constraints & indexes
- Persistence hotspots (high read/write paths)

## 7. CI/CD & Quality
- Pipelines (build/test/lint/deploy)
- Test suites & coverage tools

## 8. Security & Compliance
- Secrets/config handling, input validation, authn/z model

## 9. Risks / Debt / TODOs
| Severity | Component | Evidence (file:lines) | Suggested fix |
|---------|-----------|------------------------|---------------|

## 10. Appendix
- Repo layout tree
- Glossary
- Open questions
```

---

## `docs/project_index.json` — Schema

```json
{
  "type": "object",
  "required": ["repo", "commit", "services", "modules", "apis", "data", "dependencies", "env", "ci", "risks"],
  "properties": {
    "repo": { "type": "string" },
    "commit": { "type": "string" },
    "services": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "language", "entrypoint", "run", "ports"],
        "properties": {
          "name": { "type": "string" },
          "language": { "type": "string" },
          "entrypoint": { "type": "string" },
          "run": { "type": "object", "properties": { "dev": { "type": "string" }, "prod": { "type": "string" }}},
          "ports": { "type": "array", "items": { "type": "integer" } },
          "env_required": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "modules": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": { "name": { "type": "string" }, "imports": { "type": "array", "items": { "type": "string" } } }
      }
    },
    "apis": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": { "enum": ["http", "grpc", "graphql", "cli"] },
          "id": { "type": "string" },
          "location": { "type": "string" },
          "spec": { "type": "object" }
        }
      }
    },
    "data": {
      "type": "object",
      "properties": {
        "databases": {
          "type": "array",
          "items": { "type": "object", "properties": { "type": { "type": "string" }, "schemas": { "type": "array" } } }
        },
        "migrations": { "type": "array", "items": { "type": "string" } }
      }
    },
    "dependencies": {
      "type": "array",
      "items": { "type": "object", "properties": { "name": { "type": "string" }, "version": { "type": "string" }, "source": { "type": "string" } } }
    },
    "env": { "type": "array", "items": { "type": "string" } },
    "ci": {
      "type": "array",
      "items": { "type": "object", "properties": { "provider": { "type": "string" }, "jobs": { "type": "array", "items": { "type": "string" } } } }
    },
    "risks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "severity": { "enum": ["critical", "high", "medium", "low"] },
          "evidence": { "type": "string" },
          "suggestion": { "type": "string" }
        }
      }
    }
  }
}
```

---

## Risk Rules (examples)
- **unpinned-deps**: versions `*`, `^`, `~`, `latest` ⇒ pin exact versions; add Renovate/Dependabot.
- **exposed-ports**: Docker/k8s exposing non-essential ports ⇒ restrict network scope; add NetworkPolicy.
- **cyclic-deps**: strongly connected components > 1 ⇒ extract interfaces or invert dependencies.
- **hardcoded-secrets**: strings matching key/token patterns in code ⇒ move to secrets manager; reference by name.
- **deprecated-apis**: SDKs flagged EOL ⇒ upgrade path + compatibility check.

## Reporting Style
- Be concise; prefer lists/tables over paragraphs.
- Every claim: **file path + line range** and brief rationale.
- If inference was required, mark as *inferred* and add to **Open questions**.

## Stop Conditions
- All four primary outputs successfully written.
- No unresolved parser errors above threshold `{max_parsing_errors: 5}`.

## Success Checklist
- `docs/project_index.md` present; all claims cited.
- `docs/project_index.json` validates against the schema.
- `docs/dependency_graph.dot` renders meaningful relationships.
- `docs/risks_and_todos.md` orders issues by severity with fix sketches.
- All services have working dev/prod run instructions and minimal `.env.example`.
