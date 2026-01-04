---
description: Project rules and conventions that must be followed
---

# PCA Agent Rulebook

## 🔐 Authentication Credentials

**PERMANENT LOGIN CREDENTIALS - DO NOT CHANGE**

| Field | Value |
|-------|-------|
| Username | `ashwin` |
| Password | `Pca12345!` |
| Role | `admin` |
| Tier | `enterprise` |

> [!CAUTION]
> These credentials are frozen and must not be modified. Any changes to login functionality must preserve these exact credentials.

## Rules

1. **Login Credentials**: The username `ashwin` with password `Pca12345!` must always work for authentication.

2. **Database Preservation**: The user entry for `ashwin` in the SQLite database must not be deleted or modified.

3. **Password Requirements**: If the password validation rules change, they must still accept `Pca12345!` as a valid password.

---

*Last updated: 2026-01-02*

4. **Safety First (Refactoring Rule)**: When making major changes to a major component, **always create a copy of the parent file first** (`filename.py.bak` or `_backup.py`). This allows for immediate rollback if the refactor fails.
    - *Example*: Before refactoring `auto_insights.py`, run `cp auto_insights.py auto_insights_backup.py`.