#!/usr/bin/env python3
"""Report running-container configuration and sourced memory readings."""
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.error import URLError
from urllib.request import urlopen


def command(*args: str, seconds: int = 5) -> str:
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=seconds)
    if result.returncode:
        raise RuntimeError(result.stdout.strip() or f"{args[0]} failed")
    return result.stdout


def gib(value: str | int | None) -> str:
    if value is None:
        return "unavailable"
    return f"{int(value) / 2**30:.2f} GiB"


def setting(args: list[str], name: str) -> str | None:
    if name not in args:
        return None
    index = args.index(name) + 1
    return args[index] if index < len(args) else None


def show_configuration(engine: str, container: dict) -> None:
    config = container["Config"]
    env = dict(item.split("=", 1) for item in config.get("Env", []) if "=" in item)
    args = config.get("Cmd") or []
    print(f"Image: {container.get('ImageName', 'unavailable')}")
    print(f"Image ID: {container.get('Image', 'unavailable')}")
    print(f"Image version (OCI label): {config.get('Labels', {}).get('org.opencontainers.image.version', 'unavailable')}")
    if engine == "halogen":
        context = env.get("HALOGEN_CTX")
        mtp = "off" if env.get("HALOGEN_DRAFTER_DEFAULT") == "0" else "engine default (see readiness or logs)"
        disk = env.get("HALOGEN_CACHE_DISK_GIB")
        disk_limit = f"{disk} GiB" if disk is not None else "unavailable"
        ram_limit = staging = None
    else:
        context = setting(args, "--context")
        mtp = setting(args, "--speculative") or "unavailable"
        disk_limit = gib(setting(args, "--cache-disk-bytes"))
        ram_limit = setting(args, "--cache-ram-bytes")
        staging = setting(args, "--cache-disk-staging-bytes")
    print(f"Configured context: {context or 'unavailable'} tokens")
    print(f"Configured speculation: {mtp}")
    print(f"Cache disk limit: {disk_limit}")
    print(f"Cache RAM limit: {gib(ram_limit)}; staging limit: {gib(staging)}")
    print("Cache RAM usage: unavailable")
    mount = next((m for m in container.get("Mounts", []) if m.get("Destination") == "/cache"), None)
    if mount:
        try:
            used = command("du", "-s", "-B1", "--", mount["Source"], seconds=3).split()[0]
            print(f"Cache disk usage (du, entire mounted directory): {gib(used)}")
        except (RuntimeError, subprocess.TimeoutExpired, ValueError, IndexError) as error:
            print(f"Cache disk usage: unavailable ({error})")
    else:
        print("Cache disk usage: unavailable (no cache mount)")


def show_allocations(engine: str, name: str) -> None:
    try:
        logs = command("podman", "logs", "--tail", "1000", name)
        if engine == "halogen":
            match = re.search(r"memory: ([0-9.]+) GiB of weights locked in RAM, ([0-9.]+) GiB of KV pool, ([0-9.]+) GiB of working memory, ([0-9.]+) GiB in all", logs)
            if match:
                weights, kv, working, total = match.groups()
                print(f"Engine allocation (startup log, not live): {total} GiB total; weights {weights}, KV {kv}, working {working} GiB")
                return
        else:
            match = re.search(r"event=load_completed[^\n]*gpu_device_used_mib=(\d+)", logs)
            if match:
                print(f"Engine GPU allocation (startup log, not live): {gib(int(match[1]) * 2**20)}")
                return
        print("Engine allocation: unavailable (no measured startup allocation in recent logs)")
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Engine allocation: unavailable ({error})")


def show_host_memory() -> None:
    try:
        memory = dict(re.findall(r"^(\w+):\s+(\d+) kB", Path("/proc/meminfo").read_text(), re.M))
        print(f"Host RAM (/proc/meminfo): total {gib(int(memory['MemTotal']) * 1024)}, MemAvailable {gib(int(memory['MemAvailable']) * 1024)}")
        print(f"Host swap used (/proc/meminfo): {gib((int(memory['SwapTotal']) - int(memory['SwapFree'])) * 1024)}")
    except (OSError, ValueError, KeyError):
        print("Host memory: unavailable")
    devices = sorted(Path("/sys/class/drm").glob("card[0-9]*/device/mem_info_gtt_total"))
    if not devices:
        print("Kernel GTT: unavailable")
    for total in devices:
        try:
            used = total.with_name("mem_info_gtt_used").read_text().strip()
            print(f"Kernel GTT ({total.parents[1].name}, sysfs, all GPU users): {gib(used)} used / {gib(total.read_text().strip())} limit")
        except (OSError, ValueError):
            print(f"Kernel GTT ({total.parents[1].name}): unavailable")
    print("Memory caution: free GTT is not free physical RAM. Halogen's pinned weights can make MemAvailable overstate reclaimable memory.")


def main(engine: str, name: str, health: str) -> int:
    try:
        inspected = json.loads(command("podman", "inspect", name))
        if not isinstance(inspected, list) or not inspected or not isinstance(inspected[0], dict):
            raise ValueError("invalid container inspection")
        container = inspected[0]
        if not isinstance(container.get("Config"), dict) or not isinstance(container.get("State"), dict):
            raise ValueError("missing container configuration or state")
    except (RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
        print(f"{engine}: container unavailable ({error})")
        return 1
    state = container["State"]
    print(f"{engine}: container {state.get('Status', 'unavailable')}")
    show_configuration(engine, container)
    ready = False
    if state.get("Running") and not state.get("Paused"):
        try:
            with urlopen(health, timeout=3) as response:
                status = json.load(response)
            if not isinstance(status, dict):
                raise ValueError("invalid readiness response")
            ready = status.get("status") == ("ok" if engine == "halogen" else "ready")
            print(f"Readiness ({health}): {'ready' if ready else 'not ready'}")
            if engine == "halogen":
                print(f"Active drafter (health): {status.get('drafter_default', 'unavailable')}")
        except (URLError, TimeoutError, OSError, ValueError) as error:
            print(f"Readiness: unavailable ({error})")
        show_allocations(engine, name)
    else:
        print("Readiness: not ready (container not running or paused)")
        print("Engine allocation: unavailable (engine not active)")
    show_host_memory()
    return 0 if ready else 1


if __name__ == "__main__":
    try:
        sys.exit(main(*sys.argv[1:]))
    except (ValueError, KeyError, TypeError) as error:
        print(f"Status failed: {error}", file=sys.stderr)
        sys.exit(1)
