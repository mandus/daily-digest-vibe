# Agent Workflow Guidelines

This document outlines the required workflow for AI agents (like Mistral Vibe Code) working on this repository.

## 🚨 CRITICAL RULES

### 1. **ALWAYS Create a New Branch**
Before making ANY changes to the codebase:
```bash
# Check current branch
git branch

# Create a new feature/fix branch
git checkout -b vibe/<short-description>-<timestamp>
# Example: git checkout -b vibe/add-web-templates-1b6434
```

**NEVER work directly on `main` branch.**

### 2. **Commit Early, Commit Often**
- Make small, focused commits
- Use clear, descriptive commit messages
- Commit after each logical change

### 3. **Create a Pull Request**
After completing work on your branch:
```bash
# Push your branch to remote
git push -u origin vibe/<your-branch>

# Create a draft PR on GitHub
# (This can be done via CLI or GitHub UI)
```

## ✅ Required Workflow

```
1. Identify the task/feature/bug
2. Create new branch: vibe/<description>-<timestamp>
3. Make changes in the new branch
4. Test your changes locally
5. Commit changes with clear messages
6. Push branch to remote
7. Create Draft PR on GitHub
8. Wait for review/approval
9. Address feedback in the same branch
10. Merge via PR (never direct push to main)
```

## 📝 Branch Naming Convention

Use the format: `vibe/<short-description>-<timestamp>`

Examples:
- `vibe/fix-embedding-service-1b6434`
- `vibe/add-user-auth-1b6434`
- `vibe/update-web-styling-1b6434`
- `vibe/refactor-storage-1b6434`

The timestamp (e.g., `1b6434`) helps identify when the branch was created.

## 🔒 Main Branch Protection

The `main` branch is **protected** and requires:
- ✅ Pull request reviews before merging
- ✅ Status checks to pass
- ✅ No direct pushes allowed
- ✅ Linear history (no merge commits)

## 🛠️ Development Setup

```bash
# Clone the repo
gh repo clone mandus/daily-digest-vibe
cd daily-digest-vibe

# Create working branch
git checkout -b vibe/your-feature-1b6434

# Install dependencies with uv
uv sync

# Or with pip
pip install -r requirements.txt
```

## 📋 Before Starting Work

1. **Pull latest changes** from main:
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create your branch** from updated main:
   ```bash
   git checkout -b vibe/your-feature-1b6434
   ```

3. **Verify you're on the correct branch**:
   ```bash
   git branch  # Should show your new branch with *
   ```

## 🎯 After Completing Work

1. **Test your changes**
2. **Commit all changes**
3. **Push to remote**
4. **Create Draft PR**

## ❌ NEVER DO

- ❌ Work directly on `main` branch
- ❌ Push directly to `main` branch
- ❌ Force push to `main` branch
- ❌ Merge branches without PR
- ❌ Delete other people's branches
- ❌ Commit with vague messages like "fix stuff" or "wip"

## 📚 Additional Resources

- [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow)
- [GitHub Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Semantic Commit Messages](https://www.conventionalcommits.org/)

## 🤖 Agent-Specific Notes

If you're an AI agent (Mistral Vibe Code, etc.):

1. **Always read this file first** when starting a new session
2. **Check current branch** before making changes:
   ```bash
   git branch
   ```
3. **If on main**, immediately create a new branch
4. **Document your work** in commit messages
5. **Create PRs** for all non-trivial changes

## ⚠️ Common Pitfalls & How to Avoid Them

### FastAPI TemplateResponse API
**Problem:** Using Flask-style template rendering with FastAPI causes `TypeError: unhashable type: 'dict'`

**❌ Wrong (Flask-style):**
```python
return templates.TemplateResponse("index.html", {
    "request": request,
    "data": my_data
})
```

**✅ Correct (FastAPI/Starlette-style):**
```python
return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={
        "data": my_data
    }
)
```

**Why:** FastAPI's `TemplateResponse` uses keyword arguments, not positional dict arguments.

### Pydantic Models in Templates
**Problem:** Pydantic models can't be directly rendered in Jinja2 templates

**❌ Wrong:**
```python
return templates.TemplateResponse(..., context={"story": story_model})
```

**✅ Correct:**
```python
return templates.TemplateResponse(..., context={"story": story_model.model_dump()})
```

**Why:** Jinja2 can't serialize Pydantic models. Use `.model_dump()` or `.dict()` to convert to plain dict.

### Datetime Objects in Templates
**Problem:** Datetime objects cause serialization errors in Jinja2

**✅ Solution:** Add custom Jinja2 filters:
```python
from jinja2 import Environment, PackageLoader, select_autoescape

def format_datetime(value, format="%Y-%m-%d %H:%M:%S"):
    if value is None:
        return ""
    if hasattr(value, 'strftime'):
        return value.strftime(format)
    return str(value)

env = Environment(loader=PackageLoader("package", "templates"))
env.filters["datetime"] = format_datetime
templates = Jinja2Templates(env=env)
```

Then in templates: `{{ my_date|datetime }}`

### Always Test Web Endpoints
Before committing web changes:
```bash
# Test the server locally
uv run uvicorn web.main:app --reload

# Test key endpoints
curl http://localhost:8000/
curl http://localhost:8000/api/digest
```

## 🔍 Debugging Tips

1. **Check the exact error message** - It often tells you exactly what's wrong
2. **Compare with working examples** - Look at existing code in the repo
3. **Read the framework docs** - FastAPI, Starlette, Jinja2 have great documentation
4. **Test incrementally** - Add one feature at a time and test

## 🆘 Emergency Recovery

If you accidentally made changes on main:

```bash
# Stash your changes
git stash

# Create a new branch
git checkout -b vibe/recovery-1b6434

# Apply your changes
git stash pop

# Commit and push
git add -A
git commit -m "Recovered changes"
git push -u origin vibe/recovery-1b6434

# Reset main to remote state
git checkout main
git reset --hard origin/main
```

---

**Remember**: Protecting `main` ensures code quality and prevents accidental breaks. Always use branches and PRs!
