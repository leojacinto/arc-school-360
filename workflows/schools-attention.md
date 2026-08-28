---
name: schools-attention
description: Pull fresh QDOE school data from ServiceNow, flag schools by risk/compliance/staffing/sentiment, and produce a prioritised check-in brief with spider chart.
created_by: agent
---

## ⚠️ CRITICAL: Jonathan's Email Access

**DO NOT use `mail.py list --folder jonathan`** — that will fail with HTTP 400.
The ONLY correct way to access Jonathan's email is:
````
python3 /skills/school-360/scripts/jonathan_mail.py --school "<name>" --full
````
Never use mail.py, never guess folder names, never pass display names as folder IDs.

## ⚡ PROGRESSIVE REVEAL — output a visible section to the user after EACH numbered step. Never batch everything into one final dump.

1. **Identify user portfolio → DISPLAY NOW**
   Query `x_snc_qdoe_region` (--display-value) to find which region(s) the user manages. Then query `x_snc_qdoe_school` filtered by that region's sys_id (--query "region=<sys_id>") to get their full school portfolio. If only one school is found, also try querying by manager field. Collect: name, overall_health, digital_maturity_score, sentiment_score, active_risk_count, enrolment_count, principal, ict_coordinator.

   **OUTPUT immediately:** Table of all schools with health/score columns.
   Then write: _"Fetching compliance, staffing, and sentiment data..."_

2. **Detailed data per school → DISPLAY NOW**
   For each school in the portfolio, query the following tables (all with --display-value, filtered by school name or sys_id):
   - `x_snc_qdoe_compliance` — find non-compliant findings, note severity and linked case refs
   - `x_snc_qdoe_staffing` — check vacancies, FTE, transfers
   - `x_snc_qdoe_survey` — get sentiment scores across periods, note declining trends and themes
   - `x_snc_qdoe_initiative` — find overdue or amber/red RAG initiatives
   - `x_snc_qdoe_attention` — get flagged attention items with priority

   **OUTPUT immediately:** Summary of findings per school (bullet points).
   Then write: _"Checking personal notes and email trail..."_

3. **[MANDATORY] Personal Context (O365) → DISPLAY NOW**

       python3 /skills/school-360/scripts/personal_context.py --all

   This SINGLE call fetches BOTH personal notes AND email for ALL schools.

   **OUTPUT immediately:**
   > **📓 Personal Notes** — relevant excerpts per flagged school
   > **📧 Email Trail** — emails cross-referenced with flagged schools, sorted by date

   If unavailable, state "⚠️ Personal context unavailable" — do NOT silently omit.
   Then write: _"Resolving open cases..."_

4. **Resolve case references → DISPLAY NOW**
   For any case references (CS* numbers) found in compliance or attention data, query `sn_customerservice_case` (--query "number=<case_number>") to get case state, priority, and assigned owner.

5. **Score and rank → DISPLAY NOW**
   Score each school using these dimensions (1-5 scale, 5 = worst):
   - **Risk**: active_risk_count (0=1, 1=2, 2-3=3, 4=4, 5+=5)
   - **Compliance**: count of non-compliant findings × severity weight (high=2, medium=1, low=0.5)
   - **Staffing**: vacancy ratio vs FTE, instability of transfers
   - **Sentiment**: raw score inverted (≤2.0=5, 2.1-2.5=4, 2.6-3.0=3, 3.1-3.5=2, 3.6+=1), bonus +1 if declining trend
   - **Initiative Health**: count of overdue/amber/red initiatives

   **OUTPUT immediately:** Ranked table with composite scores.
   Then write: _"Generating spider chart..."_

6. **Spider/Radar Chart → DISPLAY NOW (ALWAYS generate, even for 1 school)**
   Run `attention_report.py` to generate the chart (it uses the same scoring dimensions and `generate_radar()` function every time):
   ```bash
   PYTHONPATH=/skills/servicenow/scripts python3 /skills/school-attention/scripts/attention_report.py \
     --instance-id <instance-id> --manager "<manager-name>" --skip-notes --skip-email
   ```
   Chart outputs to `/tmp/school-attention-radar.png`. Copy to host:
   ```bash
   cat /tmp/school-attention-radar.png | ssh arc-host 'cat > /Users/leo.francia/school-attention-radar.png'
   ```
   Embed EXACTLY ONCE — here and nowhere else:
   ```markdown
   ![Attention Radar](/Users/leo.francia/school-attention-radar.png)
   ```
   DO NOT write your own matplotlib code. DO NOT embed the image a second time anywhere else in the response.

   Then write: _"Preparing recommendations..."_

7. **Prioritised summary → DISPLAY NOW**
   - Sort schools by composite score (sum of all dimensions), highest first
   - For RED health schools: full detail block with all issues, open cases, and recommended talking points
   - For AMBER schools with score ≥ 12: condensed issue summary
   - For remaining AMBER schools: one-line mention
   - GREEN schools: omit unless they have a HIGH attention item

8. **Talking points → DISPLAY NOW**
   For each school needing attention, provide specific talking points for the monthly check-in conversation with the principal — what to raise, what to ask, what commitments to seek. Weave in email and note context (e.g. "Julie flagged Block C again on 8 Apr — ask for remediation timeline").