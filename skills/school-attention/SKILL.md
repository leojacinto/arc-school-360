---
name: school-attention
description: Regional school rollup — flags schools by risk, compliance, staffing, sentiment. Use for "which schools need attention" or "portfolio health".
---

# School Attention Report

## Execution — 2 Mandatory Calls (Staggered Display)

**BOTH CALLS ARE MANDATORY. NEVER STOP AFTER CALL 1.**

### Call 1 — ServiceNow data + radar chart (fast ~5s)

```bash
PYTHONPATH=/skills/servicenow/scripts python3 /skills/school-attention/scripts/attention_report.py \
  --instance-id <instance-id> --manager "<manager-name>" --skip-notes --skip-email
```

**Single-school mode** (used by school-checkin — produces the SAME chart with identical dimensions/scoring):
```bash
PYTHONPATH=/skills/servicenow/scripts python3 /skills/school-attention/scripts/attention_report.py \
  --instance-id <instance-id> --manager "<manager-name>" --school "<school-name>" --skip-notes --skip-email
```

This fetches SN data AND generates the radar chart at `/tmp/school-attention-radar.png`.

Then IMMEDIATELY PROCEED to Call 2. Do NOT copy or display the chart yet — that happens in Phase 1 display below.

### Call 2 — Notes + Email enrichment (~15s)

Call the M365 scripts directly — do NOT re-run the orchestrator:

```bash
PYTHONPATH=/skills/microsoft365/scripts python3 /skills/school-360/scripts/personal_mail.py --all
```

```bash
PYTHONPATH=/skills/microsoft365/scripts python3 /skills/school-360/scripts/personal_context.py --all
```

Display Phase 2 results, then write the Synthesis.

---

## Display Phase 1 (after Call 1)

For EACH school with composite score > 8, show:

```markdown
### 🟠 <School Name>
**Composite Risk: X/25** | Health: <overall_health>

| Dimension | Score | Flag |
|-----------|-------|------|
| Risk | X/5 | ⚠️ if ≥3 |
| Compliance | X/5 | ⚠️ if ≥3 |
| Staffing | X/5 | ⚠️ if ≥3 |
| Sentiment | X/5 | ⚠️ if ≥3 |
| Initiatives | X/5 | ⚠️ if ≥3 |

**Key issues:**
- <attention_items, highest priority first>
- <compliance gaps>
- <stalled initiatives with owner + overdue duration>

**Context:**
- Principal: X | ICT: X | Enrolment: X
- Devices: X | Network uptime: X% | Bandwidth: X%
- Survey trend: X → Y (theme: Z)
```

**Chart display** — handled by the calling workflow (`/schools-attention` or `/school-checkin`). Those workflows specify exactly where to copy+embed. Do NOT embed the chart from this SKILL.md — the workflow already does it once. If you embed here AND in the workflow, it appears twice.

For schools with composite ≤ 8, show a single line:
```
✅ <School Name> — composite X/25, no flags
```

## Display Phase 2 (after Call 2)

For EACH flagged school, append:

```markdown
**📧 Recent emails** (last 30 days):
- <date> — <subject> (from/to <person>)
- ...

**📝 Personal notes:**
- <note content, last 3 entries>
```

If no emails: `📧 No recent emails about this school.`
If no notes: `📝 No personal notes on file.`

Then write a **Synthesis** paragraph:
- Which school needs the most urgent action and why
- What to do before check-in (escalate, schedule call, prepare data)
- Any positive signals to acknowledge

---

## Rules

1. **NEVER ask "want me to continue?" or "shall I fetch notes?"** — BOTH CALLS ARE MANDATORY.
2. **NEVER stop after Call 1.** If you display Phase 1 without executing Call 2, you have FAILED.
3. **NEVER present results without the radar chart.** If chart generation fails, say so explicitly — don't silently omit it.
4. The `--manager` param must match the user's display name from their profile.
5. Instance ID: always use the active session value from the system prompt.
6. Chart: `attention_report.py` generates `/tmp/school-attention-radar.png`. The calling workflow (`/schools-attention` or `/school-checkin`) handles copy-to-host and embed. The `![Attention Radar]` markdown appears EXACTLY ONCE in the entire response — only where the workflow specifies. Never earlier, never later, never twice.
7. Notes/email use the M365 scripts directly — NEVER re-run attention_report.py for enrichment.
