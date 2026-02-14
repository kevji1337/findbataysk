# Git History And Deploy Pipeline

## Scope
This document defines:
- how commit history is structured and reviewed;
- how releases are cut;
- how production deployment is executed and verified.

## Commit History Policy
- Branch model:
- `main` is always deployable.
- Feature work goes to `feature/<short-name>`.
- Hotfixes go to `hotfix/<short-name>`.
- Commit format:
- `<type>(<scope>): <summary>`
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ops`.
- One commit = one logical change.
- Forced pushes to `main` are forbidden.

## Required PR Checks
- CI workflow `CI` must pass.
- At least one reviewer approval.
- No unresolved comments.
- Migration review required for DB schema changes.

## Release Process
1. Merge approved PR to `main`.
2. Create annotated tag: `vX.Y.Z`.
3. Push tag.
4. `Deploy Production` workflow runs automatically for tags.
5. Run post-deploy smoke checks.

## Deployment Pipeline
- File: `.github/workflows/deploy.yml`.
- Trigger:
- manual (`workflow_dispatch`) with explicit ref;
- automatic for tags `v*`.
- Deploy steps:
1. Checkout selected ref.
2. SSH into production server.
3. `git fetch` + `git checkout <ref>`.
4. `docker compose pull`.
5. `docker compose up -d --build`.
6. `docker compose exec -T bot alembic upgrade head`.

## Required GitHub Secrets
- `PROD_SSH_PRIVATE_KEY`
- `PROD_HOST`
- `PROD_USER`
- `PROD_APP_DIR`

## Release Audit Commands
Use these commands for release notes and incident analysis:

```bash
git log --oneline --decorate --graph -50
git log --pretty=format:"%h %ad %an %s" --date=short -50
git show <tag-or-commit>
```

## Rollback
1. Pick previous stable tag.
2. Run deploy workflow manually with that tag in `ref`.
3. Verify DB migration compatibility before rollback if schema changed.
