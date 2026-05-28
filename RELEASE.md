# Release and Packaging Notes

This file records project-local rules for future release work.

## Do Not Package Casually

- Do not run `build_release.bat` unless the user explicitly asks for a package or release build.
- Normal code changes, tests, docs edits, and branch checkpoints should not rebuild `dist`.
- Packaging is slow and rewrites large ignored outputs under `dist`, so treat it as a release step.

## Version First

Before any intentional package or GitHub Release replacement, update the version first.

Current version locations:

- `installer/czn_auto.iss`: `#define MyAppVersion "..."`
- `README.md`: installer filename examples such as `CZNAutoSetup-x.y.z.exe`
- GitHub Release tag/name if publishing, for example `v0.1.1`

Recommended flow:

1. Finish and test source changes.
2. Decide the next version number.
3. Update all visible version references.
4. Run lightweight checks.
5. Run `build_release.bat` only after the version update is committed or ready to commit.
6. If replacing GitHub Release assets, make sure the tag points at the intended commit.

## Quick Checks Before Packaging

Run these before a package build:

```powershell
python -m py_compile czn_detector.py diagnose_input.py state_check.py
python -m json.tool config.example.json > $null
```

For input-backend changes, also run a short bounded live test instead of immediately doing a full package build.
