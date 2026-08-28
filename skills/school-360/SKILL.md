---
name: school-360
description: Full 360-degree school profile — identity, contacts, health, sentiment trends, staffing, compliance, and initiatives. Use when asked to "brief me on [school]", "school summary", or "school profile".
---

# School 360 — Full School Profile

Produce a comprehensive 360-degree brief for a single school before a check-in.

## ⚠️ CRITICAL: Jonathan's Email Access

**DO NOT use `mail.py list --folder jonathan`** — that will fail with HTTP 400.
The ONLY correct way to access Jonathan's email is:
```
python3 /skills/school-360/scripts/personal_mail.py --school "<name>" --full
```
Never use mail.py, never guess folder names, never pass display names as folder IDs.

## Ownership (DO NOT re-check)

The current user (from User Profile section in system prompt) manages their region.
**Never call owner-check or query region/manager tables** — proceed directly to data gathering.
Use the user's **full display name** from the User Profile for `--manager` flags.

## ⚡ Performance Rules

1. **ONE batch call** — always use `school_data.py` instead of sequential query_table.py calls
2. **Don't re-read this SKILL.md** if already in context from a prior turn
3. **No ownership check needed** — already verified from User Profile
4. **matplotlib/networkx** — may need `pip install` on fresh sandbox; do it silently
5. **No subagents** for single-school lookups — direct tool calls only

## 🗂️ Sandbox Filesystem & Import Rules

```
ACTUAL PATH IN SANDBOX:  /sandbox/skills/...
SYMLINK SHORTCUT:        /skills/...  (same thing)

Key config modules:
  /skills/servicenow/scripts/config.py   → get_servicenow_config(), make_request()
  /skills/microsoft365/scripts/config.py  → get_access_token(), graph_request()

School scripts:
  /skills/school-360/scripts/school_data.py       → imports from servicenow config
  /skills/school-360/scripts/personal_mail.py     → imports from microsoft365 config
  /skills/school-360/scripts/personal_context.py  → imports from microsoft365 config
```

**Python's default sys.path does NOT include any skill script directory.**
When running school_data.py directly (not via attention_report.py), prefix:
```bash
PYTHONPATH=/skills/servicenow/scripts python3 /skills/school-360/scripts/school_data.py --instance-id <UUID> school "<name>"
```

For personal_mail.py and personal_context.py (M365 scripts):
```bash
python3 /skills/school-360/scripts/personal_mail.py --school "<name>"
```
(These insert their own M365 path internally — no PYTHONPATH needed unless also importing SN config.)

**DO NOT `cd` into /skills/<x>/scripts/** — the sandbox path interceptor may block it.
Always use PYTHONPATH or absolute paths.

## When to use

- "Brief me on [school] before my check-in"
- "School 360 for [school]"
- "Tell me about [school]"
- "School profile [school]"
- Any `/school-checkin` workflow trigger

## Script

**Single-call batch fetch** (replaces 6-8 sequential queries):
```bash
python3 /skills/school-360/scripts/school_data.py --instance-id <UUID> school "<school_name>"
```

Returns JSON with keys: `school`, `compliance`, `staffing`, `survey`, `initiative`, `attention`, `device`, `network`, `maturity`, `erp_budget`, `cases` — all fetched in parallel.

## ⚠️ REQUIRED DATA SOURCES — all three MUST be attempted every time

Every school-360 brief MUST pull from all three sources. Do NOT skip any.
If one fails, report the failure in the output — never silently omit it.

| # | Source | Method | Failure handling |
|---|--------|--------|-----------------|
| A | **Personal notes** (OneDrive MD) | Graph API content endpoint | Report "notes unavailable" |
| B | **Personal email** (mail folder) | `personal_mail.py` | Report "no emails found" |
| C | **ServiceNow QDOE data** | `school_data.py` | Report "SN data unavailable" |

## Execution Steps — PROGRESSIVE REVEAL

**Critical UX rule:** Output a visible section to the user AFTER EACH step completes.
Do NOT batch all data and present one giant block at the end.
Each step = fetch + render. The user sees results building up in stages.

---

### Step 1: Personal Context (O365) → DISPLAY FIRST

**This step runs BEFORE ServiceNow. It is the first tool call.**

```
python3 /skills/school-360/scripts/personal_context.py --school "<school_name>"
```

This single call fetches BOTH personal notes AND email in one shot.

**OUTPUT NOW** — render both immediately:
> **📓 Personal Notes**
> [notes.content — TODOs, observations, meeting notes from the matching section]
>
> **📧 Email Trail** ([emails.count] emails)
> - [date] From [sender]: [subject] — [one-line body summary]
> - [date] From [sender]: [subject] — [one-line body summary]

If notes unavailable: "⚠️ Notes: unavailable (token expired)"
If no emails: "📧 No email correspondence found for this school."

Then write: _"Fetching ServiceNow data..."_

---

### Step 2: ServiceNow data → DISPLAY IMMEDIATELY
Run `school_data.py --instance-id <UUID> school "<school_name>"`.

**OUTPUT NOW** — render a `record_detail` UI block with:
- **Identity**: name, code, type, sector, region, enrolment
- **Key Contacts**: principal, ICT coordinator, regional manager
- **Health & Maturity**: overall_health, digital_maturity_score, health_status
- **Sentiment**: current score, previous score, trend arrow, theme
- **Staffing**: FTE, vacancies, transfer stability
- **Compliance**: findings list with severity
- **Active Initiatives**: name, RAG, overdue status
- **Attention Items**: prioritised list

Then write: _"Synthesizing..."_

---

### Step 3: Synthesis + Talking Points → DISPLAY
Connect the dots across all three sources.

**OUTPUT NOW:**
> **🔍 Synthesis**
> [2-4 sentences connecting ServiceNow data + notes + emails into a coherent narrative]
>
> **🎯 Talking Points for Check-in**
> 1. [point derived from combined data]
> 2. [point derived from combined data]
> 3. [point derived from combined data]

---

### Step 4: Spider/Radar Chart → DISPLAY IMMEDIATELY

**MANDATORY** — always generate a radar chart for the school's dimensional profile.

Plot these 5 dimensions on a radar (0–5 scale, higher = worse/more risk):
- **Compliance** — derived from compliance_score or finding severity count
- **Staffing** — vacancies, FTE gaps, stability score inverted
- **Sentiment** — community_sentiment inverted (low sentiment = high risk)
- **Health** — overall_health mapped (red=5, amber=3, green=1)
- **Initiatives** — overdue or at-risk initiative count

**Copy-paste recipe:**
```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

categories = ['Staffing', 'Compliance', 'Initiatives', 'Health', 'Sentiment']
N = len(categories)
angles = [n / float(N) * 2 * np.pi for n in range(N)]
angles += angles[:1]  # close

scores = [staffing_risk, compliance_risk, initiative_risk, health_risk, sentiment_risk]  # each 0-5
values = scores + scores[:1]

fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
ax.set_theta_offset(np.pi / 2)   # first axis at top (12 o'clock)
ax.set_theta_direction(-1)        # clockwise
ax.plot(angles, values, linewidth=2, color='#e74c3c', marker='o')
ax.fill(angles, values, alpha=0.15, color='#e74c3c')
ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=12, fontweight='bold')
ax.set_ylim(0, 5)
ax.set_yticks([1, 2, 3, 4, 5])
ax.set_yticklabels(['1', '2', '3', '4', '5'], fontsize=8)
ax.text(0.5, 0.92, 'High risk', transform=ax.transAxes, fontsize=8, color='#e74c3c', ha='center')
ax.text(0.5, 0.12, 'Low risk', transform=ax.transAxes, fontsize=8, color='green', ha='center')
plt.title(f'{school_name} — Risk Profile', fontsize=14, fontweight='bold', pad=24)
plt.tight_layout()
plt.savefig('/tmp/school-radar.png', dpi=150, bbox_inches='tight')
```

Then copy to host workspace and display inline using markdown image syntax:
```bash
cat /tmp/school-radar.png | ssh arc-host 'cat > "$ARC_HOST_HOME/school-radar.png"'
```

**DISPLAY INLINE — MANDATORY:**
```markdown
![School Name — Risk Profile](/Users/leo.francia/school-radar.png)
```

⚠️ **NEVER** just state "saved to ~/Desktop/file.png" or give a file path without the markdown image embed.
The image MUST appear inline in the chat response using `![alt](path)` syntax.
The user cannot and will not hunt for files.

If scores are unavailable for a dimension, use 0 (unknown) — do NOT skip the chart entirely.

## ⚠️ CHART FAILURE PROTOCOL

This chart method has worked dozens of times. If it fails:
1. DO NOT claim it's a platform limitation. It isn't.
2. DO NOT try base64 data URIs, ui:start chart blocks, or any other method.
3. DO NOT block the entire response on chart failure — display ALL school data first.
4. Diagnose AFTER the user has their data. The three steps are:
   - Generate PNG in sandbox `/tmp/`
   - `cat /tmp/file.png | ssh arc-host 'cat > "$ARC_HOST_HOME/filename.png"'`
   - Embed `![alt](/Users/leo.francia/filename.png)` in response
5. If any step fails, report WHICH step failed and the exact error. Fix it. Do not invent excuses.
6. Users do not hunt for files. A chart saved to Desktop without inline display is a FAILED delivery — not a result, a chore.

---

**SUMMARY: The user MUST see 4-5 distinct output blocks appearing progressively, NOT one monolithic wall of text at the end.**

## Source Citation (Mandatory)

Every response MUST end with a **Sources** section using human-readable labels and clickable links. NEVER show raw table names (e.g. `x_snc_qdoe_compliance`) to the user — they are internal identifiers.

**Rules:**
1. Use plain-English labels: "School Profile", "Staff Survey", "Compliance Finding", "Support Case", etc.
2. Link records to their ServiceNow workspace URL where a sys_id or case number is available
3. Include record count and key qualifier (period, severity, priority) for context
4. Case numbers are ALWAYS hyperlinked

**Example footer:**
```
---
**Sources**
• [School Profile](https://<instance>.service-now.com/now/cwf/agent/record/x_snc_qdoe_school/<sys_id>)
• Staff Surveys — 2 periods (2025-T4, 2026-T1)
• Staffing Record — period 2026-T1
• Compliance Finding — 1 finding, severity: high
• Initiative — "Wireless Capacity Upgrade (Metro Refresh)"
• Attention Flag — 1 item, priority: high
• [Case CS0041207](https://<instance>.service-now.com/now/cwf/agent/record/sn_customerservice_case/<sys_id>) — Priority 2, State: New
```

**URL format** (always use Configurable Workspace):
`https://<instance>.service-now.com/now/cwf/agent/record/<table>/<sys_id>`

Replace `<instance>` with the active instance URL from the session.