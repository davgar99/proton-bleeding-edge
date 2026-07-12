# Proton Bleeding Edge Automated Script

> A small personal learning project for automating Proton bleeding-edge builds on Linux.

## Overview

This repository explores:

- Python automation
- Valve Proton source builds
- Git submodules
- Linux build tooling

It is **not** meant to replace Proton's official build instructions. The goal is to better understand the build process and improve Python and Linux workflow skills over time.

## Requirements

Before running the script, make sure you have:

- Linux
- Python 3
- Git
- Docker or Podman
- Build tools such as `make` and `gcc`

## What the Script Does

The script can:

1. Clone or update the Proton bleeding-edge repository
2. Let you choose a custom build name before compilation
3. Build Proton with parallel jobs based on your CPU count
4. Optionally install the finished build into Steam's `compatibilitytools.d` directory
5. Let you choose a custom install directory name

## Usage

### Build Proton

> **Warning**
> Compilation time can vary a lot depending on your hardware. Expect anything from roughly 1 to 20 minutes in typical cases, with slower systems sometimes taking even longer.

```bash
python main.py
```

During the run, the script will prompt you for:

- A custom Proton build name (optional)
- A custom install directory name (optional)
- Whether the finished build should be copied into Steam's compatibility tools directory

## Disclaimer

This is an unofficial learning project. It is **not affiliated** with Valve, Steam, or Proton. Credit for Proton belongs to Valve and its contributors.
