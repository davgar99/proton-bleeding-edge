import os


def resolve_build_jobs(value: str | None = None) -> int:
    """Return a safe make job count from PROTON_BUILD_JOBS or CPU availability."""
    raw = os.environ.get("PROTON_BUILD_JOBS") if value is None else value
    if raw is None or not raw.strip():
        return os.cpu_count() or 1

    try:
        jobs = int(raw)
    except ValueError as exc:
        raise ValueError("PROTON_BUILD_JOBS must be a positive integer") from exc

    if jobs < 1:
        raise ValueError("PROTON_BUILD_JOBS must be a positive integer")
    return jobs
