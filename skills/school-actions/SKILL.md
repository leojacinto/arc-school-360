---
name: school-actions
description: Recommended actions for a school — prioritised from attention items, compliance gaps, and overdue initiatives.
---

# School Actions — Recommended Actions Card

Surface prioritised recommended actions for a specific school, drawn from attention items, compliance findings, overdue initiatives, and sentiment triggers.

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

1. **ONE batch call** — use `school_data.py school "<name>"` (returns attention, compliance, initiatives, cases)
2. **Don't re-read this SKILL.md** if already in context
3. **No ownership check needed** — already hardcoded above
4. **No subagents** — direct tool calls only

## When to use

- "What are the recommended actions for [school]?"
- "What should I do about [school]?"
- "Action items for [school]"
- "Next steps for [school]"

## Execution Steps

> **⚡ PROGRESSIVE REVEAL — output a visible section to the user after EACH numbered step. Never batch everything into one final dump.**

### Step 1: Personal Context (O365) → DISPLAY FIRST

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

2. **Fetch all data in one call → DISPLAY NOW**:
```bash
python3 /skills/school-360/scripts/school_data.py --instance-id <UUID> school "<school_name>"
```
This returns: school, compliance, staffing, survey, initiative, attention, cases — all in parallel.

   **OUTPUT immediately:**
   > **🚨 Actions Brief — [School Name]**
   > Loading data... found [N] attention flags, [N] compliance findings, [N] overdue initiatives.

   Then write: _"Analysing and prioritising actions..."_

3. **From the response**, extract:
   - `attention.data` → PRIMARY source of recommended actions
   - `compliance.data` → where status=non_compliant. No linked case → "Raise a case". Stale case → "Chase owner".
   - `initiative.data` → where milestone contains "overdue" or rag_status in (red, amber). Recommend escalation.
   - `survey.data` → declining trend → recommend engagement action.
   - `staffing.data` → vacancies > 5% of FTE → recommend staffing review.
   - `cases.data` → resolve state/owner for linked cases.

## Prioritisation Logic

Rank actions by:
1. **Critical** (do this week): HIGH attention items + RED compliance + overdue >1yr initiatives
2. **Important** (do this month): MEDIUM attention + AMBER compliance + overdue <1yr
3. **Monitor** (next check-in): LOW attention + sentiment watch + minor staffing

## Output Format

Present as a structured card:

```
### 🚨 Recommended Actions — [School Name]

#### Critical (This Week)
1. **[Action title]** — [Source: attention/compliance/initiative] | Owner: [X] | Case: [CS*]

#### Important (This Month)  
2. **[Action title]** — ...

#### Monitor (Next Check-In)
3. **[Action title]** — ...
```

For each action, include:
- What to do (specific, actionable verb)
- Who owns it currently
- What case/record it links to
- What "done" looks like

Offer to: (a) draft an email to the owner, (b) update the case with a work note, (c) set a reminder to follow up.

## Source Citation (Mandatory)

Every recommended action MUST cite its evidence as a clickable trail. NEVER show raw table names to the user.

**Per-action citation** — trace the logic chain in plain English with linked records:
```
#### Critical (This Week)
1. **Escalate stalled wireless upgrade** — Chase Marcus Lindqvist for revised delivery date
   _Evidence: Attention Flag (high) → Compliance Finding (DNIPS, high severity) → [Case CS0041207](https://<instance>.service-now.com/now/cwf/agent/record/sn_customerservice_case/<sys_id>) (New, 410 days old)_
```

**Footer:**
```
---
**Sources**
• Attention Flags — 1 high-priority item
• Compliance Findings — 1 non-compliant (DNIPS)
• Active Initiatives — 1 overdue (~3 years)
• [Case CS0041207](https://...) — Priority 2, State: New
• Staff Surveys — declining trend detected (3.8 → 3.1)
```

**URL format**: `https://<instance>.service-now.com/now/cwf/agent/record/<table>/<sys_id>`