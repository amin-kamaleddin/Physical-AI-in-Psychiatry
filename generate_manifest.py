"""Generate SHA-256 checksums for repository files."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
EXCLUDE_PARTS = {'.git', '__pycache__', '.pytest_cache', '_docx_render'}
EXCLUDE_SUFFIXES = {'.pyc', '.aux', '.log', '.out', '.toc'}


def main() -> None:
    records = []
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE_PARTS for part in rel.parts) or path.suffix in EXCLUDE_SUFFIXES:
            continue
        if rel.as_posix() in {'manifest.json', 'SHA256SUMS'}:
            continue
        digest = sha256(path.read_bytes()).hexdigest()
        records.append({'path': rel.as_posix(), 'bytes': path.stat().st_size, 'sha256': digest})
    (ROOT / 'manifest.json').write_text(json.dumps({'algorithm': 'sha256', 'files': records}, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in records), encoding='utf-8')
    print(f'Wrote checksums for {len(records)} files.')


if __name__ == '__main__':
    main()
