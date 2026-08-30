---
name: school-attention
description: Regional school rollup — flags schools by risk, compliance, staffing, sentiment. Use for "which schools need attention" or "portfolio health".
---

# School Attention Report

## Execution — Staggered Display (data shown FIRST, chart shown LAST)

**ALL 5 PHASES ARE MANDATORY. NEVER STOP EARLY.**

**CRITICAL ORDERING RULE:** After each fetch, the VERY NEXT thing you output is the display text for that phase. NO tool calls between a fetch and its display. The radar chart is ALWAYS the final element — never before, never between phases.

### Phase 1 — ServiceNow data (FETCH then DISPLAY immediately)

```bash
PYTHONPATH=/skills/servicenow/scripts python3 /skills/school-attention/scripts/attention_report.py \
  --instance-id <instance-id> --manager "<manager-name>" --skip-notes --skip-email
```

**Single-school mode** (used by school-checkin):
```bash
PYTHONPATH=/skills/servicenow/scripts python3 /skills/school-attention/scripts/attention_report.py \
  --instance-id <instance-id> --manager "<manager-name>" --school "<school-name>" --skip-notes --skip-email
```

This fetches SN data AND generates the radar chart at `/tmp/school-attention-radar.png` as a side-effect. **IGNORE the chart file until Phase 5.** Do NOT copy it, do NOT embed it, do NOT touch it yet.

**→ DISPLAY Phase 1 NOW — write the school summary text into your response BEFORE making any other tool call.**

### Phase 2 — OneNote notes (FETCH then DISPLAY immediately)

```bash
PYTHONPATH=/skills/microsoft365/scripts python3 /skills/school-360/scripts/personal_context.py --all
```

**→ DISPLAY Phase 2 NOW — write notes text BEFORE making any other tool call.**

### Phase 3 — Email (FETCH then DISPLAY immediately)

```bash
PYTHONPATH=/skills/microsoft365/scripts python3 /skills/school-360/scripts/personal_mail.py --all
```

**→ DISPLAY Phase 3 NOW — write email text BEFORE making any other tool call.**

### Phase 4 — Synthesis (no fetch, just DISPLAY)

Write the synthesis paragraph from all data gathered above. No tool call needed.

**→ DISPLAY Phase 4 NOW.**

### Phase 5 — Radar chart (LAST — copy then embed)

This is the FINAL thing in the response. Copy the chart to host and embed EXACTLY ONCE:

```bash
cat /tmp/school-attention-radar.png | ssh arc-host 'cat > "$ARC_HOST_HOME/school-attention-radar.png"'
```

Then embed: `![Portfolio Risk Profile](/Users/leo.francia/school-attention-radar.png)`

**→ DISPLAY Phase 5 NOW. This is the ONLY place the chart appears. Nothing comes after this.**

---

## Display Phase 1 (after Phase 1 fetch)

For EACH school with composite score > 8, show:

```markdown
### 🟠 <School Name>
**Composite Risk: X/25** | Health: <overall_health>

**Key issues:**
- <attention_items, highest priority first>
- <compliance gaps>
- <stalled initiatives with owner + overdue duration>

**Context:**
- Principal: X | ICT: X | Enrolment: X
- Devices: X | Network uptime: X% | Bandwidth: X%
- Survey trend: X → Y (theme: Z)
```

Do NOT show a dimension scores table here — the radar chart in Phase 5 visualises dimensions.

For schools with composite ≤ 8, show a single line:
```
✅ <School Name> — composite X/25, no flags
```

## Display Phase 2 (after Phase 2 fetch — notes)

For EACH flagged school, show:

```markdown
**📝 Personal notes:**
- <note content, last 3 entries>
```

If no notes: `📝 No personal notes on file.`

## Display Phase 3 (after Phase 3 fetch — email)

For EACH flagged school, show:

```markdown
**📧 Recent emails:**
- <date> — <subject> (from <person>)
- ...
```

If no emails: `📧 No recent emails about this school.`

## Display Phase 4 (synthesis)

Write a **Synthesis** paragraph:
- Which school needs the most urgent action and why
- What to do before check-in (escalate, schedule call, prepare data)
- Any positive signals to acknowledge

## Display Phase 5 (radar chart)

Embed the chart image EXACTLY ONCE. No other phase displays the chart.

---

## Rules

1. **NEVER ask "want me to continue?" or "shall I fetch notes?"** — ALL PHASES ARE MANDATORY.
2. **NEVER stop after Phase 1.** If you display Phase 1 without completing all phases, you have FAILED.
3. **NEVER insert a tool call between a fetch and its display.** After Phase 1 fetch completes, the next thing in your response is Phase 1 display TEXT. Not a chart copy. Not another fetch. TEXT.
4. **NEVER present results without the radar chart.** If chart generation fails, say so explicitly — don't silently omit it.
5. **Radar chart is ALWAYS the final element.** If it appears before the synthesis, before notes, or before emails — you have FAILED.
6. The `--manager` param must match the user's display name from their profile.
7. Instance ID: always use the active session value from the system prompt.
8. Chart: `attention_report.py` generates `/tmp/school-attention-radar.png`. Display it ONLY in Phase 5 — copy to host, embed once. Never earlier, never later, never twice.
9. Notes/email use the M365 scripts directly — NEVER re-run attention_report.py for enrichment.
