# Proton Bleeding Edge Builder

**Build the newest Proton bleeding-edge code, keep your checkout current, and turn upstream development into a Steam-ready custom Proton build with one repeatable workflow.**

This project automates the repetitive parts of working with Valve's Proton `bleeding-edge` branch: cloning the source tree, synchronizing Git submodules, updating an existing checkout safely, configuring the build, compiling Proton, and optionally installing the finished build into Steam's `compatibilitytools.d` directory.

It is intentionally small and transparent. Instead of hiding Proton behind a large framework, the script gives Linux gamers, contributors, tinkerers, and developers a practical starting point for following upstream development and producing their own current builds.

> [!NOTE]
> This is an unofficial community/developer tool. It does not replace Valve's official Proton documentation and is not affiliated with Valve, Steam, or Proton.

## Why use it?

- **Stay close to upstream.** Reuse a verified Proton checkout and fast-forward it to the latest `bleeding-edge` revision instead of starting from scratch every time.
- **Build with confidence.** Git submodules are synchronized to the exact commits recorded by Proton before compilation, reducing the chance of accidentally producing a mixed-source build.
- **Protect local work.** The updater fails closed when it sees uncommitted changes, divergent history, the wrong branch, an unexpected remote, or an unsafe checkout instead of silently overwriting developer work.
- **Iterate on Proton development.** Use the managed `./Proton` checkout as a clean upstream base for inspecting code, developing changes, experimenting with patches, and testing modifications. Commit or stash work before asking the script to update the checkout; divergent local commits are deliberately never overwritten automatically.
- **Refresh custom installs.** Rebuild current upstream code and replace an existing Steam custom-tool installation using a staged replacement that preserves the previous install if activation fails.
- **Control build pressure.** Use automatic CPU detection or cap parallel jobs for systems with limited memory or thermal headroom.
- **Keep the workflow understandable.** The automation is Python and standard Git/build tooling, making it easy to inspect, adapt, or extend for your own development workflow.

## A useful workflow for developers

This repository can act as the repeatable build-and-install layer around Proton development. Let the script establish and update a known-good `bleeding-edge` checkout, work inside `./Proton` to inspect or modify the source, apply and test patches, then keep your changes committed or stashed whenever you need to synchronize with upstream.

The safety checks are intentional: the script will not automatically rewrite a dirty checkout or discard divergent local commits. That makes the source tree useful for experimentation without turning an updater into a destructive reset tool. After your source is in the state you want to build, the same Proton configure/build process can produce a custom Steam compatibility tool for testing.

Typical uses include following new Proton development, maintaining a local test build, validating an upstream change, experimenting with a patch series, modifying Proton for a specific game or environment, and repeatedly rebuilding a custom installation during development.

## Requirements

- Linux
- Python 3.10 or newer
- Git
- Docker or Podman
- Build tooling required by Proton, including `make`

Refer to Valve's Proton build documentation for the authoritative host and container requirements for the Proton revision you are building.

## Quick start

```bash
python main.py
```

On first use, the script clones Valve Proton's `bleeding-edge` branch into `./Proton`. On later runs, that checkout becomes your reusable upstream workspace.

If `./Proton` already exists, it is reused only when it is a real Git checkout on the `bleeding-edge` branch with a clean worktree, an `origin` that resolves to Valve's Proton repository, and history that can fast-forward to the fetched branch. Equivalent HTTPS and SSH GitHub remote forms are accepted, including harmless owner/repository casing differences. Divergent, locally modified, unrelated, file-backed, and symlink checkouts are rejected rather than overwritten.

Before configuring a build, the checkout is fast-forwarded when needed and its Git submodules are synchronized recursively to the exact commits recorded by Proton.

## Build parallelism

By default, the build uses all CPUs available to the process. On Linux this respects CPU-affinity and cpuset limits, so running the script inside a constrained container or task does not accidentally start jobs for host CPUs it cannot use. If affinity information is unavailable, the script falls back to Python's detected CPU count.

To limit parallelism further on memory-constrained or thermally limited systems, set `PROTON_BUILD_JOBS` to a positive integer:

```bash
PROTON_BUILD_JOBS=4 python main.py
```

For scripts and shared configuration, `auto` explicitly restores automatic CPU detection using the CPUs available to the process:

```bash
PROTON_BUILD_JOBS=auto python main.py
```

Invalid values such as `0`, negative numbers, and non-numeric strings are rejected instead of being passed to `make`.

## Steam installation safety

After a successful build, the script can install the result under Steam's `compatibilitytools.d` directory. Replacements are staged beside the existing installation before activation. If copying or activation fails, the existing working installation is preserved or restored rather than being intentionally deleted first.

Restart Steam after installing or replacing a custom compatibility tool so Steam can discover the new build.

## Project philosophy

The goal is simple: **make following, building, modifying, and testing Proton bleeding-edge less repetitive without taking control of the source tree away from the developer.**

The project favors explicit safety checks, reproducible source state, small understandable automation, and behavior that fails closed when an update could destroy local work. It is useful as-is for enthusiasts and as a compact foundation for developers who want to extend the workflow further.

## Disclaimer

This is an unofficial open-source project and is not affiliated with, endorsed by, or supported by Valve Corporation, Steam, or the Proton project. Proton and Steam are trademarks of their respective owners. Always consult Valve's official documentation when working on Proton itself.
