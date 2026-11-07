# Local Skill Development

Guide for creating and testing new skills locally before submitting a pull request.

## Setup

Clone the repo and work from it directly:

```bash
git clone https://github.com/arjun988/blender-skills.git
cd blender-skills
```

## Creating a New Skill

### 1. Create the folder structure

```bash
mkdir -p .claude/skills/my-skill
mkdir -p .claude/skills/my-skill/references
```

### 2. Create `SKILL.md`

Follow the schema exactly (see `CONTRIBUTING.md`). Minimum required:

```yaml
---
name: my-skill
description: Use when [triggering conditions]. Invoke for [keywords].
license: MIT
metadata:
  author: https://github.com/arjun988
  version: "1.0.0"
  domain: blender
  role: specialist
  triggers: keyword1, keyword2
  related-skills: blender-director, blender-modeler
---

# My Skill

One-sentence expert role.

## Role Definition

2–3 sentences. Expert persona, specializations.

## When to Use

- Specific scenario

## Core Workflow

1. **Step** — description

## Constraints

### MUST DO
- [Required]

### MUST NOT DO
- [Anti-pattern]

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|-----------|
| ... | `references/....md` | ... |

## Knowledge Reference

keyword1, keyword2, keyword3
```

### 3. Add reference files (optional)

For large topics, use progressive disclosure:

```bash
# .claude/skills/my-skill/references/topic.md
```

Reference file header:
```markdown
# Topic Title

> Reference for: my-skill
> Load when: [condition]
```

### 4. Test locally

**Cursor:**
```powershell
Copy-Item -Recurse -Force ".claude\skills\*" ".cursor\skills\"
```
Restart Cursor. Prompt: `"Use my-skill to [task]"` — verify it activates and routes correctly.

**Claude Code:**
Skills in `.claude/skills/` are picked up automatically in the project.

### 5. Test MCP operations

With Blender running and BlenderMCP connected, test any `execute_blender_code` calls in your skill. Verify:
- Code runs without Python exceptions
- Objects are named and parented correctly
- Collections use `COL_` prefix
- No destructive joins or deletes on source meshes

### 6. Verify frontmatter

Check your `SKILL.md` has all required fields:

```bash
# Quick check - look for required fields
Select-String -Path ".claude/skills/my-skill/SKILL.md" -Pattern "name:|description:|author:|triggers:|role:|related-skills:"
```

## Syncing `.claude` to `.cursor`

Always sync after changes:

```powershell
Copy-Item -Recurse -Force ".claude\skills\*" ".cursor\skills\"
```

Or add this as a git hook (`scripts/sync-skills.ps1`):

```powershell
# .git/hooks/pre-commit (PowerShell wrapper)
Copy-Item -Recurse -Force ".claude\skills\*" ".cursor\skills\"
git add ".cursor\skills\"
```

## Validating Before Commit

Manually check:

- [ ] Frontmatter has all required fields (`name`, `description`, `author`, `triggers`, `role`, `related-skills`)
- [ ] Description follows formula: `Use when [...]. Invoke for [...].`
- [ ] Sections present: Role Definition, When to Use, Core Workflow, Constraints, Knowledge Reference
- [ ] MCP code tested in Blender (no exceptions)
- [ ] `.cursor/skills/` synced

## Submitting

1. Create a branch: `git checkout -b feature/my-skill`
2. Add and commit: `git add . && git commit -m "Add: My Skill for XYZ"`
3. Push and open a Pull Request
4. See `CONTRIBUTING.md` for PR guidelines

## Blender API Notes (Blender 4.x)

Common gotchas when writing MCP Python:

| Old API | Blender 4.x replacement |
|---------|------------------------|
| `use_auto_smooth` | Removed — use `ShadeSmooth` with `use_auto_smooth=False` |
| `inset_faces` | Use `inset_region` |
| `BLENDER_EEVEE_NEXT` | `BLENDER_EEVEE` in most setups |
| `context.screen.areas` | Can be `None` — use `bpy.context.screen.areas` carefully |
| `bpy.ops.view3d.view_camera()` | Requires `temp_override(area=area, region=region)` |
| Emission `Strength` keyframe on shared mat | Causes white blowout — use per-object `MAT_LightInst_*` |

See `.claude/skills/references/mcp-tools.md` for the full tool catalog.
