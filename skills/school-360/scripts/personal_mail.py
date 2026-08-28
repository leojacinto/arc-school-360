#!/usr/bin/env python3
"""
Read the user's school mailbox (via configured Outlook subfolder).
Parses forwarded emails to extract original sender, date, and content.

Usage:
  python3 personal_mail.py --all
  python3 personal_mail.py --school "<school_name>"
  python3 personal_mail.py --school "<school_name>" --full
  python3 personal_mail.py --since 30d
"""
import sys
import os
import json
import re
import argparse
from pathlib import Path

# Resolve M365 config path relative to THIS file's real location on disk.
_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_SKILLS_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
_M365_SCRIPTS = os.path.join(_SKILLS_ROOT, 'microsoft365', 'scripts')
sys.path.insert(0, _M365_SCRIPTS)

from config import get_access_token, graph_request

# Folder ID for school email subfolder (subfolder of Inbox)
FOLDER_ID = "AAMkAGNlZWYwZGI0LTFhMmItNDUxZi04ZGJkLWYzMTE4MTkwMWYwNgAuAAAAAAB2hZ5_iqGwR4FbJgpJRUAfAQCiDfYGPwDuQKIPYShOFTPyAAQJmI5NAAA="


def parse_original_metadata(body: str):
    """Extract original sender name, email, and date from forwarded email body."""
    match = re.search(
        r'On\s+(\d{1,2}/\d{1,2}/\d{4}),?\s+[\d:]+[\s\u202f]*[ap]m,?\s+"([^"]+)"\s+<([^>]+)>\s+wrote:',
        body, re.IGNORECASE
    )
    if match:
        date_str = match.group(1)
        name = match.group(2)
        email = match.group(3)
        parts = date_str.split('/')
        if len(parts) == 3:
            iso_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        else:
            iso_date = date_str
        return {"name": name, "email": email, "date": iso_date}
    return None


def extract_original_body(body: str):
    """Strip the forward header and return original email content."""
    match = re.search(r'wrote:\s*\n', body)
    if match:
        content = body[match.end():]
        content = re.split(r'\n_{3,}|\n-{3,}', content)[0]
        return content.strip()
    return body.strip()


def main():
    parser = argparse.ArgumentParser(description="Read school emails from configured mail folder")
    parser.add_argument("--all", action="store_true", help="List all emails")
    parser.add_argument("--school", help="Filter by school name (substring match)")
    parser.add_argument("--since", help="Only emails since (e.g. 30d, 90d, 7d)")
    parser.add_argument("--full", action="store_true", help="Include full body text")
    args = parser.parse_args()

    token, err = get_access_token()
    if err:
        print(json.dumps({"success": False, "message": f"Auth error: {err}"}))
        sys.exit(1)

    params = {
        "$top": "50",
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,receivedDateTime,body,bodyPreview"
    }

    result, error = graph_request("GET", f"/me/mailFolders/{FOLDER_ID}/messages", token, params=params)
    if error:
        print(json.dumps({"success": False, "message": f"Graph API error: {error}"}))
        sys.exit(1)

    emails = []
    for msg in result.get("value", []):
        # Use bodyPreview for metadata parsing (clean plain text, no HTML entities)
        preview_text = msg.get("bodyPreview", "")
        original = parse_original_metadata(preview_text)

        # Get body content for full text extraction
        body_text = msg.get("body", {}).get("content", "")
        if "<html" in body_text.lower():
            body_text = re.sub(r'<[^>]+>', '', body_text)
            body_text = re.sub(r'&nbsp;', ' ', body_text)
            body_text = re.sub(r'&quot;', '"', body_text)
            body_text = re.sub(r'&lt;', '<', body_text)
            body_text = re.sub(r'&gt;', '>', body_text)
            body_text = re.sub(r'&amp;', '&', body_text)
            body_text = re.sub(r'\n\s*\n', '\n\n', body_text).strip()

        # Fallback: try parsing from cleaned body if preview didn't match
        if not original:
            original = parse_original_metadata(body_text)

        original_body = extract_original_body(body_text)

        subject = re.sub(r'^(FW:|Fw:|fw:|RE:|Re:|re:)\s*', '', msg.get("subject", "")).strip()

        entry = {
            "subject": subject,
            "original_from": original["name"] if original else "Unknown",
            "original_email": original["email"] if original else "",
            "original_date": original["date"] if original else msg["receivedDateTime"][:10],
            "forwarded_date": msg["receivedDateTime"][:10],
            "preview": msg.get("bodyPreview", "")[:200],
        }
        if args.full:
            entry["body"] = original_body[:2000]

        emails.append(entry)

    # Filter by school name
    if args.school:
        school_lower = args.school.lower()
        emails = [e for e in emails if school_lower in e["subject"].lower()
                  or school_lower in e.get("body", "").lower()
                  or school_lower in e["preview"].lower()
                  or school_lower in e["original_email"].lower()]

    # Filter by date
    if args.since:
        from datetime import datetime, timedelta
        days = int(re.search(r'(\d+)', args.since).group(1))
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        emails = [e for e in emails if e["original_date"] >= cutoff]

    print(json.dumps({
        "success": True,
        "message": f"Found {len(emails)} emails in school mailbox",
        "data": emails
    }, indent=2))


if __name__ == "__main__":
    main()
