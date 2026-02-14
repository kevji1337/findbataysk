# Load Testing (Locust)

## Scope
Load test for bot menu handlers with latency metrics (p95/p99).

## Files
- Scenario: `loadtests/locustfile.py`
- Load deps: `requirements-loadtest.txt`

## Install
```bash
pip install -r requirements-loadtest.txt
```

## Run Headless (150 concurrent users)
```bash
locust -f loadtests/locustfile.py --headless -u 150 -r 50 -t 2m --csv loadtest_menu
```

## What Is Measured
- Request groups:
- `back_to_menu`
- `cancel_action`
- `leaderboard`
- Metrics:
- RPS
- error rate
- median, p95, p99 latency

## Notes
- This scenario tests handler execution path without Telegram network.
- For comparison between commits, keep `-u`, `-r`, and `-t` fixed.
