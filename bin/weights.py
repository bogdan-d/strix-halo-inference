#!/usr/bin/env python3
"""Named, manifest-backed weight selections shared by the launcher and dashboard."""
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
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
        for key in ('model', 'manifest', 'directory', 'mtp', 'dflash', 'adapter'):
            if entry.get(key):
                relative(entry[key])
        if not entry.get('model') or not entry.get('manifest'):
            raise ValueError(f'Incomplete weight profile: {name}')
        if entry.get('extension') and (engine != 'gufo' or entry['extension'] != 'flash_next_iq'):
            raise ValueError(f'Unsupported extension for {engine}/{name}')
        if entry.get('adapter') and engine != 'gufo':
            raise ValueError(f'Unsupported adapter for {engine}/{name}')
        if entry.get('dflash') and (engine != 'gufo' or entry.get('mtp')):
            raise ValueError(f'dflash requires a Gufo profile without an MTP head: {name}')
        if 'served_model' in entry and (engine != 'gufo' or not isinstance(entry['served_model'], str)
                                        or not re.fullmatch(r'[a-z0-9][a-z0-9.-]*', entry['served_model'])):
            raise ValueError(f'Invalid served model ID for {engine}/{name}')
        if 'context' in entry and not (type(entry['context']) is int and 1024 <= entry['context'] <= 262144):
            raise ValueError(f'Invalid context window for {engine}/{name}')
    return entries


def profile(engine: str, name: str) -> dict:
    try:
        return profiles(engine)[name]
    except KeyError:
        raise ValueError(f'Unknown weight profile {engine}/{name}') from None


def extension_store(entry: dict) -> Path | None:
    """Keep native modules separate from prompt caches and tied to the exact engine image."""
    if not entry.get('extension'):
        return None
    pins = dict(item.split('=', 1) for item in shlex.split((ROOT / 'config/pins.env').read_text(), comments=True))
    cache = Path(os.environ.get('CACHE_ROOT') or Path.home() / '.cache/strix-halo-inference')
    return cache / 'gufo-extensions' / pins['GUFO_IMAGE'].split('@sha256:')[1] / pins['GUFO_IQ_REVISION']


def extension_ready(entry: dict) -> bool:
    store = extension_store(entry)
    if store is None:
        return True
    try:
        installed = json.loads((store / 'installed.json').read_text())
        return (installed.get('schema') == 1
                and [item['name'] for item in installed['extensions']] == ['flash_next_iq']
                and any((store / 'flash_next_iq/modules').glob('*.so')))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def available(entry: dict) -> bool:
    """Fast presence/size check, matching models.sh check; full hashes are verified separately."""
    try:
        rows = (ROOT / 'config' / entry['manifest']).read_text().splitlines()
        return extension_ready(entry) and bool(rows) and all((MODELS / entry.get('directory', '') / relative(row.split('\t')[2])).stat().st_size == int(row.split('\t')[1]) for row in rows)
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
                if not extension_ready(entry):
                    raise ValueError('Gufo IQ extension missing for the pinned image. See docs/gufo-extensions.md before installing.')
                for key in ('model', 'mtp'):
                    print(entry.get(key, ''))
                print(extension_store(entry) or '')
                print(entry.get('adapter', ''))
                print(entry.get('dflash', ''))
                print(entry.get('served_model', 'halogen-qwen3.8-flash-next' if engine == 'halogen' else 'qwen3.8-flash-next'))
                print(entry.get('context', 262144))
            elif action == 'extension':
                print(extension_store(entry) or '')
            elif action == 'manifest':
                print(entry.get('directory', ''))
                print(entry['manifest'])
            else:
                raise ValueError('Unknown weights action')
    except (ValueError, KeyError, IndexError) as error:
        sys.exit(str(error))
