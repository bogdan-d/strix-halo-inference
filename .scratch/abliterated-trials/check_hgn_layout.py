"""Diagnose HGN table-order overlap reports; optionally make a reordered reflink copy.

Temporary diagnostic for Halogen 0.20.4's verifier. The source is always read-only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("--ordered-copy", type=Path)
args = parser.parse_args()
source, destination = args.source, args.ordered_copy

with source.open("rb") as handle:
    header = handle.read(104)
    magic, version, count, table_offset, data_offset, size = struct.unpack_from("<IIQQQQ", header)
    assert magic == 0x314E4748 and version == 2 and size == source.stat().st_size
    assert 104 <= table_offset and table_offset + count * 160 <= data_offset <= size
    handle.seek(table_offset)
    table = handle.read(count * 160)

entries = [table[index * 160:(index + 1) * 160] for index in range(count)]
rows = []
for entry in entries:
    name = entry[:96].split(b"\0", 1)[0].decode("ascii")
    offset, length = struct.unpack_from("<QQ", entry, 136)
    assert offset % 64 == 0 and offset >= data_offset and length > 0 and offset + length <= size, (name, offset, length)
    rows.append((offset, offset + length, name, entry))

assert len({row[2] for row in rows}) == count
ordered = sorted(rows)
assert all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:])), "Real payload overlap"
reversed_pairs = sum(left[1] > right[0] for left, right in zip(rows, rows[1:]))
print(json.dumps({
    "tensors": count,
    "table_order_overlap_reports": reversed_pairs,
    "physical_overlaps": 0,
    "out_of_bounds": 0,
    "duplicate_names": 0,
    "payload_bytes": sum(end - start for start, end, _, _ in rows),
    "file_bytes": size,
    "table_sha256": hashlib.sha256(table).hexdigest(),
}, indent=2), flush=True)

if destination is None:
    raise SystemExit(0)
assert not destination.exists(), destination
subprocess.run(["cp", "--reflink=always", "--", str(source), str(destination)], check=True)
assert not source.samefile(destination)
with destination.open("r+b") as handle:
    handle.seek(table_offset)
    handle.write(b"".join(row[3] for row in ordered))
with source.open("rb") as handle:
    handle.seek(table_offset)
    assert handle.read(count * 160) == table
with destination.open("rb") as handle:
    assert handle.read(104) == header
    handle.seek(table_offset)
    new_table = handle.read(count * 160)
    assert sorted(new_table[index * 160:(index + 1) * 160] for index in range(count)) == sorted(entries)
print("Diagnostic copy differs only in tensor-table entry order; header and every table record are preserved.", flush=True)
