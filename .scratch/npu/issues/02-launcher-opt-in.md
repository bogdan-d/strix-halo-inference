# 02: Opt-in NPU models in the launcher

**What to build:** Let `bin/run.sh halogen start` load NPU models only when asked, for example through an `NPU_MODELS` setting that becomes `HALOGEN_NPU_MODELS`. When it is set, the launcher mounts the three host XRT libraries twice, at `/opt/xilinx/xrt/lib/` and at `/usr/lib/` (Halogen's documented pattern for distribution XRT), and runs `bin/models.sh check npu` before starting. When it is unset, the container is started exactly as today.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] With the setting unset, the Podman arguments are unchanged; `tests/run.py` covers both cases.
- [ ] Unknown model names and missing files fail before the container starts, with a clear message.
- [ ] `HALOGEN_DOWNLOAD` stays unset and the models volume stays read-only.
- [ ] `bin/run.sh halogen status` shows which NPU models are loaded.
- [ ] README and `docs/engine-updates.md` describe the setting and what was verified.
