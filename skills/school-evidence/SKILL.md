---
name: school-evidence
description: Trace the evidence chain behind a flagged school issue — graph traversal across compliance, cases, and snapshots.
---

## Quick Start

```bash
python3 /skills/school-evidence/scripts/evidence_chain.py \
    --instance-id <UUID> --school "School Name" [--issue "keyword"]
```

**Output:** JSON with all linked records + `ascii_graph` field for inline rendering.

**NEVER freestyle individual table queries.** This script handles the full traversal:
attention → compliance → case → initiative → devices → network → survey.

## Rendering

Display the `ascii_graph` field in a code block. Do NOT generate matplotlib PNGs for the evidence graph — use the ASCII output which renders inline continuously.

# School Evidence — Issue Graph Traversal

Trace the full evidence chain behind a flagged issue at a school. Follows links across compliance findings, cases, network data, initiatives, and attention items to show HOW records connect.

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

1. **Start with batch call** — `school_data.py school "<name>"` returns compliance + cases + attention in one call
2. **Then targeted M2M queries** only for the specific edges you need to traverse
3. **Don't re-read this SKILL.md** if already in context
4. **No ownership check needed** — already hardcoded above
5. **networkx** — already installed; never pip install mid-response

## When to use

- "Show me the evidence behind [issue] at [school]"
- "Why is [school] flagged for [X]?"
- "Trace the [problem] at [school]"
- "What records support [finding]?"
- "Evidence chain for [school]"

## Execution Steps

> **⚡ PROGRESSIVE REVEAL — output a visible section to the user after EACH numbered step. Never batch everything into one final dump.**

1. **Personal Context (O365) → DISPLAY FIRST**

   **This runs BEFORE ServiceNow. It is the first tool call.**

       python3 /skills/school-360/scripts/personal_context.py --school "<school_name>"

   This single call fetches BOTH personal notes AND email in one shot.

   **OUTPUT NOW:**
   > **📓 Personal Notes** — [notes relevant to this school/issue]
   > **📧 Email Evidence** ([count] emails) — corroborating correspondence
   > - [date] [sender]: [subject] — [one-line relevance to issue]

   If notes unavailable: "⚠️ Notes unavailable"
   If no emails: "📧 No email correspondence found."

   Then write: _"Fetching ServiceNow data..."_

2. **Fetch all school data in one call → DISPLAY NOW** (provides attention, compliance, initiatives, survey, cases):
```bash
python3 /skills/school-360/scripts/school_data.py --instance-id <UUID> school "<school_name>"
```

   **OUTPUT immediately:**
   > **🔍 Evidence Trace — [School Name]**
   > Data loaded: [N] attention items, [N] compliance findings, [N] cases, [N] initiatives.

   Then write: _"Identifying the issue and tracing the evidence chain..."_

3. **Identify the issue → DISPLAY NOW** — from user's query, determine the topic (e.g. "stalled wireless upgrade", "DNIPS non-conformance", "sentiment drop")

   **OUTPUT immediately:**
   > **🎯 Issue Identified:** [topic description] — tracing from attention flag to source records...

4. **Start from the attention item → DISPLAY NOW** — in `attention.data`, find the item matching the topic. Note its `source_table` and `source_record` fields — these point to the originating record.

   **OUTPUT immediately:**
   > **⚠️ Attention Item:** "[attention description]" | Severity: [level] | Source: [source_table]

   Then write: _"Following source link to [source_table]..."_

5. **Follow the source_table link → DISPLAY NOW** (use data already in the batch response where possible):
   - If source = `x_snc_qdoe_compliance` → check `compliance.data` for the finding. Extract `case_ref`.
   - If source = `sn_customerservice_case` → check `cases.data`.
   - If source = `x_snc_qdoe_initiative` → check `initiative.data`.
   - If source = `x_snc_qdoe_health_snapshot` → query separately (not in batch).

   **OUTPUT immediately:**
   > **📄 Source Record:** [record type] — [key details: description, severity/state, case ref if any]

   Then write: _"Chasing cross-references..."_

7. **Chase cross-references → DISPLAY NOW** (only query if not already in batch response):
   - Compliance finding → linked case_ref → already in `cases.data`
   - Initiative → linked cases via `x_snc_qdoe_m2m_init_case` → query separately
   - Initiative → linked devices via `x_snc_qdoe_m2m_init_device` → query separately
   - Case → calculate age (days since sys_created_on)

   **OUTPUT immediately:**
   > **🔗 Cross-References Found:**
   > - [Record type]: [description] | [state/age]
   > - [Record type]: [description] | [state/age]

   Then write: _"Gathering corroborating records..."_

8. **Corroborating records → DISPLAY NOW** (already in batch response):
   - `survey.data` — sentiment data mentioning the theme
   - `x_snc_qdoe_network` — network snapshot data if issue is infrastructure-related
   - `x_snc_qdoe_health_snapshot` — overall health record

   **OUTPUT immediately:**
   > **📊 Corroboration:**
   > - Survey: [sentiment score, theme match]
   > - Network: [relevant data if infrastructure issue]
   > - Health: [overall health context]

   Then write: _"Building evidence chain diagram..."_

## Output Format — Evidence Graph

Present as a visual chain showing how records connect:

```
### 📊 Evidence Chain: [Issue Title] — [School Name]

┌─────────────────────────────────────────┐
│ ATTENTION ITEM (HIGH)                   │
│ "Escalate stalled wireless upgrade"     │
│ Source: x_snc_qdoe_compliance           │
└──────────────────┬──────────────────────┘
                   │ links to
┌──────────────────▼──────────────────────┐
│ COMPLIANCE FINDING                      │
│ Network infrastructure (DNIPS)          │
│ Severity: HIGH | Status: Non-compliant  │
│ Case ref: CS0041207                     │
└──────────────────┬──────────────────────┘
                   │ case ref
┌──────────────────▼──────────────────────┐
│ CSM CASE: CS0041207                     │
│ "Wireless capacity upgrade"             │
│ State: New | Age: 410 days              │
│ Priority: 2-High | Owner: M. Lindqvist  │
└──────────────────┬──────────────────────┘
                   │ related initiative
┌──────────────────▼──────────────────────┐
│ INITIATIVE                              │
│ Wireless Capacity Upgrade (Metro Refresh)│
│ RAG: AMBER | Overdue: ~3 years          │
│ Stage: In Progress (stalled)            │
└─────────────────────────────────────────┘

CORROBORATING:
• Survey 2026-T1: sentiment 3.1, theme "network reliability"
• Survey 2025-T4: sentiment 3.8 (drop of 0.7)
```

**Do NOT generate matplotlib/networkx PNGs for the evidence graph.** Use the ASCII box diagram above — it renders inline without crashes or alignment bugs.

## Analysis

After presenting the evidence chain, provide:
1. **Root cause assessment** — what's actually broken (person, process, or resource)
2. **Duration of impact** — how long has this been festering
3. **Escalation recommendation** — who needs to act and by when

## Source Citation (Mandatory)

The evidence chain IS the citation — but present it in human language with clickable links, NEVER raw table names.

**Every node in the chain** must show:
- A plain-English label (e.g. "Compliance Finding", "CSM Case")
- The key identifying field (case number, finding title, initiative name)
- A clickable link: `[CS0041207](https://<instance>.service-now.com/now/cwf/agent/record/sn_customerservice_case/<sys_id>)`
- Age/duration where relevant (days since created)

**Edge labels** should read naturally: "raised because of", "linked to", "spawned case", "corroborated by"

Example node:
```
┌─────────────────────────────────────────┐
│ 📋 Compliance Finding                   │
│ Network infrastructure conformance (DNIPS)│
│ Severity: HIGH | Status: Non-compliant  │
│ Raised: 2025-03-12 (530 days ago)       │
│ → Linked case: CS0041207                │
│ 🔗 Open in ServiceNow                   │
└─────────────────────────────────────────┘
```

**Footer** — clickable record list:
```
---
**Evidence Trail** (click to open in ServiceNow)
1. [Attention Flag: "Escalate stalled wireless upgrade"](https://...)
2. [Compliance Finding: DNIPS non-conformance](https://...)
3. [Case CS0041207: Wireless capacity upgrade](https://...) — 410 days old
4. [Initiative: Wireless Capacity Upgrade (Metro Refresh)](https://...) — overdue ~3 years
5. Staff Survey 2026-T1 — sentiment 3.1 (theme: "network reliability")
```