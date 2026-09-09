# Chalkline desktop prototype

Native Python/PySide6 + Qt Quick + FFmpeg. This directory is separate from the
v212 PWA. Do not deploy the root PWA or bump its service worker for desktop work.

This is a native work in progress, **not a feature-complete replacement**.
Read [the parity contract](docs/parity.md) before extending or removing functionality.
The inherited inventory is retained in [legacy-inventory.json](docs/legacy-inventory.json).

## Development

1. Run `scripts/setup.ps1` to create the isolated environment on E:.
2. Run `scripts/run.ps1` to open the native prototype, or pass `-Project <path>`
   to open a saved `.chalkline` project in the latest source version.
3. Run `scripts/validate.ps1 -Media` for core, QML startup and media integration checks.
4. `scripts/build.ps1` creates a fresh portable staging folder; its location is
   recorded in `E:\Chalkline\build\latest-package.txt`. `scripts/check-package.ps1`
   checks native startup and rejects browser engine binaries.

The first review build is installed separately at `E:\Chalkline\Native\Chalkline.exe`.
Do not overwrite that folder on later builds: it can contain projects and exports.
The one-time `install-preview.ps1` refuses to replace an existing installation.

The media check uses the existing 60-second H.264 test clip; it writes only to a
timestamped `E:\Chalkline\test-results` directory and job-specific scratch folders.
It never changes source footage. FFmpeg and FFprobe are discovered in `tools/`,
the existing WinGet links or PATH. A portable release must bundle them.

Source layout:

- `src/chalkline/domain`: project documents and timeline semantics.
- `src/chalkline/application`: application use cases / Qt bindings.
- `src/chalkline/infrastructure`: media processes and export jobs.
- `src/chalkline/rendering`: shared annotation painter.
- `src/chalkline/ui`: QML interface.
- `tests`: repeatable tests; no match footage committed.
- `packaging`, `scripts`, `docs`: builds, development commands and decisions.

`.chalkline` is a ZIP with `project.json` (schema v1). It links original media;
it does not duplicate footage. Saves are atomic and unknown legacy session fields
are retained. Future asset packaging, recovery and schema migrations are tracked
in the parity contract.

## Scope and updating

100% user-functionality parity is the destination. Only .bat conversion workflows
are approved for removal. Browser-specific internals are replaced with native
mechanisms while preserving user outcomes. Optional Sync is retained.

Development is edit → run/check → bump desktop version → commit/push → build.
No push or release publication has been performed by this prototype work.
