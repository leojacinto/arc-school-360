#!/usr/bin/env python3
"""
Batch data fetcher for school skills.
One call returns ALL enrichment data for a school (or region).
Eliminates sequential query_table.py calls.

Usage:
  python3 school_data.py --instance-id <UUID> school "<school_name>"
  python3 school_data.py --instance-id <UUID> region --manager "<manager_name>"
  python3 school_data.py --instance-id <UUID> owner-check --user "<user_name>"
"""
import argparse
import json
import os
import sys
import concurrent.futures

# Resolve config path relative to THIS file's real location on disk.
# Works regardless of how the script is invoked (direct, subprocess, symlink).
_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_SKILLS_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))  # /skills or /sandbox/skills
_SN_SCRIPTS = os.path.join(_SKILLS_ROOT, 'servicenow', 'scripts')
sys.path.insert(0, _SN_SCRIPTS)

from config import get_servicenow_config, make_request


def query_table(config, table, query="", limit=100):
    """Query a ServiceNow table, return results or empty list."""
    params = {
        "sysparm_query": query,
        "sysparm_limit": limit,
        "sysparm_display_value": "true",
    }
    result, error = make_request("GET", f"table/{table}", config, params=params)
    if error:
        return {"table": table, "success": False, "error": error, "data": []}
    records = result.get("result", [])
    return {"table": table, "success": True, "count": len(records), "data": records}


def fetch_school_data(config, school_name, school_sys_id=None):
    """Fetch all enrichment data for a single school in parallel."""
    if school_sys_id:
        school_filter = f"school={school_sys_id}"
    else:
        school_filter = f"schoolLIKE{school_name}"

    tables = {
        "school": ("x_snc_qdoe_school", f"nameLIKE{school_name}", 5),
        "compliance": ("x_snc_qdoe_compliance", school_filter, 50),
        "staffing": ("x_snc_qdoe_staffing", school_filter, 10),
        "survey": ("x_snc_qdoe_survey", school_filter, 20),
        "initiative": ("x_snc_qdoe_initiative", school_filter, 20),
        "attention": ("x_snc_qdoe_attention", school_filter, 50),
        "device": ("x_snc_qdoe_device", school_filter, 100),
        "network": ("x_snc_qdoe_network", school_filter, 10),
        "maturity": ("x_snc_qdoe_maturity", school_filter, 20),
        "erp_budget": ("x_snc_qdoe_erp_budget", school_filter, 10),
    }

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {}
        for key, (table, query, limit) in tables.items():
            futures[executor.submit(query_table, config, table, query, limit)] = key

        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = {"table": tables[key][0], "success": False, "error": str(e), "data": []}

    # Resolve linked cases
    case_refs = set()
    for comp in results.get("compliance", {}).get("data", []):
        ref = comp.get("case_ref", "")
        if isinstance(ref, dict):
            ref = ref.get("display_value", "") or ref.get("value", "")
        if ref and isinstance(ref, str) and ref.startswith("CS"):
            case_refs.add(ref)

    if case_refs:
        case_query = "^OR".join([f"number={ref}" for ref in case_refs])
        results["cases"] = query_table(config, "sn_customerservice_case", case_query, 20)
    else:
        results["cases"] = {"table": "sn_customerservice_case", "success": True, "count": 0, "data": []}

    return results


def fetch_region_data(config, manager_name=None, region_sys_id=None):
    """Fetch all schools in a region with enrichment scoped to those schools only."""
    if region_sys_id:
        region_query = f"sys_id={region_sys_id}"
    elif manager_name:
        region_query = f"managerLIKE{manager_name}"
    else:
        return {"error": "Must provide --manager or --region-id"}

    region_result = query_table(config, "x_snc_qdoe_region", region_query, 5)
    if not region_result["data"]:
        return {"error": f"No region found for query: {region_query}"}

    region = region_result["data"][0]
    region_id = region.get("sys_id", "")
    region_name = region.get("name", "")

    # Step 1: get schools in this region
    schools_result = query_table(config, "x_snc_qdoe_school", f"region={region_id}", 200)
    schools = schools_result.get("data", [])

    # If only 1 school, just use fetch_school_data directly — much faster
    if len(schools) == 1:
        school = schools[0]
        school_data = fetch_school_data(config, school.get("name", ""), school.get("sys_id"))
        return {
            "region": {"name": region_name, "sys_id": region_id, "manager": region.get("manager", "")},
            "school_count": 1,
            "single_school": True,
            "schools": schools_result,
            **school_data,
        }

    # Multiple schools: build a filter scoped to these schools only
    school_sys_ids = [s.get("sys_id", "") for s in schools if s.get("sys_id")]
    school_names = [s.get("name", "") for s in schools if s.get("name")]

    # Build OR query for school field (limit to 20 schools per query to avoid URL length issues)
    # For large regions, use region-based filter instead
    if len(school_sys_ids) <= 20:
        school_filter = "^OR".join([f"school={sid}" for sid in school_sys_ids])
    else:
        # Fallback: query all and filter client-side by school names
        school_filter = ""

    # Parallel fetch: attention + compliance + initiatives SCOPED to these schools
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        f_attention = executor.submit(query_table, config, "x_snc_qdoe_attention", school_filter, 500)
        f_compliance = executor.submit(query_table, config, "x_snc_qdoe_compliance", school_filter, 500)
        f_initiatives = executor.submit(query_table, config, "x_snc_qdoe_initiative", school_filter, 500)
        f_survey = executor.submit(query_table, config, "x_snc_qdoe_survey", school_filter, 500)

    attention = f_attention.result()
    compliance = f_compliance.result()
    initiatives = f_initiatives.result()
    survey = f_survey.result()

    # If we used empty filter (large region), filter client-side
    if not school_filter and school_names:
        name_set = set(n.lower() for n in school_names)
        for result_dict in [attention, compliance, initiatives, survey]:
            if result_dict.get("data"):
                result_dict["data"] = [
                    r for r in result_dict["data"]
                    if any(sn.lower() in str(r.get("school", "")).lower() for sn in school_names)
                ]
                result_dict["count"] = len(result_dict["data"])

    return {
        "region": {"name": region_name, "sys_id": region_id, "manager": region.get("manager", "")},
        "school_count": len(schools),
        "single_school": False,
        "schools": schools_result,
        "attention": attention,
        "compliance": compliance,
        "initiatives": initiatives,
        "survey": survey,
    }


def main():
    parser = argparse.ArgumentParser(description="Batch school data fetcher")
    parser.add_argument("--instance-id", required=True, help="ServiceNow instance ID")
    sub = parser.add_subparsers(dest="command")

    school_p = sub.add_parser("school", help="Fetch all data for a single school")
    school_p.add_argument("name", help="School name (partial match)")
    school_p.add_argument("--sys-id", help="School sys_id (exact match)")

    region_p = sub.add_parser("region", help="Fetch region rollup data")
    region_p.add_argument("--manager", help="Manager name (partial match)")
    region_p.add_argument("--region-id", help="Region sys_id")

    owner_p = sub.add_parser("owner-check", help="Verify user owns school/region")
    owner_p.add_argument("--user", required=True, help="Username to verify")

    args = parser.parse_args()

    config, error = get_servicenow_config(instance_id=args.instance_id)
    if error:
        print(json.dumps({"success": False, "error": error}))
        sys.exit(1)

    if args.command == "school":
        data = fetch_school_data(config, args.name, args.sys_id)
        print(json.dumps({"success": True, "command": "school", "school_name": args.name, **data}, default=str))

    elif args.command == "region":
        data = fetch_region_data(config, args.manager, args.region_id)
        print(json.dumps({"success": True, "command": "region", **data}, default=str))

    elif args.command == "owner-check":
        region_result = query_table(config, "x_snc_qdoe_region", f"managerLIKE{args.user}", 5)
        school_result = query_table(config, "x_snc_qdoe_school", f"managerLIKE{args.user}", 200)
        print(json.dumps({
            "success": True,
            "command": "owner-check",
            "user": args.user,
            "regions": region_result["data"],
            "schools": [{"name": s.get("name"), "sys_id": s.get("sys_id")} for s in school_result["data"]],
        }, default=str))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
