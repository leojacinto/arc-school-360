---
name: school-notes
description: Personal school notebook — view and append running notes to the OneDrive markdown file in School360. Use for "show/add notes on [school]".
---

# School Notes — Personal Notebook (OneDrive Markdown)

Manage per-school running notes in the shared OneDrive markdown file at `Engagements/DoE/School360/Jonathan_OneNote_Notes.md`.

## ⚠️ CRITICAL: Jonathan's Email Access

**DO NOT use `mail.py list --folder jonathan`** — that will fail with HTTP 400.
The ONLY correct way to access Jonathan's email is:
````
python3 /skills/school-360/scripts/personal_mail.py --school "<name>" --full
````
Never use mail.py, never guess folder names, never pass display names as folder IDs.

## Ownership (pre-verified — DO NOT re-check)

The current user's name and region come from the **User Profile** section of the system prompt. **Never query ownership**.
Proceed directly to notes read/write.

## ⚡ Performance Rules

1. **No ServiceNow queries needed** — notes are in OneDrive
2. **Don't re-read this SKILL.md** if already in context
3. **No subagents** — direct tool calls only
4. **If user says "note that X"** — skip confirmation, just append immediately
5. **One Graph API call to read, two to write** (download → modify → upload)

## When to use

- "Show my notes on [school]"
- "Add a note for [school]"
- "School notebook"
- "What did I write about [school] last time?"
- "Note that [observation] for [school]"

## Architecture — Single Markdown File on OneDrive

Notes are stored as a single markdown file synced via OneDrive:

```
OneDrive: Engagements/DoE/School360/Jonathan_OneNote_Notes.md
Item ID:  01DJ3NF2NUTCZNLWLTOJB2HQSNTSQJYUS7
```

The file is structured with:
- H2 (`##`) = School name (section header)
- H3 (`###`) = Individual note entry with topic
- `*Last edited: DD Mon YYYY*` = timestamp line
- Block quotes and paragraphs = note content
- `**TODO:**` markers for action items

## Operations

### Show Notes (Read)

Read the file in one Graph API call:

```python
cd /sandbox && python3 -c "
import sys, urllib.request, ssl
sys.path.insert(0, 'skills/microsoft365/scripts')
from config import get_access_token

token, err = get_access_token()
url = 'https://graph.microsoft.com/v1.0/me/drive/items/01DJ3NF2NUTCZNLWLTOJB2HQSNTSQJYUS7/content'
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
ctx = ssl.create_default_context()
with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
    print(resp.read().decode('utf-8'))
"
```

Then extract the relevant school section (find the `## School Name` header, include everything until the next `## ` header).

### Add a Note (Append)

1. **Download** the current file content (same read method above)
2. **Find** the school's section (`## School Name`)
3. **Insert** a new H3 entry at the TOP of that section (after the `## ` header), format:

```markdown
### <School Name> – <topic>
*Last edited: DD Mon YYYY*

> <note content>
```

4. If the school section does NOT exist, create a new `## School Name` section at the end of the file.
5. **Upload** the modified content back:

```python
cd /sandbox && python3 -c "
import sys, urllib.request, ssl
sys.path.insert(0, 'skills/microsoft365/scripts')
from config import get_access_token

token, err = get_access_token()
content = open('/tmp/updated_notes.md', 'rb').read()
url = 'https://graph.microsoft.com/v1.0/me/drive/items/01DJ3NF2NUTCZNLWLTOJB2HQSNTSQJYUS7/content'
req = urllib.request.Request(url, data=content, method='PUT',
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'text/plain'})
ctx = ssl.create_default_context()
with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
    print('Saved.' if resp.status in (200,201) else f'Status: {resp.status}')
"
```

### Workflow (Append — Step-by-Step)

1. Read current content via Graph API → save to `/tmp/current_notes.md`
2. Parse markdown, find or create the school's `## ` section
3. Insert new entry after the section header
4. Write modified content to `/tmp/updated_notes.md`
5. Upload via PUT to the same item ID
6. Confirm to user

## Important Notes

- **Date format** in entries: `*Last edited: DD Mon YYYY*` (e.g. `*Last edited: 27 Aug 2026*`)
- **If the user says "note that X"** — treat X as the note content, don't ask for confirmation
- **The OneDrive markdown file is the source of truth** — don't duplicate notes in memory
- **Insert new entries at the TOP of a school section** — most recent first
- **Preserve all existing content** — never truncate or lose notes when appending
- **Use block quotes** (`>`) for observation-style notes, plain paragraphs for meeting notes
- **`**TODO:**`** prefix for action items

## Source Citation (Mandatory)

- When displaying notes, show: `📓 Personal notebook (OneDrive) — last updated [date from entry]`
- When confirming a note was added: `✅ Saved to School360 notebook (entry: 2026-08-27 — <topic>)`
- If showing notes alongside other school data, clearly label which facts come from the personal notebook vs. live ServiceNow data
