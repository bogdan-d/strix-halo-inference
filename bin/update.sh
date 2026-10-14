#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec python - "$ROOT" "$@" <<'PY'
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ENGINES = (("halogen", "HALOGEN", "peonist-ai/halogen-flash-server"),
           ("gufo", "GUFO", "gufo-org/gufo"),
           ("strixite", "STRIXITE", "shawnshekari/strixite"))

STABLE_TAG = re.compile(r"v?[0-9]+\.[0-9]+\.[0-9]+")

@dataclass(frozen=True)
class Image:
    prefix: str
    current: str
    reference: str
    version: str


def command(args: list[str], *, capture: bool = True) -> str:
    result = subprocess.run(args, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None, timeout=1800)
    return result.stdout or ""


def http_get(url: str) -> tuple[int, str]:
    output = command(["curl", "--silent", "--show-error", "--location",
                      "--connect-timeout", "15", "--max-time", "60",
                      "--write-out", "\n%{http_code}", url])
    body, separator, status = output.rpartition("\n")
    if not separator or not re.fullmatch(r"[0-9]{3}", status):
        raise ValueError(f"Invalid HTTP response status from {url}")
    if status not in ("200", "404"):
        raise ValueError(f"HTTP {status} from {url}")
    return int(status), body


def version_tuple(version: str) -> tuple[int, ...]:
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError(f"Expected a stable release version, got {version!r}")
    return tuple(int(part) for part in version.split("."))


def release_notes(upstream: str, version: str) -> None:
    tag = "v" + version
    url = f"https://github.com/{upstream}/releases/tag/{tag}"
    status, body = http_get(f"https://api.github.com/repos/{upstream}/releases/tags/{tag}")
    if status == 200:
        release = json.loads(body)
        if not isinstance(release, dict):
            raise ValueError(f"Invalid release metadata for {tag}")
        if release.get("tag_name") != tag or release.get("draft") or release.get("prerelease"):
            raise ValueError(f"Release metadata does not match stable {tag}")
        body = release.get("body") or "No release notes published."
    elif upstream == "peonist-ai/halogen-flash-server":
        # Halogen publishes tagged changelogs but currently no GitHub Releases.
        url = f"https://github.com/{upstream}/blob/{tag}/CHANGELOG.md"
        status, body = http_get(f"https://raw.githubusercontent.com/{upstream}/{tag}/CHANGELOG.md")
        if status != 200:
            raise ValueError(f"No release notes or tagged changelog for {tag}")
        section = re.search(r"^## " + re.escape(version) + r"\s*\n(.*?)(?=^## |\Z)",
                            body, flags=re.MULTILINE | re.DOTALL)
        if section is None:
            raise ValueError(f"No {version} section in tagged changelog")
        body = "No GitHub Release published. Tagged changelog:\n" + section.group(1).strip()
    else:
        url = f"https://github.com/{upstream}/releases"
        body = f"No GitHub Release published for {tag}."
    if not isinstance(body, str):
        raise ValueError(f"Invalid release notes for {tag}")
    # Release prose is untrusted terminal output, never executable input.
    body = re.sub(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", "", body)
    print(f"Release notes {tag}: {url}\n{body.strip()}\n", flush=True)


def versions_to_report(upstream: str, pinned: str, latest: str) -> list[str]:
    """Every stable release after the current pin up to latest, oldest first."""
    lower, upper = version_tuple(pinned), version_tuple(latest)
    if upper <= lower:
        return [latest]
    # GitHub lists tags newest first; 100 covers any realistic gap between two runs.
    status, body = http_get(f"https://api.github.com/repos/{upstream}/tags?per_page=100")
    tags = json.loads(body) if status == 200 else None
    if not isinstance(tags, list):
        raise ValueError(f"Invalid tag list for {upstream}")
    versions = {latest}
    for tag in tags:
        name = tag.get("name") if isinstance(tag, dict) else None
        if isinstance(name, str) and STABLE_TAG.fullmatch(name):
            version = name.removeprefix("v")
            if lower < version_tuple(version) <= upper:
                versions.add(version)
    return sorted(versions, key=version_tuple)


def inspect_image(engine: str, prefix: str, current: str, pinned_version: str) -> Image:
    match = re.fullmatch(r"(ghcr\.io/[a-z0-9/._-]+)@sha256:[0-9a-f]{64}", current)
    if match is None:
        raise ValueError(f"Invalid {prefix}_IMAGE pin")
    repository = match.group(1)
    metadata = json.loads(command(["skopeo", "inspect", "--no-tags", "--retry-times", "3",
                                   "--override-arch", "amd64", "--override-os", "linux",
                                   "docker://" + repository + ":latest"]))
    if not isinstance(metadata, dict):
        raise ValueError(f"Invalid registry metadata for {engine}")
    digest = metadata.get("Digest")
    labels = metadata.get("Labels")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError(f"Invalid registry digest for {engine}")
    if metadata.get("Name") != repository or metadata.get("Architecture") != "amd64" or metadata.get("Os") != "linux":
        raise ValueError(f"Unexpected repository or platform for {engine}")
    if not isinstance(labels, dict) or not isinstance(labels.get("org.opencontainers.image.version"), str):
        raise ValueError(f"Missing release version on {engine} image")
    version = labels["org.opencontainers.image.version"].removeprefix("v")
    if version_tuple(version) < version_tuple(pinned_version):
        raise ValueError(f"Refusing {engine} downgrade from {pinned_version} to {version}")
    reference = repository + "@" + digest
    revision = labels.get("org.gufo.engine.revision", labels.get("org.opencontainers.image.revision"))
    revision = revision if isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{7,40}", revision) else "not advertised"
    state = "up to date" if reference == current else "update available"
    print(f"\n{engine}: {pinned_version} -> {version}, {state}\n"
          f"  pinned: {current}\n  latest: {reference}\n  image revision: {revision}", flush=True)
    return Image(prefix, current, reference, version)


def main() -> None:
    root = Path(sys.argv[1])
    parser = argparse.ArgumentParser(prog="bin/update.sh", description="Update digest-pinned upstream images and show their release notes.")
    parser.add_argument("--check", action="store_true", help="Inspect only, without pulling images or writing files")
    parser.add_argument("--pull", action="store_true", help="Pull all three resolved images even when their pins are unchanged")
    parser.add_argument("--fresh-cache", action="store_true", help="Archive all three engine prompt caches. Engines must be stopped")
    args = parser.parse_args(sys.argv[2:])
    if args.check and (args.pull or args.fresh_cache):
        parser.error("--check cannot be combined with --pull or --fresh-cache")

    with ExitStack() as resources:
        if not args.check:
            lock = resources.enter_context((root / "config/.update.lock").open("a"))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if command(["podman", "info", "--format", "{{.Host.Security.Rootless}}"]).strip() != "true":
                raise ValueError("Use rootless Podman, not sudo")
        cache = Path(os.environ.get("CACHE_ROOT") or str(Path.home() / ".cache/strix-halo-inference")).expanduser().resolve()
        if args.fresh_cache:
            models = Path(os.environ.get("MODELS_DIR") or "/home/bogdan/models").expanduser().resolve()
            if cache in (Path("/"), Path.home().resolve(), models):
                raise ValueError("CACHE_ROOT must be a dedicated cache directory")
            cache.mkdir(parents=True, exist_ok=True)
            lock = resources.enter_context((cache / "start.lock").open("a"))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            active = command(["podman", "ps", "--filter", "label=io.strix-halo-inference.managed=true",
                              "--format", "{{.Names}}"]).strip()
            if active:
                raise ValueError(f"Stop the active engine before archiving caches: {active}")
            for engine, _, _ in ENGINES:
                path = cache / engine
                if path.is_symlink() or (path.exists() and not path.is_dir()):
                    raise ValueError(f"Expected an ordinary cache directory: {path}")

        path = root / "config/pins.env"
        original = path.read_text()
        pins = dict(re.findall(r"^([A-Z_]+)=(\S+)$", original, flags=re.MULTILINE))
        images = []
        for engine, prefix, upstream in ENGINES:
            if prefix + "_IMAGE" not in pins or prefix + "_VERSION" not in pins:
                raise ValueError(f"Missing image or version pin for {engine}")
            image = inspect_image(engine, prefix, pins[prefix + "_IMAGE"], pins[prefix + "_VERSION"])
            for version in versions_to_report(upstream, pins[prefix + "_VERSION"], image.version):
                release_notes(upstream, version)
            images.append(image)
        if args.check:
            print("Check only. No images pulled, pins written or caches changed.")
            return

        # Resolve and validate the entire batch before pulling. Commit pins only after every pull succeeds.
        for image in images:
            if args.pull or image.current != image.reference:
                command(["podman", "pull", image.reference], capture=False)
        updated = original
        for image in images:
            for key, value in ((image.prefix + "_IMAGE", image.reference), (image.prefix + "_VERSION", image.version)):
                updated, count = re.subn(r"^" + key + r"=.*$", key + "=" + value, updated, flags=re.MULTILINE)
                if count != 1:
                    raise ValueError(f"Expected exactly one {key} assignment")
        if path.read_text() != original:
            raise ValueError("pins.env changed during update. Nothing overwritten")
        if updated != original:
            with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=".pins.env.", delete=False) as file:
                temporary = Path(file.name)
                try:
                    file.write(updated)
                    file.flush()
                    os.fsync(file.fileno())
                    temporary.chmod(path.stat().st_mode & 0o777)
                    temporary.replace(path)
                finally:
                    temporary.unlink(missing_ok=True)
            print("Updated config/pins.env. Review with git diff -- config/pins.env.")
        else:
            print("Image pins are already current.")
        if args.fresh_cache:
            archive = cache / ("archive-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
            archive.mkdir()
            for engine, _, _ in ENGINES:
                source = cache / engine
                if source.exists():
                    source.rename(archive / engine)
            print(f"Prompt caches archived, not deleted: {archive}")
        print("Running containers are unchanged. Stop and start an engine explicitly to use its new pin.")


try:
    main()
except (OSError, ValueError, subprocess.SubprocessError) as error:
    print(f"Update failed: {error}", file=sys.stderr)
    sys.exit(1)
PY
