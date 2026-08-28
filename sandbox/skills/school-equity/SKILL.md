---
name: school-equity
description: Digital profile and equity risk assessment — bandwidth, device churn, staffing instability, and maturity trajectory.
---

# School Equity — Digital Profile & Equity Risk

Synthesise a digital equity risk profile for a school. Pulls together bandwidth/connectivity constraints, device churn history, staffing instability (itinerant/contract patterns), and maturity trajectory to identify structural disadvantage.

## ⚠️ CRITICAL: Jonathan's Email Access

**DO NOT use `mail.py list --folder jonathan`** — that will fail with HTTP 400.
The ONLY correct way to access Jonathan's email is:
````
python3 /skills/school-360/scripts/personal_mail.py --school "<name>" --full
````
Never use mail.py, never guess folder names, never pass display names as folder IDs.

## ⚠️ OWNERSHIP VERIFICATION (Mandatory — applies to ALL school-* skills)

## Ownership (pre-verified — DO NOT re-check)

## Ownership (from User Profile — DO NOT re-check)

The current user's name and region come from the **User Profile** section of the system prompt.
**Never call owner-check or query region/manager tables**. Proceed directly to data gathering.

## ⚡ Performance Rules

1. **ONE batch call** — `school_data.py school "<name>"` returns device, network, maturity, staffing, budget in parallel
2. **Don't re-read this SKILL.md** if already in context
3. **No ownership check needed** — already hardcoded above
4. **matplotlib** — already installed; never pip install mid-response
5. **No subagents** — direct tool calls only

## When to use

- "Digital profile for [school]"
- "Equity risks at [school]"
- "Is [school] digitally disadvantaged?"
- "Show me the bandwidth and device situation at [school]"
- "Why is [school]'s maturity so low?"

## Execution Steps

> **⚡ PROGRESSIVE REVEAL — output a visible section to the user after EACH numbered step. Never batch everything into one final dump.**

1. **Personal Context (O365) → DISPLAY FIRST**

**This step runs BEFORE ServiceNow. It is the first tool call.**

    python3 /skills/school-360/scripts/personal_context.py --school "<school_name>"

This single call fetches BOTH personal notes AND email in one shot.

**OUTPUT NOW:**
> **📓 Personal Notes**
> [notes.content — relevant section]
>
> **📧 Email Trail** ([emails.count] emails)
> - [date] From [sender]: [subject] — [one-line summary]

If notes unavailable: "⚠️ Notes unavailable"
If no emails: "📧 No email correspondence found."

Then write: _"Fetching ServiceNow data..."_

2. **Fetch all school data in one call → DISPLAY NOW** (returns school profile, network, device, maturity, staffing, budget, compliance):
```bash
python3 /skills/school-360/scripts/school_data.py --instance-id <UUID> school "<school_name>"
```
All subsequent steps use fields from this single JSON response.

   **OUTPUT immediately:**
   > **📊 Digital Equity Profile — [School Name]**
   > Data loaded. Analysing [N] network records, [N] devices, [N] staffing records...

   Then write: _"Analysing connectivity and bandwidth..."_

3. **Network/Bandwidth → DISPLAY NOW** — from `network.data`:
   - Look for: bandwidth_mbps, connection_type, reliability_score, uptime metrics
   - Flag: low bandwidth relative to enrolment, satellite/wireless-only connectivity, poor reliability
   - Calculate: bandwidth per student (bandwidth_mbps ÷ enrolment from `school.data`)

   **OUTPUT immediately:**
   > **🌐 Connectivity** — [bandwidth] Mbps for [enrolment] students ([ratio] Mbps/student). Connection: [type]. Reliability: [score].

   Then write: _"Analysing device fleet..."_

4. **Device Fleet & Churn → DISPLAY NOW** — from `device.data`:
   - Count devices, types, ages
   - Look for churn signals: multiple device batches deployed within short periods (swaps)
   - Flag: 3+ swaps in 3 years = instability; high proportion of aged devices = fleet risk

   **OUTPUT immediately:**
   > **💻 Device Access** — [N] devices across [types]. [Churn assessment]. [Fleet age assessment].

   Then write: _"Analysing maturity trajectory..."_

5. **Maturity Trajectory → DISPLAY NOW** — from `maturity.data`:
   - Look at maturity scores over time periods
   - Determine trend: improving, stagnant, declining
   - Compare to region average if available (from school table aggregate)

   **OUTPUT immediately:**
   > **📈 Digital Capability** — Maturity score: [score]. Trend: [improving/stagnant/declining]. [Comparison to region if available].

   Then write: _"Analysing staffing stability..."_

6. **Staffing Stability → DISPLAY NOW** — from `staffing.data`:
   - Look for: transfers_in_out pattern, high vacancy rate, "itinerant" or contract indicators
   - Flag: unstable transfers, chronic vacancies (especially ICT-related roles)
   - Check across periods if multiple records exist

   **OUTPUT immediately:**
   > **👥 Stability** — [vacancy rate], [transfer pattern], [ICT-specific staffing note].

   Then write: _"Checking budget context..."_

7. **Budget Context → DISPLAY NOW** — query `x_snc_qdoe_erp_budget` (--display-value, --query "schoolLIKE<school>")
   - Look for: IT allocation, variance (over/underspend), funding source
   - Flag: underspend (can't execute), overspend (stretched), or no dedicated IT line

   **OUTPUT immediately:**
   > **💰 Investment** — IT allocation: [amount]. Variance: [over/underspend %]. Funding: [source type].

   Then write: _"Checking compliance impact..."_

8. **Compliance Impact → DISPLAY NOW** — query `x_snc_qdoe_compliance` (--display-value, --query "schoolLIKE<school>")
   - Non-conformances that indicate infrastructure gaps (DNIPS, network standards)

   **OUTPUT immediately:**
   > **⚠️ Compliance** — [N] findings. [Key infrastructure-related non-conformances].

   Then write: _"Calculating equity risk scores and generating radar chart..."_

## Equity Risk Scoring

Assess across 5 equity dimensions (0–5 each, 5 = highest risk):

| Dimension | What drives risk up |
|-----------|-------------------|
| **Connectivity** | Low bandwidth/student, satellite-only, poor reliability, no redundancy |
| **Device Access** | High churn, aged fleet, insufficient ratio (devices:students), frequent swaps |
| **Digital Capability** | Low/declining maturity score, no ICT coordinator, itinerant staff |
| **Stability** | Staff turnover, transfer churn, vacancy rate, leadership changes |
| **Investment** | Budget underspend, no dedicated IT line, reliance on one-off grants |

## 10. Equity Radar Chart → DISPLAY NOW (ALWAYS generate)

After scoring all 5 dimensions, ALWAYS generate a radar/spider chart:

```python
import matplotlib.pyplot as plt
import numpy as np

categories = ['Connectivity', 'Device Access', 'Digital Capability', 'Stability', 'Investment']
scores = [<conn_score>, <device_score>, <capability_score>, <stability_score>, <investment_score>]

angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
scores_plot = scores + [scores[0]]
angles += angles[:1]

fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
ax.set_ylim(0, 5)
ax.set_yticks([1, 2, 3, 4, 5])
ax.set_yticklabels(['1', '2', '3', '4', '5'], fontsize=8)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=10, fontweight='bold')

composite = sum(scores)
color = '#dc3545' if composite >= 18 else '#fd7e14' if composite >= 10 else '#28a745'
ax.plot(angles, scores_plot, 'o-', linewidth=2, color=color)
ax.fill(angles, scores_plot, alpha=0.25, color=color)
ax.set_title(f'Equity Risk — <School Name>\nComposite: {composite}/25', fontsize=13, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig('/tmp/equity-radar.png', dpi=150, bbox_inches='tight')
```

Copy to host and display inline:
```
cat /tmp/equity-radar.png | ssh arc-host 'cat > "$ARC_HOST_HOME/school-equity-radar.png"'
```
Then: `![Equity Radar](/Users/leo.francia/school-equity-radar.png)`

### ⚠️ CHART FAILURE PROTOCOL
If chart generation fails: display ALL equity data/tables first, THEN diagnose. The 3-step method (generate in /tmp → ssh copy to $ARC_HOST_HOME → embed ![alt](path)) has worked many times. Do NOT claim platform limitation. Do NOT try alternative methods. Do NOT make users hunt for files. Fix the specific failing step.

Then write: _"Preparing equity narrative..."_

## Output Format

```
### 📊 Digital Equity Profile — [School Name]

**Overall Equity Risk: [HIGH / MEDIUM / LOW]**

| Dimension | Risk Level | Key Signal |
|-----------|-----------|------------|
| Connectivity | 🔴 HIGH | 25 Mbps for 842 students (0.03 Mbps/student) |
| Device Access | 🟠 MEDIUM | 3 fleet swaps in 3 years, current batch stable |
| Digital Capability | 🟡 LOW-MED | Maturity 58, no dedicated ICT coordinator |
| Stability | 🔴 HIGH | Itinerant principal, 4 vacancies/85 FTE |
| Investment | 🟠 MEDIUM | Budget variance -12%, grant-dependent |

#### Narrative
[2-3 paragraph synthesis explaining the equity story — how these dimensions compound, what the structural barriers are, and what would need to change]

#### Recommendations for Advocacy
1. [Specific resource ask the RM could escalate — e.g. "Bandwidth upgrade from 25→100 Mbps via fibre extension"]
2. [Staffing stability intervention]
3. [Device lifecycle policy adjustment]
```

## Key Insight

This skill exists to answer: **"Is this school structurally disadvantaged in a way that explains its health score — and what can I advocate for?"**

It's not a status report (that's school-360). It's an equity lens — designed to help regional managers make the case for targeted investment in disadvantaged schools.

## Visualization & Display

When producing charts (spider/radar, bar, line) or diagrams (network graphs, evidence chains):

1. **Library**: Use `matplotlib` for charts, `networkx` + `matplotlib` for network/graph diagrams
2. **Render in sandbox**: Generate PNG at 150 DPI, tight layout, transparent background for dark themes
3. **Copy to host workspace**: `cat /tmp/chart.png | ssh arc-host 'cat > "$ARC_HOST_HOME/<filename>.png"'`
4. **Display inline**: Always show with `![Description](/Users/leo.francia/<filename>.png)` — NEVER just give a file path
5. **Auto-install**: If matplotlib/networkx not available, `pip install` silently without asking
6. **Chart style**: Use a clean, professional style (e.g. `plt.style.use('seaborn-v0_8-whitegrid')` or similar). Label axes clearly. Use colour to encode severity (red/amber/green).

## Source Citation (Mandatory)

Every metric in the equity profile MUST cite its source. Regional managers use this to write funding submissions — traceability is non-negotiable. **NEVER show raw table names** — use plain-English labels with clickable links.

- **Per-dimension citation**: Each row links to the record category that evidences it
- **Derived metrics**: When calculating ratios (e.g. bandwidth/student), state both inputs in plain language
- **Trend assertions**: When claiming "3 swaps in 3 years", cite the specific deployments by date

Example row:
```
| Connectivity | 🔴 HIGH | 25 Mbps for 842 students (0.03 Mbps/student) |
Sources: Network Profile (bandwidth: 25 Mbps) · School Enrolment (842 students)
```

Footer format:
```
---
**Sources** (click to open in ServiceNow)
- [Network Profile: Millbrook](https://<instance>.service-now.com/...) — bandwidth, reliability
- Device Fleet: 47 records spanning 2023–2026 (3 refresh cycles identified)
- [Maturity Assessments](https://...) — 4 periods tracked
- [Staffing Record 2026-T1](https://...) — FTE, vacancies, transfers
- [Budget FY2025-26](https://...) — IT allocation, variance
- Compliance: 2 findings ([DNIPS non-conformance](https://...), [Firewall audit](https://...))
```

### URL Format

Use the CSM Configurable Workspace URL for all ServiceNow record links:
```
https://<instance>.service-now.com/now/cwf/agent/record/<table>/<sys_id>
```

For standard platform tables (cases, incidents):
```
https://<instance>.service-now.com/now/cwf/agent/record/sn_customerservice_case/<sys_id>
```

For custom QDOE tables:
```
https://<instance>.service-now.com/now/cwf/agent/record/x_snc_qdoe_<table>/<sys_id>
```