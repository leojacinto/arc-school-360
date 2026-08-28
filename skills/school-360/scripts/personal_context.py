"""
Fetch ALL personal context for a school in one call — OneDrive notes + email trail.
This is the ONLY script needed for the user's personal data. One call, both sources.

Usage:
  python3 /skills/school-360/scripts/personal_context.py --school "<school_name>"
  python3 /skills/school-360/scripts/personal_context.py --all
"""
import sys, os, re, json, argparse, urllib.request, ssl

# Resolve M365 config path relative to THIS file's real location on disk.
_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_SKILLS_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
_M365_SCRIPTS = os.path.join(_SKILLS_ROOT, 'microsoft365', 'scripts')
sys.path.insert(0, _M365_SCRIPTS)

from config import get_access_token, graph_request

# ─── Constants ───
NOTES_ITEM_ID = "01DJ3NF2NUTCZNLWLTOJB2HQSNTSQJYUS7"
MAIL_FOLDER_ID = "AAMkAGNlZWYwZGI0LTFhMmItNDUxZi04ZGJkLWYzMTE4MTkwMWYwNgAuAAAAAAB2hZ5_iqGwR4FbJgpJRUAfAQCiDfYGPwDuQKIPYShOFTPyAAQJmI5NAAA="


def fetch_notes(token, school_filter=None):
    """Fetch OneDrive markdown notes, optionally filter to a school section."""
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{NOTES_ITEM_ID}/content"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            content = resp.read().decode("utf-8")
    except Exception as e:
        return {"available": False, "error": str(e)}

    if not school_filter:
        return {"available": True, "content": content}

    # Extract the matching ## section
    pattern = re.compile(
        rf'^## .*{re.escape(school_filter)}.*$',
        re.IGNORECASE | re.MULTILINE
    )
    match = pattern.search(content)
    if not match:
        # Try partial match
        pattern = re.compile(
            rf'^## .*{school_filter.split()[0]}.*$',
            re.IGNORECASE | re.MULTILINE
        )
        match = pattern.search(content)

    if not match:
        return {"available": True, "content": None, "message": f"No section found matching '{school_filter}'"}

    # Get everything from this ## to the next ##
    start = match.start()
    next_section = re.search(r'^## ', content[match.end():], re.MULTILINE)
    if next_section:
        end = match.end() + next_section.start()
    else:
        end = len(content)

    section = content[start:end].strip()
    return {"available": True, "content": section}


def fetch_emails(token, school_filter=None):
    """Fetch emails from Jonathan's mail folder."""
    params = {
        "$top": "50",
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,receivedDateTime,bodyPreview"
    }

    result, error = graph_request("GET", f"/me/mailFolders/{MAIL_FOLDER_ID}/messages", token, params=params)
    if error:
        return {"available": False, "error": str(error)}

    emails = []
    for msg in result.get("value", []):
        preview = msg.get("bodyPreview", "")

        # Parse original sender from forward header in preview
        # Handles non-breaking spaces (\u202f, \u00a0) and regular spaces
        sender_match = re.search(
            r'On\s+(\d{1,2}/\d{1,2}/\d{4}),?\s*[\d:]+[\s\u202f\u00a0]*[ap]m,?\s*["\u201c]([^"\u201d]+)["\u201d]\s*<([^>]+)>',
            preview, re.IGNORECASE
        )

        if sender_match:
            date_str = sender_match.group(1)
            name = sender_match.group(2)
            email_addr = sender_match.group(3)
            parts = date_str.split('/')
            iso_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}" if len(parts) == 3 else date_str
        else:
            name = "Unknown"
            email_addr = ""
            iso_date = msg["receivedDateTime"][:10]

        # Clean subject
        subject = re.sub(r'^(FW:|Fw:|fw:|RE:|Re:|re:)\s*', '', msg.get("subject", "")).strip()

        # Extract body after "wrote:" line
        body_match = re.search(r'wrote:\s*\n', preview)
        body = preview[body_match.end():].strip() if body_match else preview

        emails.append({
            "subject": subject,
            "from": name,
            "email": email_addr,
            "date": iso_date,
            "body": body[:300]
        })

    # Apply school filter
    if school_filter:
        school_lower = school_filter.lower()
        emails = [e for e in emails if
                  school_lower in e["subject"].lower() or
                  school_lower in e["body"].lower() or
                  school_lower in e["email"].lower()]

    return {"available": True, "emails": emails, "count": len(emails)}


def main():
    parser = argparse.ArgumentParser(description="Fetch all personal context for a school")
    parser.add_argument("--school", help="School name filter (substring match)")
    parser.add_argument("--all", action="store_true", help="Return all notes and emails unfiltered")
    args = parser.parse_args()

    school = args.school if args.school else (None if args.all else None)

    token, err = get_access_token()
    if err:
        print(json.dumps({"success": False, "message": f"Auth error: {err}"}))
        sys.exit(1)

    notes_result = fetch_notes(token, school)
    email_result = fetch_emails(token, school)

    output = {
        "success": True,
        "school_filter": school,
        "notes": notes_result,
        "emails": email_result,
    }

    # Summary line
    notes_status = "✅" if notes_result.get("available") and notes_result.get("content") else "⚠️ unavailable"
    email_count = email_result.get("count", 0) if email_result.get("available") else 0
    email_status = f"✅ {email_count} emails" if email_result.get("available") else "⚠️ unavailable"
    output["summary"] = f"Notes: {notes_status} | Email: {email_status}"

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
