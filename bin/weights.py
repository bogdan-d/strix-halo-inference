#!/usr/bin/env python3
"""Named, manifest-backed weight selections shared by the launcher and dashboard."""
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MODELS = Path(os.environ.get('MODELS_DIR', '/home/bogdan/models'))


def relative(value: str) -> str:
    if not isinstance(value, str) or not value or PurePosixPath(value).is_absolute() or '..' in PurePosixPath(value).parts or any(c in value for c in '\n\r\t'):
        raise ValueError(f'Expected a relative path: {value!r}')
    return value


def profiles(engine: str) -> dict:
    catalog = json.loads((ROOT / 'config/weights.json').read_text())
    entries = catalog[engine]
    for name, entry in entries.items():
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name):
            raise ValueError(f'Invalid weight profile: {name}')
        for key in ('model', 'manifest', 'directory', 'mtp'):
            if entry.get(key):
                relative(entry[key])
        if not entry.get('model') or not entry.get('manifest'):
            raise ValueError(f'Incomplete weight profile: {name}')
    return entries


def profile(engine: str, name: str) -> dict:
    try:
        return profiles(engine)[name]
    except KeyError:
        raise ValueError(f'Unknown weight profile {engine}/{name}') from None


def available(entry: dict) -> bool:
    """Fast presence/size check, matching models.sh check; full hashes are verified separately."""
    try:
        rows = (ROOT / 'config' / entry['manifest']).read_text().splitlines()
        return bool(rows) and all((MODELS / entry.get('directory', '') / relative(row.split('\t')[2])).stat().st_size == int(row.split('\t')[1]) for row in rows)
    except (OSError, ValueError, IndexError):
        return False


if __name__ == '__main__':
    try:
        engine, action, *args = sys.argv[1:]
        if action == 'list':
            for name, entry in profiles(engine).items():
                print(f'{name}\t{"installed" if available(entry) else "missing"}\t{entry["label"]}')
        else:
            entry = profile(engine, args[0])
            # One field per line: Bash reads this without evaluating configuration as shell code.
            if action == 'launch':
                for key in ('model', 'mtp'):
                    print(entry.get(key, ''))
            elif action == 'manifest':
                print(entry.get('directory', ''))
                print(entry['manifest'])
            else:
                raise ValueError('Unknown weights action')
    except (ValueError, KeyError, IndexError) as error:
        sys.exit(str(error))
