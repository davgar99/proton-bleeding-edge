# Proton Bleeding Edge Automated Script

This is a small learning project where I am experimenting with Python automation, Valve Proton, Git submodules, and Linux build tooling.

The goal is not to replace Proton's official build instructions. This repo is mainly for learning how the Proton build process works and improving my Python/Linux workflow over time.

I do plan on improving the script further over time.

## Requirements

- Linux
- Python 3
- Git
- Docker or Podman
- Build tools such as make and GCC

## Usage

> [!WARNING]
> Compilation time varies significantly by CPU and available build cache.

```bash
python main.py
```

The script clones Valve Proton's `bleeding-edge` branch into `./Proton` on first use. If that directory already exists, it is reused only when it is a real Git checkout on the `bleeding-edge` branch with a clean worktree, an `origin` that resolves to Valve's Proton repository, and history that can fast-forward to the fetched branch. Equivalent HTTPS and SSH GitHub remote forms are accepted. The script refuses to overwrite divergent, locally modified, or unrelated checkouts.

Before configuring a build, the existing checkout is fast-forwarded when needed and its Git submodules are synchronized to the exact commits recorded by Proton. This avoids accidentally compiling a mixture of current Proton sources and stale submodules.

## Disclaimer

This is an unofficial learning project. It is not affiliated with Valve, Steam, or Proton. All credit goes to Valve.
