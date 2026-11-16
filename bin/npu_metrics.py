"""Read-only NPU collector. Never open the device unless Halogen reports an NPU object."""
import ctypes
import fcntl
import json
import os
import re
import struct
from urllib.request import ProxyHandler, build_opener
DIRECT = build_opener(ProxyHandler({}))
ENGINES = {"halogen": "http://127.0.0.1:8731/health"}
# The amdxdna sensor query, from include/uapi/drm/amdxdna_accel.h: DRM_IOCTL_AMDXDNA_GET_INFO with
# DRM_AMDXDNA_QUERY_SENSORS fills an array of struct amdxdna_drm_query_sensor. The driver fills these from the SoC's
# power-management firmware: one total-power sensor, then one busy percentage per NPU column.
ACCEL = "/dev/accel/accel0"
GET_INFO = 0xC0106447  # DRM_IOWR(DRM_COMMAND_BASE + 7, 16-byte struct amdxdna_drm_get_info)
QUERY_SENSORS = 4
SENSOR = struct.Struct("64sIIII64s16sbB6x")  # label, input, max, average, highest, status, units, unitm, type
POWER, COLUMN = 0, 1


def sensors() -> list[tuple[int, float]]:
    """Each sensor's type and reading in base units. The driver drops sensors that do not fit, so ask for room to spare."""
    buffer = ctypes.create_string_buffer(SENSOR.size * 16)
    request = bytearray(struct.pack("IIQ", QUERY_SENSORS, len(buffer), ctypes.addressof(buffer)))
    fd = os.open(ACCEL, os.O_RDWR)
    try:
        fcntl.ioctl(fd, GET_INFO, request)
    finally:
        os.close(fd)
    _, size, _ = struct.unpack("IIQ", request)
    readings = []
    for offset in range(0, size - size % SENSOR.size, SENSOR.size):
        _, value, _, _, _, _, _, unitm, kind = SENSOR.unpack_from(buffer.raw, offset)
        readings.append((kind, value * 10.0 ** unitm))
    return readings


def npu_metrics() -> str | None:
    """NPU readings while Halogen serves NPU models, else None. Reading the sensors wakes a suspended NPU for five
    seconds, so a scrape every two seconds would keep it awake while nothing uses it."""
    try:
        with DIRECT.open(ENGINES["halogen"], timeout=2) as response:
            npu = json.load(response).get("npu")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(npu, dict):
        return None
    lines = []
    try:
        readings = sensors()
    except OSError:
        readings = []
    busy = [value for kind, value in readings if kind == COLUMN]
    if busy:
        lines += ["# TYPE npu_busy_percent gauge", f"npu_busy_percent {sum(busy) / len(busy):g}"]
    power = [value for kind, value in readings if kind == POWER]
    if power:
        lines += ["# TYPE npu_power_watts gauge", f"npu_power_watts {power[0]:g}"]
    loaded = set(npu.get("loaded") or [])
    models = [model for model in npu.get("models") or [] if isinstance(model, str) and re.fullmatch(r"[a-z0-9][a-z0-9.-]*", model)]
    if models:
        lines.append("# TYPE npu_model_loaded gauge")
        lines += [f'npu_model_loaded{{model="{model}"}} {int(model in loaded)}' for model in models]
    if isinstance(npu.get("queued"), int):
        lines += ["# TYPE npu_queued gauge", f"npu_queued {npu['queued']}"]
    return "\n".join(lines) + "\n"
