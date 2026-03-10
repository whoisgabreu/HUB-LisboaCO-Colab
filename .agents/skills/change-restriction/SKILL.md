---
name: change-restrictions
description: Enforces strict modification rules for the Antigravity project. Use when implementing code changes, bug fixes, or feature updates to ensure the agent does not modify restricted areas such as database, models, services, or existing business rules.
---

# Change Restrictions Skill

This skill enforces **strict constraints for code modifications** in the Antigravity project.

The goal is to ensure that updates are **minimal, safe, and limited to the requested scope**, avoiding unintended side effects.

---

# Core Restrictions

The agent MUST follow these rules:

1. **Database Protection**
   - It is strictly forbidden to perform any modification to the database.
   - Do not create, alter, remove, or migrate tables.
   - Do not change schema definitions.

2. **Services Protection**
   - Existing services must NOT be modified.
   - If additional logic is required, implement it outside the existing services.

3. **Models Protection**
   - Existing models must NOT be changed.
   - Do not add, remove, or alter fields in existing models.

4. **Stable Logic Protection**
   - Do not modify logic that is already working correctly.
   - Avoid refactoring existing functional code.

5. **Business Rules Protection**
   - Existing business rules must remain untouched.
   - Never change validation rules, calculations, or decision flows that are already implemented.

6. **Scope Protection**
   - Only implement changes explicitly requested.
   - Do not introduce improvements, refactors, or optimizations outside the scope.

---

# Allowed Changes

The agent may:

- Add **new files** if necessary.
- Add **new isolated logic** that does not affect existing systems.
- Implement **small and direct fixes** strictly related to the requested task.
- Extend functionality **without modifying existing services, models, or database structures**.

---

# Modification Strategy

When implementing a change, follow this decision process:

1. Identify the **exact scope of the request**.
2. Verify whether the change requires:
   - database modification
   - model modification
   - service modification
3. If any of the above is required → **DO NOT proceed**.
4. Look for a **non-invasive alternative solution**.

Prefer:

- wrappers
- adapters
- new helper functions
- new isolated modules

---

# Implementation Guidelines

All updates must be:

- **Minimal**
- **Direct**
- **Efficient**
- **Isolated**

Avoid:

- Large refactors
- Structural changes
- Unnecessary improvements

---

# Safety Checklist

Before applying changes, confirm:

- [ ] Database remains unchanged
- [ ] No existing services were modified
- [ ] No existing models were modified
- [ ] Business rules remain untouched
- [ ] Only requested functionality was implemented
- [ ] Changes are minimal and isolated

If any rule is violated, **stop and search for an alternative solution**.