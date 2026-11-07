#!/usr/bin/env python3
"""Rebuild a credential-free, offline-default copy of the scored PAIEC submission."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
CHUNK = 4 * 1024 * 1024


def sha256(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def transfer(source, destination, item):
    digest = hashlib.sha256()
    count = 0
    while block := source.read(CHUNK):
        count += len(block)
        if count > item['bytes']:
            raise ValueError(f"Oversized member: {item['path']}")
        digest.update(block)
        destination.write(block)
    if count != item['bytes'] or digest.hexdigest() != item['sha256']:
        raise ValueError(f"Wrong size or SHA-256 for {item['path']}")


def member_source(stack, args, original, item):
    name = item['path']
    if item['delivery'] == 'bundled':
        return stack.enter_context((ROOT / 'runtime' / name).open('rb'))
    if args.asset_dir and (args.asset_dir / name).is_file():
        return stack.enter_context((args.asset_dir / name).open('rb'))
    if original is not None:
        return stack.enter_context(original.open(name))
    if args.fetch_minilm and item['delivery'] == 'public-minilm':
        return stack.enter_context(urllib.request.urlopen(item['url'], timeout=60))
    raise FileNotFoundError(
        f"Missing {name}. Supply an authorized exact copy with --asset-dir "
        "or --scored-archive. The public MiniLM weight also supports --fetch-minilm."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset-dir', type=Path, help='Authorized exact assets in original member paths')
    parser.add_argument('--scored-archive', type=Path, help='Private frozen #1032237 archive; never upload it here')
    parser.add_argument('--fetch-minilm', action='store_true', help='Fetch the sole public weight from its pinned URL')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'ARTIFACT_MANIFEST.json').read_text())
    entries = manifest['members']
    paths = [item['path'] for item in entries]
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate manifest member')
    for name in paths:
        member = PurePosixPath(name)
        if member.is_absolute() or '..' in member.parts or '\\' in name:
            raise ValueError('Unsafe manifest member')
    if args.output.exists():
        parser.error('Output already exists; select a new path')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        original = None
        if args.scored_archive:
            frozen = manifest['original_scored_archive']
            if args.scored_archive.stat().st_size != frozen['bytes'] or sha256(args.scored_archive) != frozen['sha256']:
                raise ValueError('Input archive does not match frozen #1032237')
            original = stack.enter_context(zipfile.ZipFile(args.scored_archive))
        temp = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=args.output.parent)))
        private = temp / 'rebuilt.zip'
        with zipfile.ZipFile(private, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as out:
            for item in entries:
                with contextlib.ExitStack() as source_stack:
                    data = member_source(source_stack, args, original, item)
                    with out.open(item['path'], 'w') as target:
                        transfer(data, target, item)
            package_hashes = {item['path']: item['sha256'] for item in entries}
            out.writestr('PACKAGE_HASHES.json', json.dumps(package_hashes, indent=2, sort_keys=True) + '\n')
        private.chmod(0o600)
        os.link(private, args.output)
    print(f'Rebuilt {len(entries)+1} verified members with paid inference disabled: {args.output}')
    print(f'{args.output.stat().st_size} bytes, SHA-256 {sha256(args.output)}')


if __name__ == '__main__':
    main()
