# DB Migration Risk Specialist

A new specialist for the Closeread audit pipeline. Reads the repository's migration history, the ORM model definitions, and the deployment configuration to flag database changes that carry irreversible-data-loss risk, downtime risk, or schema-drift risk. Outputs structured findings consumable by the packet renderer and one LLM-summarized paragraph for the buyer-facing artifact.

The target build time is 1-2 days for a developer familiar with the Closeread specialist contract. The specialist is deterministic in its detection layer and only invokes an LLM in the final summarization step.

## Scope

The specialist answers a single buyer DD question: "what does this codebase tell me about how the seller manages schema change, and what risk do the next 10 deploys carry?"

It covers four risk classes:

1. **Irreversible migrations.** `DROP COLUMN`, `DROP TABLE`, `RENAME COLUMN` (no rollback path), destructive `ALTER COLUMN TYPE` (lossy casts), and `DELETE FROM` inside a migration. Any of these without a corresponding `down`/`reverse` method or backup step is a finding.
2. **Missing migration files.** ORM model fields defined in code that have no corresponding `CREATE TABLE` / `ADD COLUMN` migration anywhere in the migration directory. Indicates schema drift between code and database.
3. **Long-lock migrations.** Migrations that hold exclusive locks on tables likely to be large (presence of `ALTER TABLE` without `ALGORITHM=INPLACE` on MySQL, missing `CONCURRENTLY` on PostgreSQL index operations, table renames without shadow-table pattern). High-downtime-risk on production.
4. **Schema drift indicators.** Evidence that staging and production schemas diverge: multiple `*-hotfix-*` migrations, `manual_fix_*` migration filenames, README/CHANGELOG references to "run this manually in prod", or comments inside migrations saying `# TODO apply to staging`.

## Out of scope

- **Migration runtime profiling.** The specialist does not execute migrations or estimate row counts. Lock-duration claims are based on operation type, not measured data volume.
- **Cross-database compatibility.** Whether a Postgres-only operation works on the seller's RDS instance is the buyer's runtime DD problem.
- **Data quality.** Whether the seller's `users.email` column has duplicate rows is a data audit, not a schema audit.
- **Application code referencing dropped columns.** The dependency graph between application code and DB schema is the architecture specialist's surface, with a cross-reference back here when relevant.

## Supported ORMs and migration directories

Each entry lists the canonical migration directory layout, the filename pattern, and the parser used.

| ORM | Migration dir | File pattern | Parser |
|---|---|---|---|
| Django | `*/migrations/` | `NNNN_*.py` | Python AST: walk `operations = [...]` list, match `migrations.RunSQL`, `migrations.RemoveField`, `migrations.AlterField`, `migrations.DeleteModel` |
| Rails ActiveRecord | `db/migrate/` | `YYYYMMDDHHMMSS_*.rb` | Ruby regex: match `def change`, `def up`, `def down`, and DSL calls (`drop_table`, `remove_column`, `change_column`) |
| Prisma | `prisma/migrations/*/` | `migration.sql` | Raw SQL parser (sqlparse) per migration directory |
| Drizzle | `drizzle/` or `migrations/` | `NNNN_*.sql` + `_meta/_journal.json` | Raw SQL parser + journal cross-reference for ordering |
| Knex | `migrations/` | `YYYYMMDDHHMMSS_*.js` / `.ts` | JS/TS AST (acorn or @babel/parser): walk `exports.up` / `exports.down`, match knex schema DSL calls |
| Alembic | `alembic/versions/` | `*.py` | Python AST: walk `upgrade()` / `downgrade()`, match `op.drop_column`, `op.alter_column`, `op.execute` |
| Raw SQL | `db/migrations/`, `sql/`, `migrations/` | `*.sql` (any naming) | Raw SQL parser, ordering inferred from filename sort |

For repos that use a non-canonical layout, the specialist falls back to a recursive glob for any directory containing 3 or more files matching `*migration*` or `*migrate*` in any of the supported extensions. If detection fails entirely, the specialist emits one INFO finding ("no migrations directory detected") and exits with a clean health score for this artifact.

## Detection passes

Five deterministic passes run per detected migration system. Each pass emits zero or more raw hits that are deduplicated, severity-scored, and shaped into findings by the post-processor.

### Pass 1: irreversibility scan

For each migration file in chronological order:

- Parse to extract the list of operations.
- For each operation, classify as `destructive` (drops data), `lossy` (changes type with no safe cast), or `safe`.
- For each destructive or lossy operation, check whether the same file (or its sibling `down` file) contains a recovery path (`add_column` with the same name, `op.execute("BACKUP ...")`, etc.).
- Flag operations with no recovery path. Severity scales with operation: `DROP TABLE` is HIGH, `DROP COLUMN` is MEDIUM, lossy `ALTER COLUMN TYPE` is MEDIUM, `RENAME COLUMN` without alias is LOW (data preserved, application code may break).

### Pass 2: model-to-migration parity

For each ORM with model definitions in code (Django models.py, Rails ActiveRecord classes, Prisma schema.prisma, Drizzle schema.ts, Alembic SQLAlchemy models):

- Build the set of `(table, column)` pairs declared in models.
- Build the set of `(table, column)` pairs created or added across the full migration history.
- Diff. Any model column without a corresponding migration is a HIGH finding (the seller's code expects a column that the migrations have not created; either the migration is missing or it was applied manually in production).
- Reverse diff (migrations that create columns no longer present in any model) is a LOW finding (dead column, candidate for cleanup).

### Pass 3: lock-duration heuristic

For each migration operation, classify by database engine + operation type:

- PostgreSQL: `CREATE INDEX` without `CONCURRENTLY` → MEDIUM. `ALTER TABLE ... ADD CONSTRAINT` without `NOT VALID` then `VALIDATE` two-step → MEDIUM. `ALTER COLUMN TYPE` on a column with a default → HIGH (table rewrite).
- MySQL: `ALTER TABLE` without `ALGORITHM=INPLACE, LOCK=NONE` → MEDIUM. Any DDL on InnoDB before MySQL 5.6 → HIGH (full table copy).
- SQLite: any `ALTER TABLE` other than `ADD COLUMN` → MEDIUM (SQLite rewrites the table).
- Generic: `UPDATE` or `DELETE` inside a migration with no `WHERE` clause → HIGH (full table scan + lock).

If the migration file contains a comment indicating awareness (`-- safe for prod`, `-- requires downtime`, `# zero-downtime: false`), the severity is unchanged but the finding's `rationale` field notes the seller's awareness.

### Pass 4: drift indicators

Walk the migration directory listing + the repo's documentation:

- Filenames matching `*hotfix*`, `*manual*`, `*adhoc*`, `*emergency*` → one MEDIUM finding per cluster (3+ in the same year is a pattern, not an incident).
- Comments inside migrations matching `apply manually`, `run in production`, `TODO apply`, `not yet applied`, `WIP` → MEDIUM finding per file.
- README or CHANGELOG mentions of `run X in production`, `manual schema change`, `out of band` → MEDIUM finding with file reference.
- Gaps in migration timestamp sequence larger than the codebase median by 3x → LOW finding (suggests squashed-and-deleted migrations, history rewrite, or branch-merge gaps).

### Pass 5: rollback discipline

For each migration with destructive operations from Pass 1:

- Django: presence of a corresponding `RunPython` with a `reverse_code` callable other than `migrations.RunPython.noop`.
- Rails: presence of an explicit `def down` method (not just `def change`).
- Alembic: presence of a non-empty `downgrade()` function.
- Knex: presence of `exports.down`.
- Prisma/Drizzle/raw SQL: presence of a sibling `*_down.sql` or `*_rollback.sql` file in the same directory.

Migrations missing the rollback path get a LOW finding aggregated across the repo (the count itself is the finding, not one finding per migration).

## Finding shapes

The specialist emits findings conforming to the Closeread standard finding envelope. Five finding types are defined.

### Finding 1: `db.migration.irreversible_destructive_op`

```json
{
  "id": "db.migration.irreversible_destructive_op",
  "severity": "HIGH",
  "title": "Destructive migration with no rollback path",
  "file": "db/migrate/20251104223344_drop_legacy_orders.rb",
  "line": 7,
  "quoted_code": "drop_table :legacy_orders",
  "operation": "drop_table",
  "table": "legacy_orders",
  "orm": "rails",
  "rationale": "drop_table inside def change with no def down. ActiveRecord will not know how to reverse this migration; rollback requires manual intervention. Buyer's M&A engineering team will flag this.",
  "remediation": "Replace def change with explicit def up + def down. The down method should recreate the table from a backup or snapshot reference."
}
```

### Finding 2: `db.migration.missing_for_model_field`

```json
{
  "id": "db.migration.missing_for_model_field",
  "severity": "HIGH",
  "title": "ORM model column has no creating migration",
  "model_file": "apps/billing/models.py",
  "model": "Invoice",
  "column": "stripe_payment_intent_id",
  "orm": "django",
  "rationale": "models.Invoice.stripe_payment_intent_id is declared in code but no migration in the apps/billing/migrations/ directory creates it. This indicates either a missing migration file or a manual schema change applied directly to production.",
  "remediation": "Run python manage.py makemigrations billing and commit the generated file. If the column already exists in production, use makemigrations --empty + RunPython.noop to backfill the migration history without altering the schema."
}
```

### Finding 3: `db.migration.long_lock_risk`

```json
{
  "id": "db.migration.long_lock_risk",
  "severity": "MEDIUM",
  "title": "Migration likely to hold table lock on large tables",
  "file": "alembic/versions/2025_11_14_add_index_to_events.py",
  "line": 14,
  "quoted_code": "op.create_index('ix_events_user_id', 'events', ['user_id'])",
  "engine": "postgresql",
  "operation": "create_index",
  "rationale": "CREATE INDEX without CONCURRENTLY on PostgreSQL takes an ACCESS EXCLUSIVE lock for the duration of the build. On a multi-million-row events table this can mean minutes of write downtime. Standard zero-downtime pattern is op.create_index(..., postgresql_concurrently=True) with op.execute('COMMIT') boundaries.",
  "remediation": "Rewrite as a manually-wrapped CONCURRENTLY index build, or document the expected lock duration in a comment + deploy runbook."
}
```

### Finding 4: `db.migration.drift_indicator`

```json
{
  "id": "db.migration.drift_indicator",
  "severity": "MEDIUM",
  "title": "Migration filename pattern suggests out-of-band schema change",
  "files": [
    "db/migrate/20250803_manual_fix_billing.rb",
    "db/migrate/20251012_hotfix_users_email.rb",
    "db/migrate/20251201_emergency_revert_orders.rb"
  ],
  "rationale": "Three migration files within the past 18 months follow the *hotfix* / *manual* / *emergency* naming pattern. This is a pattern, not an incident; it indicates the seller has applied schema changes out of the normal review path. Buyer's M&A engineering will read this as a process-discipline signal.",
  "remediation": "Document the incidents that produced these migrations + describe the policy update that prevents recurrence. The packet narrative should name the pattern explicitly."
}
```

### Finding 5: `db.migration.rollback_missing_aggregate`

```json
{
  "id": "db.migration.rollback_missing_aggregate",
  "severity": "LOW",
  "title": "Migrations without explicit rollback methods",
  "count": 14,
  "total_migrations": 87,
  "orm": "alembic",
  "examples": [
    "alembic/versions/2024_06_03_add_index.py",
    "alembic/versions/2024_08_19_alter_column_type.py",
    "alembic/versions/2025_01_22_drop_unused_column.py"
  ],
  "rationale": "14 of 87 Alembic migrations have an empty or pass-only downgrade() function. Forward-only is a defensible pattern if the seller has explicitly chosen it, but the absence of explicit declaration leaves the buyer uncertain. A single forward-only policy in CONTRIBUTING.md resolves the ambiguity.",
  "remediation": "Either fill the downgrade() functions or add a forward-only declaration to CONTRIBUTING.md naming the policy + the rollback strategy (point-in-time recovery, full restore, etc.)."
}
```

## Severity rubric specific to this specialist

- **HIGH**: any destructive operation (DROP TABLE, DELETE without WHERE) without rollback path; any model column missing a creating migration; full-table-rewrite operations on tables likely to be large.
- **MEDIUM**: long-lock operations, drift-indicator clusters, lossy column type changes, missing concurrent-index pattern on PostgreSQL.
- **LOW**: rename without alias (data preserved but application code may break), forward-only migrations in aggregate, migration history timestamp gaps.
- **INFO**: detected migration system + count + last migration date (always emitted, never absent).

## LLM summarization prompt

After deterministic detection, the post-processor calls the configured LLM once per artifact with the following prompt. The model receives only the structured findings and basic repo metadata; it does not see source code beyond the `quoted_code` fields already in the findings.

```
You are writing one paragraph for a code-audit packet that a software business owner will hand to a prospective buyer. The reader is an M&A engineering reviewer; they have 90 seconds for this paragraph before moving on.

Context: this specialist analyzed the database migration history of a {LANGUAGE} codebase using {ORM}. It found {N_HIGH} HIGH-severity issues, {N_MEDIUM} MEDIUM-severity issues, and {N_LOW} LOW-severity issues across {N_MIGRATIONS} migration files spanning {DATE_RANGE}.

The findings, in priority order:
{FINDINGS_JSON}

Write one paragraph (max 120 words) that:
1. States the headline risk in the first sentence (no hedging, no preamble).
2. Names the worst single finding by file + line if HIGH-severity findings exist.
3. Describes the pattern across findings if more than 3 of the same finding type are present.
4. Closes with the recommended next action (specific, not abstract).

Do not use em dashes. Do not use the word "comprehensive" or "robust". Do not summarize what the specialist does; describe what it found. If there are zero findings, write one sentence stating the migration history is clean and naming the ORM + migration count.

Return only the paragraph. No headings, no bullet points, no markdown.
```

The temperature is set to 0.2. The output is post-processed to strip any em dashes that slip through (Closeread house style) and to assert max-120-word length.

## What "good" looks like in the packet output

A clean DB-migration-risk artifact has:

- Zero HIGH findings.
- An identified ORM + migration directory with a non-empty history.
- Either explicit rollback methods on most destructive migrations, or an explicit forward-only policy documented in `CONTRIBUTING.md` or `docs/database.md`.
- No drift-indicator filename patterns in the past 18 months.
- A statement in the packet narrative naming the ORM + the deploy pattern (online-schema-change tool, blue/green, etc.).

A seller who can hand a buyer a clean DB-migration-risk artifact has removed one of the top three "what breaks in the first 30 days post-close" concerns from the buyer's diligence queue.

## Detection caveats

- **Squashed migrations.** Django's `squashmigrations` and Rails's `db:schema:dump` rewrite the migration history. The specialist treats the squashed file as the canonical history; older deleted migrations are not analyzed. The parity pass (Pass 2) still works correctly because it compares current models to current migrations.
- **Multiple databases.** A repo with Postgres for the main app and SQLite for a worker queue has two migration directories. The specialist runs once per detected directory + emits findings keyed by which.
- **Monorepos.** A monorepo with N apps under `services/*/migrations/` runs N independent passes and aggregates findings under per-app sub-artifacts.
- **Custom DSLs.** Some shops wrap their ORM in custom DSLs (e.g., a homegrown migration framework on top of raw SQL). The raw-SQL parser handles these as a fallback; the specialist will not detect the custom DSL's safety guarantees and may over-flag.
- **Hand-written downgrades that lie.** A `def down` that contains `raise NotImplementedError` is still flagged as having a rollback method by the AST pass; the static-analysis layer cannot detect runtime falsehood. The specialist accepts this false-negative rate as preferable to running migrations in a sandbox.

## Related artifacts

- `02-reliability.md`: silent failures during migration are a reliability finding; the two artifacts cross-reference when a migration also lacks error handling.
- `07-credentials.md`: migration files occasionally embed credentials (legacy systems migrating from one DB to another with hardcoded source DSN). The credentials specialist catches these independently.
- `09-test-coverage.md`: a codebase that ships destructive migrations with no migration-tests is doubly risky. The packet narrative cross-references both artifacts.

## Build estimate

The deterministic detection layer is approximately 800 lines of Python across six modules (one per supported ORM + raw SQL). The model-parity pass is the longest single module (parsing Django models.py, Rails AR classes, Prisma schema, and Drizzle schema.ts each requires ecosystem-specific code) at roughly 300 lines. The LLM summarization is 40 lines of glue. Total build estimate is 1-2 developer days assuming the developer is familiar with the existing Closeread specialist contract (finding envelope, artifact health rubric, packet renderer interface).
