"""
Organize and clean up docs folder.
"""
import os
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import csv

DOCS_DIR = Path(r"C:\Users\Vache\projects\arc_pdf_tool\docs")
TODAY = datetime.now().strftime("%Y%m%d")

# Classification rules
GUIDES_PATTERNS = ['*tutorial*', '*guide*', '*howto*', '*checklist*', '*quickstart*']
REFERENCE_PATTERNS = ['*schema*', 'api*', 'openapi*', '*_spec*', 'data_dictionary*']
LAYOUTS_PATTERNS = ['*layout*', '*audit*', '*preview*']
REPORTS_PATTERNS = ['*audit*', '*.csv', '*.json', '*_results*', '*_summary*', '*_report*']
IMAGE_PATTERNS = ['*.png', '*.jpg', '*.jpeg', '*.svg', '*.gif', '*.drawio']

# Delete patterns
DELETE_PATTERNS = [
    '.DS_Store', 'Thumbs.db', 'desktop.ini',
    '~$*', '*.tmp', '*.bak', '*.old', '*.orig', '*.rej',
    '*.log', '*.cache', '*.toc', '*.aux',
    '.ipynb_checkpoints', '.pytest_cache'
]

def get_file_hash(filepath):
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except:
        return None

def should_delete(filename):
    """Check if file matches delete patterns."""
    for pattern in DELETE_PATTERNS:
        if pattern.startswith('*'):
            if filename.endswith(pattern[1:]):
                return True
        elif pattern.endswith('*'):
            if filename.startswith(pattern[:-1]):
                return True
        elif filename == pattern:
            return True
    return False

def classify_file(filepath):
    """Classify file into destination folder."""
    name = filepath.name.lower()

    # Check if should delete first
    if should_delete(name):
        return 'DELETE', 'matches noise pattern'

    # Images
    if any(filepath.match(p) for p in IMAGE_PATTERNS):
        return 'images', 'image file'

    # Guides (tutorials, how-to, checklists)
    if any(filepath.match(p) for p in GUIDES_PATTERNS):
        return 'guides', 'guide/tutorial'

    # Reference (API/specs/schemas)
    if any(filepath.match(p) for p in REFERENCE_PATTERNS):
        return 'reference', 'API/spec/schema'

    # Layouts
    if any(filepath.match(p) for p in LAYOUTS_PATTERNS):
        return 'layouts', 'layout doc'

    # Reports
    if any(filepath.match(p) for p in REPORTS_PATTERNS):
        return 'reports', 'report/summary'

    # Special cases
    if name == 'readme.md':
        return 'KEEP_ROOT', 'main README'

    if name.endswith('.md'):
        # General markdown docs - check content hints
        if any(x in name for x in ['phase', 'complete', 'status', 'next']):
            return 'reports', 'status report'
        if any(x in name for x in ['install', 'deployment', 'docker', 'run']):
            return 'guides', 'setup guide'
        if any(x in name for x in ['parser', 'diff', 'operations']):
            return 'reference', 'reference doc'
        # Default markdown to guides
        return 'guides', 'markdown doc'

    if name.endswith(('.py', '.dot')):
        return 'ARCHIVE', 'script/diagram - unclear purpose'

    # Ambiguous - archive it
    return 'ARCHIVE', 'unclear classification'

def scan_and_plan():
    """Scan docs folder and create action plan."""
    print("=" * 80)
    print("DRY RUN - Scanning docs folder")
    print("=" * 80)

    all_files = []
    for root, dirs, files in os.walk(DOCS_DIR):
        # Skip existing organized folders during scan
        root_path = Path(root)
        if any(x in root_path.parts for x in ['guides', 'reference', 'layouts', 'reports', 'images', 'archive']):
            continue

        for file in files:
            filepath = Path(root) / file
            all_files.append(filepath)

    # Calculate hashes and detect duplicates
    hash_to_files = defaultdict(list)
    for filepath in all_files:
        file_hash = get_file_hash(filepath)
        if file_hash:
            hash_to_files[file_hash].append(filepath)

    # Build action plan
    actions = []
    duplicates_deleted = 0

    for filepath in all_files:
        relative_path = filepath.relative_to(DOCS_DIR)
        file_hash = get_file_hash(filepath)

        # Check for duplicates
        if file_hash and len(hash_to_files[file_hash]) > 1:
            # Keep newest, mark others for deletion
            files_with_hash = sorted(hash_to_files[file_hash], key=lambda f: f.stat().st_mtime, reverse=True)
            if filepath != files_with_hash[0]:
                actions.append({
                    'action': 'DELETE',
                    'from': str(relative_path),
                    'to': '',
                    'reason': f'duplicate of {files_with_hash[0].name}',
                    'hash': file_hash
                })
                duplicates_deleted += 1
                continue

        # Classify
        dest, reason = classify_file(filepath)

        if dest == 'DELETE':
            actions.append({
                'action': 'DELETE',
                'from': str(relative_path),
                'to': '',
                'reason': reason,
                'hash': file_hash or ''
            })
        elif dest == 'KEEP_ROOT':
            actions.append({
                'action': 'KEEP',
                'from': str(relative_path),
                'to': str(relative_path),
                'reason': reason,
                'hash': file_hash or ''
            })
        elif dest == 'ARCHIVE':
            archive_path = f'archive/{TODAY}/{relative_path}'
            actions.append({
                'action': 'ARCHIVE',
                'from': str(relative_path),
                'to': archive_path,
                'reason': reason,
                'hash': file_hash or ''
            })
        else:
            # Move to organized folder
            new_path = f'{dest}/{filepath.name}'
            actions.append({
                'action': 'MOVE',
                'from': str(relative_path),
                'to': new_path,
                'reason': reason,
                'hash': file_hash or ''
            })

    # Print plan
    print(f"\nFound {len(all_files)} files")
    print(f"Duplicates to remove: {duplicates_deleted}")
    print("\nACTION PLAN:")
    print("-" * 80)
    print(f"{'Action':<10} {'From':<40} {'To':<40} {'Reason':<20}")
    print("-" * 80)

    for action in actions:
        from_str = action['from'][:37] + '...' if len(action['from']) > 40 else action['from']
        to_str = action['to'][:37] + '...' if len(action['to']) > 40 else action['to']
        reason_str = action['reason'][:17] + '...' if len(action['reason']) > 20 else action['reason']
        print(f"{action['action']:<10} {from_str:<40} {to_str:<40} {reason_str:<20}")

    return actions

def apply_plan(actions, dry_run=False):
    """Apply the cleanup plan."""
    if dry_run:
        print("\n[DRY RUN] Would execute the plan above")
        return

    print("\n" + "=" * 80)
    print("APPLYING CLEANUP PLAN")
    print("=" * 80)

    # Create destination folders
    for folder in ['guides', 'reference', 'layouts', 'reports', 'images', f'archive/{TODAY}']:
        folder_path = DOCS_DIR / folder
        folder_path.mkdir(parents=True, exist_ok=True)

    # Track actions for reporting
    moved_count = 0
    deleted_count = 0
    archived_count = 0
    deleted_files = []
    archived_files = []

    for action in actions:
        from_path = DOCS_DIR / action['from']

        if not from_path.exists():
            continue

        if action['action'] == 'DELETE':
            print(f"DELETE: {action['from']}")
            deleted_files.append(action)
            from_path.unlink()
            deleted_count += 1

        elif action['action'] == 'KEEP':
            print(f"KEEP: {action['from']}")

        elif action['action'] == 'MOVE':
            to_path = DOCS_DIR / action['to']
            to_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"MOVE: {action['from']} -> {action['to']}")
            shutil.move(str(from_path), str(to_path))
            moved_count += 1

        elif action['action'] == 'ARCHIVE':
            to_path = DOCS_DIR / action['to']
            to_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"ARCHIVE: {action['from']} -> {action['to']}")
            archived_files.append(action)
            shutil.move(str(from_path), str(to_path))
            archived_count += 1

    # Create breadcrumb README in archive
    archive_readme = DOCS_DIR / f'archive/{TODAY}/README.md'
    with open(archive_readme, 'w', encoding='utf-8') as f:
        f.write(f"# Archived Files - {TODAY}\n\n")
        f.write("These files were archived during docs cleanup because their purpose was unclear or they appeared to be outdated.\n\n")
        f.write(f"Total files: {len(archived_files)}\n\n")
        for item in archived_files:
            f.write(f"- `{item['from']}` - {item['reason']}\n")

    # Create reports
    create_reports(actions, moved_count, deleted_count, archived_count, deleted_files, archived_files)

    print(f"\n[OK] Cleanup complete!")
    print(f"  Moved: {moved_count}")
    print(f"  Deleted: {deleted_count}")
    print(f"  Archived: {archived_count}")

def create_reports(actions, moved_count, deleted_count, archived_count, deleted_files, archived_files):
    """Create cleanup reports."""

    # Cleanup report markdown
    report_path = DOCS_DIR / f'cleanup_report_{TODAY}.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Docs Cleanup Report - {TODAY}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Moved**: {moved_count} files\n")
        f.write(f"- **Deleted**: {deleted_count} files\n")
        f.write(f"- **Archived**: {archived_count} files\n\n")

        f.write("## Organization Structure\n\n")
        f.write("```\n")
        f.write("docs/\n")
        f.write("  guides/          # Tutorials, how-to, checklists\n")
        f.write("  reference/       # API/specs/schemas\n")
        f.write("  layouts/         # Layout docs, audits\n")
        f.write("  reports/         # Audit outputs, summaries\n")
        f.write("  images/          # Images for docs\n")
        f.write(f"  archive/{TODAY}/  # Unclear/deprecated files\n")
        f.write("```\n\n")

        f.write("## All Actions\n\n")
        f.write("| Action | From | To | Reason |\n")
        f.write("|--------|------|----|---------|\n")
        for action in actions:
            f.write(f"| {action['action']} | `{action['from']}` | `{action['to']}` | {action['reason']} |\n")

    # Deleted files CSV
    if deleted_files:
        deleted_csv = DOCS_DIR / f'cleanup_deleted_{TODAY}.csv'
        with open(deleted_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['from', 'reason', 'hash'])
            writer.writeheader()
            for item in deleted_files:
                writer.writerow({'from': item['from'], 'reason': item['reason'], 'hash': item['hash']})

    # Archive index CSV
    if archived_files:
        archive_csv = DOCS_DIR / f'archive/{TODAY}/index.csv'
        with open(archive_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['from', 'to', 'reason'])
            writer.writeheader()
            for item in archived_files:
                writer.writerow({'from': item['from'], 'to': item['to'], 'reason': item['reason']})

    print(f"\n[OK] Reports created:")
    print(f"  - {report_path}")
    if deleted_files:
        print(f"  - {DOCS_DIR / f'cleanup_deleted_{TODAY}.csv'}")
    if archived_files:
        print(f"  - {DOCS_DIR / f'archive/{TODAY}/index.csv'}")

if __name__ == '__main__':
    import sys

    # Dry run first
    actions = scan_and_plan()

    # Check for --apply flag
    if '--apply' in sys.argv or '-y' in sys.argv:
        apply_plan(actions, dry_run=False)
    else:
        print("\n" + "=" * 80)
        print("\nTo apply this plan, run:")
        print(f"  python {Path(__file__).name} --apply")
        print("\n[DRY RUN] No changes made.")
