---
created: 2025-11-24 14:16:05
updated: 2025-11-24 14:34:50
tags: [dev-ops, structure, organization]
author: wonny
status: active
---

# Project Structure

## 📂 Directory Organization

```
joungwon.stocks/
├── src/                   # Source code
│   ├── core/             # Core components
│   ├── fetchers/         # Data fetchers (Tier 1-4)
│   ├── config/           # Configuration
│   └── learners/         # ML/RL agents
│
├── scripts/              # Utility scripts & tests
│   ├── initialize_stocks.py
│   ├── run_initial_collection.py
│   ├── test_fixes.py
│   ├── test_fetchers.py
│   └── test_orchestrator.py
│
├── sql/                  # Database scripts
│   ├── 00_drop_tables.sql
│   ├── 01_create_tables.sql
│   ├── 02_verify_schema.sql
│   ├── 03_add_site_management_tables.sql
│   ├── 04_update_existing_site_tables.sql
│   └── 05_insert_reference_sites.sql
│
├── docs/                 # Documentation & configuration hub
│   ├── requirements.txt  # Python dependencies
│   ├── obsidian/         # Obsidian vault (technical docs)
│   │   ├── changelog/
│   │   ├── dev-ops/
│   │   ├── features/
│   │   └── troubleshooting/
│   ├── cache/            # Library caches (OpenDART, etc.)
│   └── *.md              # General documentation
│
├── venv/                 # Virtual environment
│
├── .env                 # Environment variables
├── .gitignore           # Git ignore rules
├── CLAUDE.md            # Claude Code instructions
└── README.md            # Project overview
```

## 📝 File Organization Rules

### Python Configuration
- **Location**: `docs/requirements.txt`
- **Files**: Python dependencies
- **Note**: Consolidated with documentation

### Database Scripts
- **Location**: `sql/`
- **Pattern**: `##_descriptive_name.sql`
- **Examples**:
  - `00_drop_tables.sql`
  - `01_create_tables.sql`
  - `02_verify_schema.sql`
  - `03_add_site_management_tables.sql`
  - `04_update_existing_site_tables.sql`
  - `05_insert_reference_sites.sql`

### Scripts
- **Location**: `scripts/`
- **Types**:
  - Utility scripts: `initialize_stocks.py`, `run_initial_collection.py`
  - Test scripts: `test_*.py`
- **Note**: Tests are in scripts/ (not separate tests/ folder)

### Documentation
- **docs/requirements.txt**: Python dependencies (pip install -r docs/requirements.txt)
- **docs/obsidian/**: Obsidian vault - Technical docs, changelogs, troubleshooting
- **docs/cache/**: Library caches (OpenDART, etc.)
- **docs/*.md**: General documentation (architecture, integration analysis, etc.)

### Source Code
- **src/core/**: Framework components (BaseFetcher, Orchestrator)
- **src/fetchers/**: Data collection by tier
- **src/config/**: Settings, database, environment
- **src/learners/**: ML/RL agents

## 🎯 Benefits

**Simplicity**:
- ✅ Flat, standard Python project structure
- ✅ No nested dev/ directory
- ✅ Easier navigation and discovery

**Standard Conventions**:
- ✅ Follows Python packaging best practices
- ✅ SQL scripts in sql/ (common pattern)
- ✅ Documentation in docs/
- ✅ Source code in src/

**Maintainability**:
- ✅ Less directory nesting
- ✅ Clearer organization
- ✅ Simpler onboarding

---

**Last Updated**: 2025-11-24 14:34:50
