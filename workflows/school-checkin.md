---
name: school-checkin
description: Brief on a specific school before a monthly check-in — pulls live data, verifies ownership, and produces talking points and follow-up actions.
created_by: agent
---

## ⚠️ CRITICAL: Jonathan's Email Access

**DO NOT use `mail.py list --folder jonathan`** — that will fail with HTTP 400.
The ONLY correct way to access Jonathan's email is:
````
python3 /skills/school-360/scripts/jonathan_mail.py --school "<name>" --full
````
Never use mail.py, never guess folder names, never pass display names as folder IDs.

1. **Ownership verification** (silent): Identify the logged-in user from User Profile. Check if they manage the school. If NOT the owner, ask about delegated authority. If they ARE, proceed silently.

---

**⚡ PROGRESSIVE REVEAL — output after EACH step, not at the end.**

---

### Step 2: Personal Context (O365) → DISPLAY FIRST

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

3. **ServiceNow school data → DISPLAY NOW**
   Query `x_snc_qdoe_school` (--display-value, --query "nameLIKE<school_name>") for: name, overall_health, digital_maturity_score, sentiment_score, active_risk_count, enrolment_count, principal, ict_coordinator, manager, region.

   **OUTPUT** a quick summary card:
   > **🏫 [School Name]** | Health: [emoji] | Maturity: X | Sentiment: X (↑/↓)
   > Principal: X | Enrolment: X | Risks: X

   Then write: _"Pulling compliance, staffing, and initiatives..."_

4. **Supporting ServiceNow data → DISPLAY NOW**
   Pull all (with --display-value, filtered by school):
   - `x_snc_qdoe_compliance` — findings, severity, cases
   - `x_snc_qdoe_staffing` — FTE, vacancies, transfers
   - `x_snc_qdoe_survey` — sentiment across periods, themes
   - `x_snc_qdoe_initiative` — all initiatives, RAG status
   - `x_snc_qdoe_attention` — flagged items with priority
   - Resolve open cases (CS* numbers → `sn_customerservice_case`)

   **OUTPUT** each category as a compact section:
   > **📋 Compliance** — N findings (high/medium/low)
   > **👥 Staffing** — X FTE, Y vacancies
   > **📊 Sentiment** — X → Y (trend), theme: "..."
   > **🚀 Initiatives** — N active, M overdue
   > **⚠️ Attention** — N flags

   Then write: _"Generating risk chart..."_

5. **Radar Chart → DISPLAY NOW**
   Generate the chart using the SAME script as the portfolio view, filtered to one school:

   ```bash
   PYTHONPATH=/skills/servicenow/scripts python3 /skills/school-attention/scripts/attention_report.py \
     --instance-id <instance-id> --manager "<manager-name>" --school "<school_name>" --skip-notes --skip-email
   ```

   This produces `/tmp/school-attention-radar.png` using `score_school()` (Risk, Compliance, Staffing, Sentiment, Initiatives — 0-5 scale). Same dimensions and scoring as the portfolio radar.

   Copy to host:
   ```bash
   cat /tmp/school-attention-radar.png | ssh arc-host 'cat > /Users/leo.francia/school-attention-radar.png'
   ```

   Embed the chart EXACTLY ONCE — here and nowhere else in the entire response:
   ```markdown
   ![Risk Profile](/Users/leo.francia/school-attention-radar.png)
   ```

   ⚠️ DO NOT write your own matplotlib code. DO NOT embed the image a second time anywhere.

   Then write: _"Bringing it all together..."_

6. **Synthesis + Talking Points → DISPLAY NOW**
   Connect dots across ALL sources. Identify dominant issues and causal chains:
   - Stalled initiative → compliance failure → sentiment drop
   - Staffing gaps → workload pressure → sentiment drop
   - Multiple risks compounding → overall health decline

   **OUTPUT:**
   > **🔍 The Story**
   > [2-3 sentences connecting ServiceNow + notes + emails into a narrative]
   >
   > **🎯 Talking Points**
   > 1. [What to open with]
   > 2. [What to ask about]
   > 3. [What commitment to make]
   > 4. [Follow-up action]
   > 5. [Next step]

7. **Offer next steps**: Ask if the user wants to (a) draft an email chasing a blocker, (b) schedule a follow-up reminder, (c) log a work note on an open case, or (d) add a note to the School360 notebook.