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
