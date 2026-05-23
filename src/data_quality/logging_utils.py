from __future__ import annotations

import functools
import logging
import sys
import time
from typing import Any, Callable, TypeVar


F = TypeVar("F", bound=Callable[..., Any])


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # Keep the console focused on assignment output while preserving our own
    # decorator logs for start/end/status/timing.
    logging.getLogger("great_expectations").setLevel(logging.WARNING)
    logging.getLogger("great_expectations.data_context.types.base").setLevel(logging.WARNING)
    logging.getLogger("posthog").setLevel(logging.CRITICAL)


def log_execution(step_name: str | None = None) -> Callable[[F], F]:
    """Decorate framework steps with uniform start/end/time/status logging."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = step_name or func.__qualname__
            start_time = time.perf_counter()
            logging.info("START | %s", name)
            try:
                result = func(*args, **kwargs)
            except Exception:
                elapsed = time.perf_counter() - start_time
                logging.exception("END | %s | status=failure | elapsed=%.3fs", name, elapsed)
                raise

            elapsed = time.perf_counter() - start_time
            logging.info("END | %s | status=success | elapsed=%.3fs", name, elapsed)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
