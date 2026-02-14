# Production Operations

## Scope
This document defines production-level monitoring, logging, and backups.

## Monitoring Config
- Prometheus config: `ops/monitoring/prometheus.yml`
- Targets included:
- `node-exporter` (host metrics)
- `postgres-exporter` (DB metrics)
- `redis-exporter` (Redis metrics)

## Logging Config
- Promtail config: `ops/logging/promtail-config.yml`
- Log source:
- Docker JSON logs from `/var/lib/docker/containers/*/*-json.log`
- Sink:
- Loki endpoint via `LOKI_URL` env var.

## Backups
- Linux backup script: `ops/backup/backup-postgres.sh`
- Linux restore script: `ops/backup/restore-postgres.sh`
- Environment template: `ops/backup/backup.env.example`
- Windows helper: `scripts/backup_postgres.ps1`

## Backup Policy
- Frequency: daily at minimum.
- Retention: 14 days (default, configurable via `RETENTION_DAYS`).
- Backup format: compressed SQL dump (`.sql.gz`).
- Backups must be copied off-host (object storage or another VM).

## Minimum Alert Set
- Bot process not running for > 1 minute.
- Postgres unavailable.
- Redis unavailable.
- Disk usage > 85%.
- Backup not created in last 24h.

## Recovery Drill (Monthly)
1. Pick one recent backup.
2. Restore it to staging DB.
3. Run smoke tests:
- bot starts;
- referral counters read correctly;
- admin panel responds.
4. Record result and recovery time.

## Ownership
- Product owner approves SLA and user-impact priorities.
- Tech owner maintains runbooks, alerts, and backup restoration capability.
