import os


def _detected_jobs() -> int:
    return os.cpu_count() or 1


def resolve_build_jobs(value: str | None = None) -> int:
    """Return a safe make job count from PROTON_BUILD_JOBS or CPU availability."""
    raw = os.environ.get("PROTON_BUILD_JOBS") if value is None else value
    if raw is None or not raw.strip():
        return _detected_jobs()

    normalized = raw.strip().lower()
    if normalized == "auto":
        return _detected_jobs()

    try:
        jobs = int(normalized)
    except ValueError as exc:
        raise ValueError("PROTON_BUILD_JOBS must be 'auto' or a positive integer") from exc

    if jobs < 1:
        raise ValueError("PROTON_BUILD_JOBS must be 'auto' or a positive integer")
    return jobs
