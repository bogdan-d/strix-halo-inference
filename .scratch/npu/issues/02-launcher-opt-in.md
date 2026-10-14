# 02: Opt-in NPU models in the launcher

**What to build:** Let `bin/run.sh halogen start` load NPU models only when asked, for example through an `NPU_MODELS` setting that becomes `HALOGEN_NPU_MODELS`. When it is set, the launcher mounts the three host XRT libraries twice, at `/opt/xilinx/xrt/lib/` and at `/usr/lib/` (Halogen's documented pattern for distribution XRT), runs `bin/models.sh check npu`, and holds the fabric clock with `sudo -n halogen-fabric-clock hold` before starting. `bin/run.sh halogen stop` releases a held clock. When it is unset, the container is started exactly as today.

**Blocked by:** 01

**Status:** ready-for-agent

- [x] With the setting unset, the Podman arguments are unchanged; `tests/run.py` covers both cases.
- [x] Unknown model names and missing files fail before the container starts, with a clear message.
- [x] `HALOGEN_DOWNLOAD` stays unset and the models volume stays read-only.
- [x] `bin/run.sh halogen status` shows which NPU models are configured. Whether Halogen reports the loaded ones is for ticket 03.
- [ ] A real start holds the clock and a stop releases it, once ticket 01's script and sudoers rule are installed.
- [x] README and `docs/engine-updates.md` describe the setting and what was verified.

## Comments

- October 14: implemented and covered by `tests/run.py` with stubs. Waiting on ticket 01's script and sudoers rule for a real start, which ticket 03 does anyway.
