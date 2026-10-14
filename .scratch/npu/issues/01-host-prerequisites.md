# 01: Install XRT and hold the fabric clock

**What to build:** Make the host able to run Halogen's NPU models. Install `xrt` and `xrt-plugin-amdxdna` from the CachyOS repositories, and install Halogen's `halogen-fabric-clock` script and systemd unit from the release matching the Halogen pin. Both are root-owned host changes, so the user performs or explicitly approves them.

**Blocked by:** None (can start immediately).

**Status:** ready-for-human

- [ ] `pacman -Q xrt xrt-plugin-amdxdna` shows both packages, and `libxrt_coreutil.so.2`, `libxrt_core.so.2` and `libxrt_driver_xdna.so.2` exist in `/usr/lib`.
- [ ] `halogen-fabric-clock status` reports the clock held, and it stays held after a reboot.
- [ ] Kernel, BIOS and IOMMU settings are unchanged.
- [ ] The installed versions and the unit's source tag are recorded in `docs/engine-updates.md`.
