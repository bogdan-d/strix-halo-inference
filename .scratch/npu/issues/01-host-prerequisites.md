# 01: Install XRT and the fabric clock script

**What to build:** Make the host able to run Halogen's NPU models. Install `xrt` and `xrt-plugin-amdxdna` from the CachyOS repositories. Install Halogen's `halogen-fabric-clock` script from the release matching the Halogen pin, plus a sudoers rule that lets the user run only its `hold` and `release` without a password. Do not enable its boot unit: holding the clock costs about 2.3 W at idle, so the launcher holds it only while Halogen runs NPU models (ticket 02). Both are root-owned host changes, so the user performs them.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] `pacman -Q xrt xrt-plugin-amdxdna` shows both packages, and `libxrt_coreutil.so.2`, `libxrt_core.so.2` and `libxrt_driver_xdna.so.2` exist in `/usr/lib`.
- [x] `/usr/local/sbin/halogen-fabric-clock` is root-owned, and `sudo -n halogen-fabric-clock hold` then `release` work without a password.
- [x] `halogen-fabric-clock.service` is not enabled, and the clock is `auto` after boot.
- [x] Kernel, BIOS and IOMMU settings are unchanged.
- [x] The installed versions, the script's source tag and the power measurement are recorded in `docs/engine-updates.md`.

## Comments

- October 14: the user installed XRT 2.21.75 (`xrt 1:2.21.75-14.1`, `xrt-plugin-amdxdna 1:2.21.75-2.1`). Holding the clock measured +2.65 W and +1.99 W idle package power in two back-to-back rounds, so the user chose a per-run hold over the boot unit. The journal shows no suspend on this host, so resume is not handled.
