---
name: school-programs
description: Active initiatives/programs at a school — milestones, RAG, ownership, and M2M traversal to linked devices and cases.
---

# School Programs — Initiative-Centric View

Surface active central programs and initiatives touching a school. Supports both "list programs" and "drill into a specific program" (M2M traversal to linked devices, cases, and schools).

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

1. **Mode 1** — `school_data.py school "<name>"` already returns initiatives in one call; no extra query needed
2. **Mode 2/3** — only then query M2M tables (`x_snc_qdoe_m2m_init_device`, `x_snc_qdoe_m2m_init_case`)
3. **Don't re-read this SKILL.md** if already in context
4. **No ownership check needed** — already hardcoded above
5. **No subagents** — direct tool calls only

## When to use

- "What programs are active at [school]?"
- "Central initiatives at [school]"
- "Show me everything linked to [initiative name]"
- "What's the status of the device refresh at [school]?"
- "Which schools are part of [program]?"
- "Has [school] asked about [X] before?"
- "What's the history of [program type] at [school]?"

## Three Modes

> **⚡ PROGRESSIVE REVEAL — output a visible section to the user after EACH numbered step. Never batch everything into one final dump.**

### Mode 1: List Programs for a School

Trigger: "What programs/initiatives are active at [school]?"

1. **Personal Context (O365) → DISPLAY FIRST**

   **This runs BEFORE ServiceNow. It is the first tool call.**

       python3 /skills/school-360/scripts/personal_context.py --school "<school_name>"

   **OUTPUT NOW:**
   > **📓 Notes** — [initiative-relevant notes]
   > **📧 Email** ([count]) — [delivery updates, blockers communicated outside ServiceNow]

   Then write: _"Fetching ServiceNow initiative data..."_

2. **Fetch all school data → DISPLAY NOW** (includes initiatives):
```bash
python3 /skills/school-360/scripts/school_data.py --instance-id <UUID> school "<school_name>"
```

   **OUTPUT immediately:**
   > **📋 Programs & Initiatives — [School Name]**
   > Data loaded: [N] active initiatives found.

   Then write: _"Building initiatives summary..."_

3. **Extract initiatives → DISPLAY NOW** from `initiative.data` in the response
4. **For each initiative**, present:
   - Name, stage, rag_status, milestone, owner
   - Start/end dates (or blank if not set)
   - Whether overdue and by how long
6. **Present as Active Initiatives card → DISPLAY NOW** — use a record_list or structured card format:

   **OUTPUT immediately:**
```
### 📋 Active Programs — [School Name]

| Program | Stage | RAG | Milestone | Owner |
|---------|-------|-----|-----------|-------|
| Enabling Schools — Device Refresh 2026 | in_progress | 🟠 AMBER | Phase 2 due Feb | Marcus Lindqvist |
```

### Mode 2: Drill Into a Program (M2M Traversal)

Trigger: "Show me everything linked to [initiative name] at [school]"

1. **Find the initiative → DISPLAY NOW** — query `x_snc_qdoe_initiative` (--display-value, --query "nameLIKE<initiative>^schoolLIKE<school>")

   **OUTPUT immediately:**
   > **🔗 Drilling into: [Initiative Name]**
   > Stage: [stage] | RAG: [status] | Owner: [name]

   Then write: _"Traversing linked devices..."_

2. **Traverse M2M — Devices → DISPLAY NOW** — query `x_snc_qdoe_m2m_init_device` (--display-value, --query "initiativeLIKE<initiative_name>^ORinitiative=<initiative_sys_id>")
   - For each linked device record, get details from `x_snc_qdoe_device` if needed

   **OUTPUT immediately:**
   > **💻 Linked Devices** — [N] device records linked.
   > [Brief: e.g. "30× Chromebooks deployed 2026-03, 15× pending"]

   Then write: _"Traversing linked cases..."_

3. **Traverse M2M — Cases → DISPLAY NOW** — query `x_snc_qdoe_m2m_init_case` (--display-value, --query "initiativeLIKE<initiative_name>^ORinitiative=<initiative_sys_id>")
   - For each linked case, query `sn_customerservice_case` (--query "number=<case_number>") for state, priority, assigned_to, short_description

   **OUTPUT immediately:**
   > **📁 Linked Cases** — [N] cases connected.
   > [Brief: e.g. "CS0041302 — re-cabling Block B (Open, 45d)"]

   Then write: _"Checking for additional spawned cases..."_

4. **Check for spawned/related cases → DISPLAY NOW** — also query cases directly: `sn_customerservice_case` (--query "short_descriptionLIKE<initiative_keyword>^account.nameLIKE<school>")

   **OUTPUT immediately:**
   > **📁 Related Cases** — [N] additional cases found matching this initiative keyword.

   Then write: _"Checking device fleet state..."_

5. **Check devices deployed → DISPLAY NOW** — query `x_snc_qdoe_device` (--display-value, --query "schoolLIKE<school>") to see fleet state

   **OUTPUT immediately:**
   > **💻 Full Fleet** — [N] devices at [school]. [Types breakdown].

   Then write: _"Building program linkage diagram..."_

## Output Format — Drill-Down

```
### 🔗 Program Linkages: [Initiative Name] — [School]

**Initiative**: [name]
**Stage**: [stage] | **RAG**: [status] | **Overdue**: [yes/no, by how long]
**Owner**: [name]

#### Linked Devices
| Device/Batch | Type | Status | Deployed |
|--------------|------|--------|----------|
| Laptop Batch 2026-Q1 (×30) | Chromebook | Deployed | 2026-03-15 |

#### Spawned Cases
| Case | Description | State | Priority | Owner | Age |
|------|-------------|-------|----------|-------|-----|
| CS0041302 | DNIP re-cabling — Block B | Open | 3-Medium | J. Santos | 45d |

#### Timeline
- 2025-11: Initiative approved
- 2026-01: Device order placed
- 2026-03: Devices deployed (Phase 1)
- 2026-04: Re-cabling case raised (network couldn't support new devices)
- NOW: Phase 2 overdue — awaiting network remediation
```

## Key Tables

- `x_snc_qdoe_initiative` — main initiative records
- `x_snc_qdoe_m2m_init_device` — initiative ↔ device edges
- `x_snc_qdoe_m2m_init_case` — initiative ↔ case edges
- `x_snc_qdoe_device` — device fleet records
- `sn_customerservice_case` — CSM cases

## Notes

- Initiatives may span multiple schools — if the user asks "which schools are part of [program]", query the initiative table without a school filter
- The M2M tables are the key differentiator from school-360 — they reveal the operational edges that a summary view hides
- Always calculate case age (days since sys_created_on) for staleness assessment

## Visualization & Display

When producing initiative linkage diagrams or timelines:

1. **Library**: Use `matplotlib` for timelines, `networkx` + `matplotlib` for linkage graphs
2. **Render in sandbox**: Generate PNG at 150 DPI, tight layout
3. **Copy to host workspace**: `cat /tmp/program-links.png | ssh arc-host 'cat > "$ARC_HOST_HOME/<school-slug>-programs.png"'`
4. **Display inline**: Always show with `![Program Linkages](/Users/leo.francia/<school-slug>-programs.png)` — NEVER just give a file path
5. **Auto-install**: If matplotlib/networkx not available, `pip install` silently without asking
6. **When to render**: Produce a linkage diagram when Mode 2 (drill-down) is triggered and there are 3+ linked records

## Source Citation (Mandatory)

Every initiative, linked device, and spawned case MUST cite its source record. This enables drill-down and verification.

- **Initiative records**: cite `x_snc_qdoe_initiative` with sys_id
- **M2M edges**: cite the junction table (`x_snc_qdoe_m2m_init_device` or `x_snc_qdoe_m2m_init_case`) that proves the link exists
- **Cases**: hyperlink CS* numbers and note state + age
- **Devices**: note batch sys_id from `x_snc_qdoe_device`

Example:
```
#### Spawned Cases
| Case | Description | State | Age |
|------|-------------|-------|-----|
| [CS0041302](https://<instance>.service-now.com/now/cwf/agent/record/sn_customerservice_case/<sys_id>) | DNIP re-cabling — Block B | Open | 45d |
```

Footer format:
```
---
**Sources** (click to open in ServiceNow)
- [Enabling Schools — Device Refresh 2026](https://<instance>.service-now.com/now/cwf/agent/record/x_snc_qdoe_initiative/<sys_id>) — initiative record
- Linked devices: 30 Chromebooks deployed (via initiative-device relationship)
- Linked cases: [CS0041302](https://...) · [CS0041207](https://...)
- Device fleet: 47 records for this school
```

### Mode 3: Historical / Prior Requests

Trigger: "Has [school] asked about [X] before?", "What's the history of device refreshes at [school]?"

This mode surfaces **closed, completed, and cancelled** records — not just active ones. The goal is to show whether a request is a repeat pattern or net-new.

1. **Query historical initiatives** — `x_snc_qdoe_initiative` (--display-value, --query "schoolLIKE<school>^stageLIKEcomplete^ORstageLIKEcancel^ORstageLIKEclosed")
   - Also query without stage filter and show ALL initiatives (active + historical) for context
2. **Query historical cases** — `sn_customerservice_case` (--display-value, --query "short_descriptionLIKE<keyword>^account.nameLIKE<school>") — do NOT filter by state, return all states including Closed/Resolved
3. **Cross-reference principals** — if a prior request was made under a different principal, note this: "Requested under [Previous Principal] in [date]"
4. **Pattern detection** — flag if the same type of request has appeared 2+ times:
   ```
   ⚠️ REPEAT PATTERN: This is the 3rd device refresh request from this school.
   Previously requested: 2023-T2 (Principal: D. Murray), 2024-T4 (Principal: K. Tran)
   ```
5. **Present timeline** showing all related records chronologically, regardless of status:
   ```
   ### 📜 History: [Topic] at [School]
   
   | Date | Type | Description | State | Principal at time |
   |------|------|-------------|-------|-------------------|
   | 2023-06 | Case CS0038901 | Device refresh request | Closed - Denied | D. Murray |
   | 2024-11 | Initiative | Pilot device program | Cancelled | K. Tran |
   | 2026-02 | Case CS0041450 | Senior-school device refresh | Open | T. Whitfield |
   ```

This is critical for check-in prep — it prevents a regional manager from treating a request as new when the school has been asking for years.