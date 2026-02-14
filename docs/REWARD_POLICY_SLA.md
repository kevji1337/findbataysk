# Reward Claims Policy And SLA

## Purpose
Define formal rules for referral reward claims and admin processing timelines.

## Claim Lifecycle
- `pending`: claim is received and waits for admin review.
- `approved`: reward is confirmed and issued.
- `rejected`: claim is denied with reason.

## Eligibility Rules
- User must have a valid referral link.
- Claim amount is based on current referral rules (`REFERRALS_PER_GIFT`).
- Duplicate processing of the same claim is forbidden.
- Every decision must be logged with admin ID and timestamp.

## Mandatory Decision Data
- Claim ID
- User ID
- Requested reward count
- Final status (`approved` / `rejected`)
- Admin ID
- Decision timestamp
- Reason (required for reject)

## SLA
- First response to claim: <= 12 hours.
- Final decision for standard cases: <= 24 hours.
- Peak periods / incidents: <= 48 hours (must be announced in admin channel).
- Claims older than SLA are escalated automatically to owner.

## Escalation Matrix
- 0-24h: primary admin handles queue.
- 24-48h: secondary admin is assigned.
- >48h: owner escalation and incident report.

## Anti-Abuse Rules
- Repeated suspicious claim attempts can be temporarily frozen.
- Freeze must include reason and expiration time.
- Frozen claim must still receive final decision within incident SLA.

## Communication Policy
- On `pending`: user gets "claim received".
- On `approved`: user gets "claim approved" + fulfillment details.
- On `rejected`: user gets reason and re-apply conditions.

## Audit And Reporting
- Weekly report:
- claims created / approved / rejected;
- median and p95 processing time;
- count of SLA breaches and reasons.
