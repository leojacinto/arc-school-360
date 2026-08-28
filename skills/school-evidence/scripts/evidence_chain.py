#!/usr/bin/env python3
"""
Evidence Chain — Deterministic graph traversal for school issues.

Usage:
    python3 /skills/school-evidence/scripts/evidence_chain.py \
        --instance-id <UUID> --school "School Name" [--issue "keyword"]

Outputs JSON with:
- All linked records (attention → compliance → case → initiative → devices)
- Network snapshots + survey data as corroboration
- An ASCII evidence graph for inline rendering
"""

import argparse
import json
import subprocess
import sys
import os

# Resolve paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# query_table.py is in /skills/servicenow/scripts/ or /sandbox/skills/servicenow/scripts/
for candidate in ["/skills/servicenow/scripts", "/sandbox/skills/servicenow/scripts"]:
    if os.path.isfile(os.path.join(candidate, "query_table.py")):
        QUERY_SCRIPT = os.path.join(candidate, "query_table.py")
        break
else:
    print(json.dumps({"success": False, "error": "Cannot find query_table.py"}))
    sys.exit(1)


def query_table(instance_id, table, query_str, fields=None, limit=50):
    """Run query_table.py and return parsed JSON."""
    cmd = [
        sys.executable, QUERY_SCRIPT,
        "--instance-id", instance_id,
        "query", table,
        "--query", query_str,
        "--limit", str(limit),
        "--display-value",
    ]
    if fields:
        cmd.extend(["--fields", fields])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return {"success": False, "error": result.stderr.strip() or result.stdout.strip()}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"success": False, "error": f"Invalid JSON: {result.stdout[:200]}"}


def find_school_sys_id(instance_id, school_name):
    """Look up school sys_id from x_snc_qdoe_school."""
    res = query_table(instance_id, "x_snc_qdoe_school",
                      f"nameLIKE{school_name}",
                      fields="sys_id,name,school_code")
    if res.get("success") and res.get("data"):
        return res["data"][0]
    return None


def build_ascii_graph(data):
    """Generate a plain-language evidence chain diagram."""
    lines = []
    lines.append("")
    lines.append("=" * 72)
    lines.append("  EVIDENCE CHAIN")
    lines.append("=" * 72)
    lines.append("")

    # Attention item
    if data.get("attention"):
        att = data["attention"][0] if isinstance(data["attention"], list) else data["attention"]
        lines.append("  ❗ FLAGGED ISSUE")
        lines.append(f"  │ What:     {att.get('title', 'N/A')}")
        lines.append(f"  │ Priority: {att.get('priority', 'N/A')}")
        lines.append(f"  │ Why:      {att.get('reason', 'N/A')}")
        lines.append("  │")
        lines.append("  ▼ triggered by...")
        lines.append("")

    # Compliance finding
    if data.get("compliance"):
        comp = data["compliance"][0] if isinstance(data["compliance"], list) else data["compliance"]
        lines.append("  🚫 COMPLIANCE GAP")
        lines.append(f"  │ Standard: {comp.get('control', 'N/A')}")
        lines.append(f"  │ Severity: {comp.get('finding_severity', 'N/A')}")
        lines.append(f"  │ Status:   {comp.get('status', 'N/A')}")
        lines.append(f"  │ Case:     {comp.get('case_ref', 'N/A')}")
        lines.append("  │")
        lines.append("  ▼ linked to case...")
        lines.append("")

    # Case
    if data.get("case"):
        case = data["case"][0] if isinstance(data["case"], list) else data["case"]
        opened = case.get("opened_at", "N/A")
        lines.append("  📋 OPEN CASE")
        lines.append(f"  │ Number:   {case.get('number', 'N/A')}")
        lines.append(f"  │ Summary:  {case.get('short_description', 'N/A')}")
        lines.append(f"  │ State:    {case.get('state', 'N/A')}")
        lines.append(f"  │ Priority: {case.get('priority', 'N/A')}")
        lines.append(f"  │ Owner:    {case.get('assigned_to', 'N/A')}")
        lines.append(f"  │ Opened:   {opened}")
        lines.append(f"  │ Contact:  {case.get('contact', 'N/A')}")
        lines.append("  │")
        lines.append("  ▼ part of initiative...")
        lines.append("")

    # Initiative
    if data.get("initiative"):
        init = data["initiative"][0] if isinstance(data["initiative"], list) else data["initiative"]
        lines.append("  🎯 STALLED INITIATIVE")
        lines.append(f"  │ Name:      {init.get('name', 'N/A')}")
        lines.append(f"  │ Owner:     {init.get('owner', 'N/A')}")
        lines.append(f"  │ RAG:       {init.get('rag_status', 'N/A')}")
        lines.append(f"  │ Stage:     {init.get('stage', 'N/A')}")
        lines.append(f"  │ Milestone: {init.get('milestone', 'N/A')}")
        lines.append("  │")
        lines.append("  ▼ affects devices...")
        lines.append("")

    # Devices
    if data.get("devices"):
        lines.append("  💻 AFFECTED DEVICES")
        for dev in data["devices"]:
            lines.append(f"  │ {dev.get('device_class', '?')} × {dev.get('count', '?')} "
                         f"[{dev.get('lifecycle_status', '?')}]")
        lines.append("  │")
        lines.append("  ▼ causing network issues...")
        lines.append("")

    # Network
    if data.get("network"):
        lines.append("  📡 NETWORK IMPACT")
        for nw in data["network"]:
            lines.append(f"  │ Period:    {nw.get('period', 'N/A')}")
            lines.append(f"  │ Bandwidth: {nw.get('bandwidth_util', '?')}%")
            lines.append(f"  │ Uptime:    {nw.get('uptime_pct', '?')}%")
            lines.append(f"  │ Incidents: {nw.get('incidents', '?')}")
        lines.append("  │")
        lines.append("  ▼ which is hurting staff sentiment...")
        lines.append("")

    # Survey / Sentiment
    if data.get("survey"):
        lines.append("  📉 STAFF SENTIMENT")
        for sv in data["survey"]:
            theme = f' — theme: "{sv.get("theme")}"' if sv.get("theme") else ""
            lines.append(f"  │ {sv.get('period', '?')}: {sv.get('sentiment_score', '?')}/5 "
                         f"({sv.get('respondent_group', '?')}){theme}")
        lines.append("")

    lines.append("=" * 72)
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evidence chain traversal for school issues")
    parser.add_argument("--instance-id", required=True, help="ServiceNow instance UUID")
    parser.add_argument("--school", required=True, help="School name (partial match)")
    parser.add_argument("--issue", default=None, help="Optional issue keyword filter")
    args = parser.parse_args()

    # Step 1: Find school
    school = find_school_sys_id(args.instance_id, args.school)
    if not school:
        print(json.dumps({"success": False, "error": f"School not found: {args.school}"}))
        sys.exit(1)

    school_sys_id = school["sys_id"]
    school_name = school.get("name", args.school)

    # Step 2: Get attention items
    att_res = query_table(args.instance_id, "x_snc_qdoe_attention",
                          f"school={school_sys_id}",
                          fields="title,priority,reason,source_record")
    attention = att_res.get("data", []) if att_res.get("success") else []

    # Filter by issue keyword if provided
    if args.issue and attention:
        keyword = args.issue.lower()
        filtered = [a for a in attention if keyword in (a.get("title", "") + a.get("reason", "")).lower()]
        if filtered:
            attention = filtered

    # Step 3: Get compliance findings
    comp_res = query_table(args.instance_id, "x_snc_qdoe_compliance",
                           f"school={school_sys_id}",
                           fields="control,finding_severity,status,case_ref")
    compliance = comp_res.get("data", []) if comp_res.get("success") else []

    # Step 4: Get case(s) linked from compliance
    cases = []
    case_refs = [c.get("case_ref") for c in compliance if c.get("case_ref")]
    for ref in case_refs:
        case_res = query_table(args.instance_id, "sn_customerservice_case",
                               f"number={ref}",
                               fields="number,short_description,state,priority,assigned_to,opened_at,contact,description")
        if case_res.get("success") and case_res.get("data"):
            cases.extend(case_res["data"])

    # Step 5: Get initiatives
    init_res = query_table(args.instance_id, "x_snc_qdoe_initiative",
                           f"school={school_sys_id}",
                           fields="name,owner,rag_status,stage,milestone")
    initiatives = init_res.get("data", []) if init_res.get("success") else []

    # Step 6: Get devices
    dev_res = query_table(args.instance_id, "x_snc_qdoe_device",
                          f"school={school_sys_id}",
                          fields="device_class,count,lifecycle_status")
    devices = dev_res.get("data", []) if dev_res.get("success") else []

    # Step 7: Network snapshots
    net_res = query_table(args.instance_id, "x_snc_qdoe_network",
                          f"school={school_sys_id}",
                          fields="period,bandwidth_util,uptime_pct,incidents")
    network = net_res.get("data", []) if net_res.get("success") else []

    # Step 8: Survey / sentiment
    survey_res = query_table(args.instance_id, "x_snc_qdoe_survey",
                             f"school={school_sys_id}",
                             fields="period,sentiment_score,respondent_group,theme")
    survey = survey_res.get("data", []) if survey_res.get("success") else []

    # Build result
    result = {
        "success": True,
        "school": school_name,
        "school_sys_id": school_sys_id,
        "attention": attention,
        "compliance": compliance,
        "case": cases,
        "initiative": initiatives,
        "devices": devices,
        "network": network,
        "survey": survey,
    }

    # Build ASCII graph
    result["ascii_graph"] = build_ascii_graph(result)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
