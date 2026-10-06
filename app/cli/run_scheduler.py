"""Run the scheduler (PRD W-004, W-008): draft and publish marketing posts, and run the switched-on automation recipes.

    uv run python -m app.cli.run_scheduler            # forever, one pass every 60 seconds
    uv run python -m app.cli.run_scheduler --once     # a single pass (cron, or a one-off check)
    uv run python -m app.cli.run_scheduler --interval 300

It connects as the application role, like the API, and works inside each shop's own transaction; the only cross-shop read
is the list of shops that have something to do. Run exactly one copy: two copies would race to publish (a post is also
protected from double publishing by its stored Facebook id, but one copy is the supported setup). A failure in one shop is
logged and the others carry on. Nothing here prints a token.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.services import automation_service
from app.services.marketing_publisher import tick

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("bazaarflow.scheduler")


async def run(once: bool, interval: int) -> None:
    while True:
        result = await tick()
        logger.info(
            "scheduler pass: generated=%s published=%s retried=%s failed=%s paused=%s",
            result.generated,
            result.published,
            result.retried,
            result.failed,
            result.paused,
        )
        runs = await automation_service.tick()
        logger.info("automation pass: %s run(s) recorded", runs)
        if once:
            return
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BazaarFlow marketing scheduler")
    parser.add_argument("--once", action="store_true", help="run a single pass and exit")
    parser.add_argument("--interval", type=int, default=60, help="seconds between passes (default 60)")
    args = parser.parse_args()
    asyncio.run(run(args.once, max(args.interval, 10)))


if __name__ == "__main__":
    main()
