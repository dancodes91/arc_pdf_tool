# Docs Organization Summary

**Date**: November 3, 2025
**Status**: ✓ Complete

## What Was Done

The `docs/` folder has been organized into a clear structure with all files categorized by purpose.

## Final Structure

```
docs/
├── README.md                    # Main docs entry point (kept in root)
├── guides/          (25 files)  # Tutorials, how-to, deployment guides
├── reference/       (9 files)   # API docs, parsers, specs, plans
├── reports/         (11 files)  # Status reports, summaries, test results
├── images/          (3 files)   # Screenshots and diagrams
├── layouts/         (0 files)   # Reserved for layout documentation
└── archive/20251103 (3 files)   # Scripts and files of unclear purpose
```

## File Counts

- **Total organized**: 48 files
  - Guides: 25
  - Reference: 9
  - Reports: 11
  - Images: 3
  - Archived: 2 (scripts/diagrams)
- **Deleted**: 0 (no obvious junk found)
- **Duplicates removed**: 0

## What Went Where

### guides/ - Setup, deployment, and strategy docs
- All DEPLOYMENT*.md files
- INSTALL.md, DOCKER_QUICKSTART.md, RUN_WEB_UI.md
- Strategy documents (MULTI_MANUFACTURER, HYBRID, etc.)
- How-to guides and checklists

### reference/ - Technical reference and specs
- PARSERS.md, OPERATIONS.md, DIFF.md
- DATA_DICTIONARY.md
- UNIVERSAL_PARSER_*.md files
- TESTING_HYBRID_PARSER_UI.md

### reports/ - Status updates and summaries
- All *_SUMMARY.md files
- All *_RESULTS.md files
- TEST_RESULTS.md, STATUS_AND_NEXT_STEPS.md
- project_index.json

### images/ - Visual assets
- error_1.png, error_2.png, error_3.png (moved from sc/ folder)

### archive/20251103/ - Unclear purpose
- create_deployment_pdf.py - Script with unclear usage
- dependency_graph.dot - Diagram source file
- README.md - Explains why items were archived

## Principles Used

1. **KEEP over DELETE**: When classification was unclear, files were archived rather than deleted
2. **No content changes**: Only file organization, no edits to content
3. **Semantic grouping**: Files grouped by purpose (guides, reference, reports)
4. **Main README stays**: README.md kept in root for visibility

## Next Steps

If you need to:
- **Find deployment guides**: Check `guides/`
- **Understand parser architecture**: Check `reference/`
- **Review project status**: Check `reports/`
- **Access images**: Check `images/`
- **Review archived items**: Check `archive/20251103/`

## Clean-up Script

The organization was performed by `cleanup_docs.py` (in project root), which can be re-run if needed:

```bash
python cleanup_docs.py        # Dry-run (shows plan)
python cleanup_docs.py --apply # Execute plan
```

---

**Organization complete!** All docs are now easy to find and navigate.
