#!/usr/bin/env python3
"""
attention_report.py — Single deterministic orchestrator for school-attention.

Calls existing working scripts as subprocesses:
  - school_data.py (ServiceNow data)
  - personal_mail.py (email context)
  - personal_context.py (OneDrive notes)

Then scores, ranks, and outputs ONE JSON blob with everything.
No duplicated imports. No fragile sys.path games.
"""

import argparse
import json
import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# CHART GENERATION — deterministic radar from score_school() output
# ============================================================

RADAR_DIMENSIONS = ["risk", "compliance", "staffing", "sentiment", "initiatives"]
RADAR_LABELS = ["Risk", "Compliance", "Staffing", "Sentiment", "Initiatives"]
RADAR_SCALE_MAX = 5  # all dimensions scored 0-5

def generate_radar(schools_with_scores, output_dir="/tmp"):
    """
    Render a radar chart from score_school() output.
    
    Args:
        schools_with_scores: list of dicts, each with "name" and "scores" keys.
                             scores must contain RADAR_DIMENSIONS keys (0-5 int).
        output_dir: directory to write PNG to.
    
    Returns:
        path to PNG file, or None if matplotlib unavailable.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None

    N = len(RADAR_DIMENSIONS)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    colours = ['#e67e22', '#e74c3c', '#3498db', '#2ecc71', '#9b59b6',
               '#1abc9c', '#f39c12', '#d35400']

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)   # first axis at top (12 o'clock)
    ax.set_theta_direction(-1)        # clockwise

    for idx, school in enumerate(schools_with_scores):
        scores = school["scores"]
        values = [scores.get(dim, 0) for dim in RADAR_DIMENSIONS]
        values += values[:1]
        colour = colours[idx % len(colours)]
        ax.plot(angles, values, linewidth=2, label=school["name"], color=colour, marker='o', markersize=5)
        ax.fill(angles, values, alpha=0.12, color=colour)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(RADAR_LABELS, fontsize=11, fontweight='bold')
    ax.set_ylim(0, RADAR_SCALE_MAX)
    ax.set_yticks(range(0, RADAR_SCALE_MAX + 1))
    ax.set_yticklabels([str(i) for i in range(0, RADAR_SCALE_MAX + 1)], fontsize=8, color='grey')
    ax.grid(True, alpha=0.3)

    if len(schools_with_scores) == 1:
        title = f"{schools_with_scores[0]['name']} — Risk Profile"
    else:
        title = "Portfolio Risk Profile"
    plt.title(title, fontsize=13, fontweight='bold', pad=20)

    if len(schools_with_scores) > 1:
        ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1), fontsize=9)

    plt.tight_layout()
    output_path = os.path.join(output_dir, "school-attention-radar.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return output_path

# ============================================================
# CONSTANTS — resolve paths that work in both /skills/ overlay and /sandbox/skills/
# ============================================================
def _resolve(relative):
    """Find script at /skills/... or /sandbox/skills/... (whichever exists)."""
    candidates = [
        f"/skills/{relative}",
        f"/sandbox/skills/{relative}",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # Fallback: return first (will error with clear message)
    return candidates[0]

SCHOOL_DATA_SCRIPT = _resolve("school-360/scripts/school_data.py")
PERSONAL_MAIL_SCRIPT = _resolve("school-360/scripts/personal_mail.py")
PERSONAL_CONTEXT_SCRIPT = _resolve("school-360/scripts/personal_context.py")

# ============================================================
# SUBPROCESS HELPERS
# ============================================================

def run_script(cmd, timeout=60, pythonpath=None):
    """Run a script, return (parsed_json, error_string)."""
    try:
        env = os.environ.copy()
        if pythonpath:
            env["PYTHONPATH"] = pythonpath + ":" + env.get("PYTHONPATH", "")
        else:
            env["PYTHONPATH"] = "/sandbox/skills/servicenow/scripts:" + env.get("PYTHONPATH", "")
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env
        )
        if result.returncode != 0:
            return None, f"Exit {result.returncode}: {result.stderr.strip()}"
        # Try to parse JSON from stdout
        output = result.stdout.strip()
        if not output:
            return None, "Empty output"
        try:
            return json.loads(output), None
        except json.JSONDecodeError:
            return {"raw": output}, None
    except subprocess.TimeoutExpired:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)


def fetch_region_data(instance_id, manager_name):
    """Call school_data.py region --manager <name>."""
    cmd = [
        sys.executable, SCHOOL_DATA_SCRIPT,
        "--instance-id", instance_id,
        "region", "--manager", manager_name
    ]
    return run_script(cmd, timeout=60)


def fetch_emails(school_name=None):
    """Call personal_mail.py."""
    cmd = [sys.executable, PERSONAL_MAIL_SCRIPT]
    if school_name:
        cmd += ["--school", school_name]
    else:
        cmd += ["--all"]
    return run_script(cmd, timeout=30, pythonpath="/sandbox/skills/microsoft365/scripts")


def fetch_notes(school_name=None):
    """Call personal_context.py."""
    cmd = [sys.executable, PERSONAL_CONTEXT_SCRIPT]
    if school_name:
        cmd += ["--school", school_name]
    else:
        cmd += ["--all"]
    return run_script(cmd, timeout=30, pythonpath="/sandbox/skills/microsoft365/scripts")


# ============================================================
# SCORING
# ============================================================

def score_school(school_data):
    """
    Score a school on 5 dimensions (0-5 each, higher = worse).
    Returns dict with dimension scores and composite.
    """
    scores = {}

    # 1. Risk — active_risk_count
    risk_count = int(school_data.get("active_risk_count", 0) or 0)
    scores["risk"] = min(risk_count, 5)

    # 2. Compliance — count of non-compliant findings
    compliance_items = school_data.get("_compliance", [])
    high_sev = sum(1 for c in compliance_items if c.get("finding_severity") == "high")
    med_sev = sum(1 for c in compliance_items if c.get("finding_severity") == "medium")
    scores["compliance"] = min(high_sev * 2 + med_sev, 5)

    # 3. Staffing — vacancies / FTE ratio
    staffing_items = school_data.get("_staffing", [])
    if staffing_items:
        latest = staffing_items[0]
        vacancies = int(latest.get("vacancies", 0) or 0)
        fte = int(str(latest.get("fte", 100) or 100).replace(",", ""))
        ratio = vacancies / max(fte, 1)
        if ratio > 0.1:
            scores["staffing"] = 5
        elif ratio > 0.05:
            scores["staffing"] = 3
        elif ratio > 0.02:
            scores["staffing"] = 2
        else:
            scores["staffing"] = 1
    else:
        scores["staffing"] = 0

    # 4. Sentiment — current score + trend
    survey_items = school_data.get("_survey", [])
    if len(survey_items) >= 2:
        current = float(survey_items[-1].get("sentiment_score", 3.5) or 3.5)
        previous = float(survey_items[-2].get("sentiment_score", 3.5) or 3.5)
        base = 5 - current  # invert: 5.0 → 0, 1.0 → 4
        trend_penalty = max(0, previous - current)  # drop = penalty
        scores["sentiment"] = min(round(base + trend_penalty), 5)
    elif len(survey_items) == 1:
        current = float(survey_items[0].get("sentiment_score", 3.5) or 3.5)
        scores["sentiment"] = min(round(5 - current), 5)
    else:
        scores["sentiment"] = 0

    # 5. Initiatives — overdue/amber/red
    initiative_items = school_data.get("_initiatives", [])
    overdue = sum(1 for i in initiative_items if "overdue" in str(i.get("milestone", "")).lower())
    red_amber = sum(1 for i in initiative_items if i.get("rag_status") in ("red", "amber"))
    scores["initiatives"] = min(overdue * 2 + red_amber, 5)

    scores["composite"] = sum(scores.values())
    scores["max_composite"] = 25
    return scores


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="School attention report — deterministic single-command orchestrator"
    )
    parser.add_argument("--instance-id", required=True, help="ServiceNow instance ID")
    parser.add_argument("--manager", required=True, help="Manager display name")
    parser.add_argument("--school", default=None, help="Filter to a single school by name (substring match)")
    parser.add_argument("--skip-notes", action="store_true", help="Skip personal notes fetch")
    parser.add_argument("--skip-email", action="store_true", help="Skip email fetch")
    args = parser.parse_args()

    output = {
        "success": True,
        "manager": args.manager,
        "schools": [],
        "errors": []
    }

    # ---- STEP 1: Fetch region data from ServiceNow ----
    region_data, err = fetch_region_data(args.instance_id, args.manager)
    if err:
        output["success"] = False
        output["errors"].append(f"region_data: {err}")
        print(json.dumps(output, indent=2))
        sys.exit(1)

    if not region_data.get("success"):
        output["success"] = False
        output["errors"].append(f"region_data returned success=false")
        print(json.dumps(output, indent=2))
        sys.exit(1)

    region_info = region_data.get("region", {})
    output["region"] = region_info.get("name", "Unknown")

    schools_raw = region_data.get("schools", {}).get("data", [])
    if not schools_raw:
        output["errors"].append("No schools found for this manager")
        print(json.dumps(output, indent=2))
        sys.exit(0)

    # Filter to a single school if --school provided
    if args.school:
        filter_lower = args.school.lower()
        schools_raw = [s for s in schools_raw if filter_lower in s.get("name", "").lower()]
        if not schools_raw:
            output["errors"].append(f"No school matching '{args.school}' found")
            print(json.dumps(output, indent=2))
            sys.exit(0)

    # Attach sub-data to each school for scoring
    attention_data = region_data.get("attention", {}).get("data", [])
    compliance_data = region_data.get("compliance", {}).get("data", [])
    initiative_data = region_data.get("initiative", {}).get("data", [])
    survey_data = region_data.get("survey", {}).get("data", [])
    staffing_data = region_data.get("staffing", {}).get("data", [])
    device_data = region_data.get("device", {}).get("data", [])
    network_data = region_data.get("network", {}).get("data", [])
    cases_data = region_data.get("cases", {}).get("data", [])
    maturity_data = region_data.get("maturity", {}).get("data", [])

    for school in schools_raw:
        sid = school.get("sys_id", "")
        school_name = school.get("name", "")

        # Filter sub-data for this school
        def for_school(items):
            return [i for i in items if
                    i.get("school", {}).get("display_value", "") == school_name or
                    i.get("school", {}).get("link", "").endswith(sid)]

        school["_compliance"] = for_school(compliance_data)
        school["_initiatives"] = for_school(initiative_data)
        school["_survey"] = for_school(survey_data)
        school["_staffing"] = for_school(staffing_data)
        school["_attention"] = for_school(attention_data)
        school["_devices"] = for_school(device_data)
        school["_network"] = for_school(network_data)
        school["_cases"] = for_school(cases_data)
        school["_maturity"] = for_school(maturity_data)

        # Score
        scores = score_school(school)

        # Use short name for email/notes search (strip "State High School" etc.)
        stop_words = {"state", "high", "school", "primary", "college", "secondary", "special"}
        short_name = " ".join(
            w for w in school_name.split() if w.lower() not in stop_words
        ).strip() or school_name

        # ---- Fetch emails + notes in parallel (threaded) ----
        emails = None
        notes = None

        if not args.skip_email or not args.skip_notes:
            def _fetch_email():
                return fetch_emails(short_name) if not args.skip_email else (None, None)

            def _fetch_notes():
                return fetch_notes(short_name) if not args.skip_notes else (None, None)

            with ThreadPoolExecutor(max_workers=2) as executor:
                email_future = executor.submit(_fetch_email)
                notes_future = executor.submit(_fetch_notes)

                email_data, email_err = email_future.result()
                if email_err:
                    output["errors"].append(f"email ({school_name}): {email_err}")
                elif email_data:
                    emails = email_data.get("data", []) if email_data else []

                notes_data, notes_err = notes_future.result()
                if notes_err:
                    output["errors"].append(f"notes ({school_name}): {notes_err}")
                elif notes_data:
                    notes = notes_data

        # Build school entry
        entry = {
            "name": school_name,
            "sys_id": sid,
            "school_code": school.get("school_code", ""),
            "school_type": school.get("school_type", ""),
            "sector": school.get("sector", ""),
            "enrolment_count": school.get("enrolment_count", ""),
            "overall_health": school.get("overall_health", ""),
            "digital_maturity_score": school.get("digital_maturity_score", ""),
            "sentiment_score": school.get("sentiment_score", ""),
            "principal": school.get("principal", {}).get("display_value", ""),
            "ict_coordinator": school.get("ict_coordinator", {}).get("display_value", ""),
            "scores": scores,
            "attention_items": [
                {"title": a.get("title", ""), "priority": a.get("priority", ""),
                 "reason": a.get("reason", "")}
                for a in school["_attention"]
            ],
            "compliance_items": [
                {"control": c.get("control", ""), "severity": c.get("finding_severity", ""),
                 "status": c.get("status", ""), "case_ref": c.get("case_ref", {}).get("display_value", "")}
                for c in school["_compliance"]
            ],
            "initiatives": [
                {"name": i.get("name", ""), "rag": i.get("rag_status", ""),
                 "milestone": i.get("milestone", ""), "owner": i.get("owner", {}).get("display_value", "")}
                for i in school["_initiatives"]
            ],
            "staffing": [
                {"period": s.get("period", ""), "vacancies": s.get("vacancies", ""),
                 "fte": s.get("fte", ""), "transfers": s.get("transfers_in_out", "")}
                for s in school["_staffing"]
            ],
            "survey_trend": [
                {"period": sv.get("period", ""), "score": sv.get("sentiment_score", ""),
                 "group": sv.get("respondent_group", ""), "theme": sv.get("theme", "")}
                for sv in school["_survey"]
            ],
            "devices": [
                {"class": d.get("device_class", ""), "count": d.get("count", ""),
                 "lifecycle": d.get("lifecycle_status", "")}
                for d in school["_devices"]
            ],
            "network": [
                {"period": n.get("period", ""), "bandwidth_util": n.get("bandwidth_util", ""),
                 "uptime_pct": n.get("uptime_pct", ""), "incidents": n.get("incidents", "")}
                for n in school["_network"]
            ],
            "maturity": [
                {"dimension": m.get("dimension", ""), "score": m.get("score", "")}
                for m in school["_maturity"]
            ],
            "emails": emails,
            "notes": notes,
        }
        output["schools"].append(entry)

    # Sort by composite score descending (worst first)
    output["schools"].sort(key=lambda s: s["scores"]["composite"], reverse=True)

    # ---- STEP 4: Generate radar chart from computed scores ----
    chart_input = [
        {"name": s["name"], "scores": s["scores"]}
        for s in output["schools"]
    ]
    chart_path = generate_radar(chart_input)
    # Signal success without exposing the path (prevents agent from pre-emptively embedding)
    output["chart_generated"] = chart_path is not None
    if chart_path:
        print("[chart] generated successfully", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
