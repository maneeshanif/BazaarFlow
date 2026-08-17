"""Command-line utility for the Facebook Manager toolkit.

This script exposes a small CLI that lets you interact with the Facebook Graph API
using the features implemented in :mod:`src.facebook_manager`.  All commands hit
the real API, so ensure that:

* ``FACEBOOK_PAGE_ID`` and ``FACEBOOK_ACCESS_TOKEN`` are configured in your
  environment (or stored in a ``.env`` file).
* You're comfortable performing the action on the live page before running the
  command.

Example usage::

    # Verify credentials
    python main.py verify

    # Publish a quick text post
    python main.py post-text "Hello, Facebook!"

    # Post an image from a URL
    python main.py post-image --image-url https://example.com/cat.jpg --message "Meet our new mascot"

    # Fetch comments + insights for a post and write them to JSON
    python main.py fetch-post-engagement 837535619434131_122113814331036166 --output insights.json

All commands return a non-zero exit code when an error occurs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from dotenv import load_dotenv
from pydantic import ValidationError

from src import (
    FacebookManager,
    InsightPeriod,
    ImagePostRequest,
    TextPostRequest,
    load_config,
)
from src.exceptions import (
    FacebookAPIError,
    ImageUploadError,
    InvalidCredentialsError,
    PostCreationError,
)

DEFAULT_OUTPUT_FILE = "last_post_engagement.json"
DEFAULT_COMMENT_LIMIT = 100


def build_parser() -> argparse.ArgumentParser:
    """Create and return the top-level argument parser."""

    parser = argparse.ArgumentParser(
        prog="facebook-manager",
        description="Interact with the Facebook Manager toolkit from the command line.",
    )

    env_group = parser.add_mutually_exclusive_group()
    env_group.add_argument(
        "--env-file",
        type=str,
        help="Path to a .env file to load before executing the command.",
    )
    env_group.add_argument(
        "--no-env-file",
        action="store_true",
        help="Do not automatically load a .env file (environment variables only).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ------------------------------------------------------------------
    fetch = subparsers.add_parser(
        "fetch-post-engagement",
        help="Fetch comments and insights for a single post.",
    )
    fetch.add_argument(
        "post_id",
        help="Post identifier in the PageID_PostID format required by the Graph API.",
    )
    fetch.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_COMMENT_LIMIT,
        help=f"Maximum number of comments to retrieve (default: {DEFAULT_COMMENT_LIMIT}).",
    )
    fetch.add_argument(
        "--period",
        default=InsightPeriod.LAST_24_HOURS.value,
        help="Insight period to request (day, week, days_28, lifetime).",
    )
    fetch.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help=(
            "Destination for the JSON payload. Use '-' to print to stdout."
            f" Default: {DEFAULT_OUTPUT_FILE}."
        ),
    )
    fetch.add_argument(
        "--skip-output",
        action="store_true",
        help="Skip writing the JSON payload to disk/stdout.",
    )

    # ------------------------------------------------------------------
    text = subparsers.add_parser("post-text", help="Publish a text-only post.")
    text.add_argument("message", nargs="?", help="Message to publish. If omitted, read from stdin.")

    # ------------------------------------------------------------------
    image = subparsers.add_parser("post-image", help="Publish an image post.")
    image.add_argument("--message", help="Optional message to accompany the image.")
    image.add_argument("--image-url", dest="image_url", help="Public URL of the image to post.")
    image.add_argument("--image-path", dest="image_path", help="Local filesystem path to the image to upload.")

    # ------------------------------------------------------------------
    verify = subparsers.add_parser(
        "verify",
        help="Verify that the configured credentials are valid.",
    )
    verify.add_argument(
        "--quiet",
        action="store_true",
        help="Only use the exit code to report success/failure.",
    )

    # ------------------------------------------------------------------
    page = subparsers.add_parser(
        "page-insights",
        help="Fetch page-level insights for the configured page.",
    )
    page.add_argument(
        "--period",
        default=InsightPeriod.LAST_24_HOURS.value,
        help="Insight period to request (day, week, days_28, lifetime).",
    )

    return parser


def parse_insight_period(raw: str) -> InsightPeriod:
    """Parse a user-provided period string into an :class:`InsightPeriod`."""

    normalized = (raw or "").strip().lower()
    for period in InsightPeriod:
        aliases = {
            period.value.lower(),
            period.name.lower(),
            period.name.lower().replace("_", "-"),
        }
        if normalized in aliases:
            return period
    valid_values = ", ".join(sorted({p.value for p in InsightPeriod}))
    raise ValueError(f"Unsupported insight period '{raw}'. Choose one of: {valid_values}.")


def fetch_comments_and_insights(
    manager: FacebookManager,
    post_id: str,
    limit: int,
    period: InsightPeriod,
) -> Dict[str, Any]:
    """Fetch comments and insights for *post_id* using *manager*."""

    comments_resp = manager.get_post_comments(post_id=post_id, limit=limit)
    comments_data = [
        {
            "comment_id": comment.comment_id,
            "from": comment.from_user,
            "message": comment.message,
            "created_time": comment.created_time,
            "like_count": comment.like_count,
            "reply_count": comment.comment_count,
        }
        for comment in comments_resp.comments
    ]

    insights = manager.get_post_insights(post_id=post_id, period=period)
    insights_data = {
        "post_id": insights.post_id,
        "period_requested": period.value,
        "period": insights.period.value,
        "reach": insights.reach,
        "impressions": insights.impressions,
        "reactions": {
            "like": insights.reactions.like,
            "love": insights.reactions.love,
            "wow": insights.reactions.wow,
            "haha": insights.reactions.haha,
            "sad": insights.reactions.sad,
            "angry": insights.reactions.angry,
            "care": insights.reactions.care,
            "computed_total": insights.reactions.computed_total,
        },
        "comments_count": insights.comments_count,
        "shares_count": insights.shares_count,
        "clicked": getattr(insights, "clicked", 0),
        "engagement_rate": insights.engagement_rate,
    }

    return {
        "post_id": post_id,
        "comments": comments_data,
        "comments_total": len(comments_data),
        "insights": insights_data,
        "raw_comments_response_meta": {
            "has_next_page": getattr(comments_resp, "has_next_page", False),
            "next_cursor": getattr(comments_resp, "next_cursor", None),
        },
    }


def print_post_engagement_summary(payload: Dict[str, Any]) -> None:
    """Pretty-print high level information about the fetched engagement payload."""

    insights = payload["insights"]
    print("Summary:")
    print(f"  Comments retrieved: {payload['comments_total']}")
    print(f"  Total reactions: {insights['reactions']['computed_total']}")
    print(f"  Reach: {insights['reach']}")
    print(f"  Impressions: {insights['impressions']}")
    engagement = insights.get("engagement_rate")
    if engagement is not None:
        print(f"  Engagement rate: {engagement:.2f}%")
    print(f"  Insight period (requested/actual): {insights['period_requested']} -> {insights['period']}")

    comments = payload.get("comments", [])
    if comments:
        print("\nFirst comments:")
        for comment in comments[:5]:
            author = comment.get("from")
            if isinstance(author, dict):
                author = author.get("name") or author.get("id") or "Unknown user"
            message_preview = (comment.get("message") or "").strip().replace("\n", " ")
            if len(message_preview) > 120:
                message_preview = f"{message_preview[:117]}..."
            print(f" - {author}: {message_preview} ({comment.get('like_count', 0)} likes)")


def write_output(payload: Dict[str, Any], destination: str) -> None:
    """Write *payload* to *destination* (or stdout when destination is '-')."""

    if destination == "-":
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    output_path = Path(destination)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFull output written to {output_path.resolve()}")


def format_validation_errors(errors: Iterable[Dict[str, Any]]) -> str:
    """Render Pydantic validation errors into a readable multi-line string."""

    lines = []
    for error in errors:
        location = ".".join(str(part) for part in error.get("loc", []) if part is not None)
        message = error.get("msg", "Invalid value")
        lines.append(f"- {location}: {message}" if location else f"- {message}")
    return "\n".join(lines)


def command_fetch_post_engagement(config, args) -> int:
    period = parse_insight_period(args.period)
    with FacebookManager(config=config) as manager:
        payload = fetch_comments_and_insights(manager, args.post_id, args.limit, period)

    print_post_engagement_summary(payload)

    if not args.skip_output:
        write_output(payload, args.output)

    return 0


def command_post_text(config, args) -> int:
    message = args.message
    if not message:
        message = sys.stdin.read().strip() if not sys.stdin.isatty() else input("Enter post message: ").strip()

    if not message:
        raise ValueError("A message is required to create a text post.")

    request = TextPostRequest(message=message)

    with FacebookManager(config=config) as manager:
        response = manager.create_text_post(request)

    print(f"Post created successfully: {response.post_id}")
    return 0


def command_post_image(config, args) -> int:
    if bool(args.image_url) == bool(args.image_path):
        raise ValueError("Provide exactly one of --image-url or --image-path.")

    request = ImagePostRequest(
        message=args.message,
        image_url=args.image_url,
        image_path=args.image_path,
    )

    with FacebookManager(config=config) as manager:
        response = manager.create_image_post(request)

    print(f"Image post created successfully: {response.post_id}")
    return 0


def command_verify(config, args) -> int:
    with FacebookManager(config=config) as manager:
        success = manager.verify_credentials()

    if not args.quiet:
        print("Credentials verified successfully." if success else "Credential verification failed without error response.")

    return 0 if success else 1


def command_page_insights(config, args) -> int:
    period = parse_insight_period(args.period)
    with FacebookManager(config=config) as manager:
        insights = manager.get_page_insights(period=period)

    print(f"Page insights for {insights.page_id} ({period.value} → {insights.period.value}):")

    metrics = [
        ("page_impressions", "Page impressions"),
        ("page_reach", "Page reach"),
        ("page_engaged_users", "Engaged users"),
        ("page_post_engagements", "Post engagements"),
        ("page_fans", "Total fans"),
        ("page_fans_online", "Fans online"),
        ("page_views_total", "Page views"),
        ("page_consumptions", "Content consumptions"),
    ]

    for attr, label in metrics:
        value = getattr(insights, attr, 0)
        print(f"  {label:<22}: {value}")

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    env_path: Optional[Path] = None
    if getattr(args, "env_file", None):
        env_path = Path(args.env_file)
        if not env_path.exists():
            print(f"ERROR: Environment file '{env_path}' does not exist.", file=sys.stderr)
            return 1
        load_dotenv(env_path)
    elif not getattr(args, "no_env_file", False):
        load_dotenv()

    try:
        if env_path is not None:
            config = load_config(env_file=str(env_path))
        elif getattr(args, "no_env_file", False):
            config = load_config(use_env_file=False)
        else:
            config = load_config()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ValidationError as exc:
        print("Configuration is invalid:")
        print(format_validation_errors(exc.errors()))
        return 2

    command_map = {
        "fetch-post-engagement": command_fetch_post_engagement,
        "post-text": command_post_text,
        "post-image": command_post_image,
        "verify": command_verify,
        "page-insights": command_page_insights,
    }

    try:
        handler = command_map[args.command]
        return handler(config, args)
    except InvalidCredentialsError as exc:
        print(f"Invalid credentials: {exc}", file=sys.stderr)
        return 3
    except FacebookAPIError as exc:
        print(f"Facebook API error: {exc}", file=sys.stderr)
        return 4
    except (PostCreationError, ImageUploadError) as exc:
        print(f"Operation failed: {exc}", file=sys.stderr)
        return 5
    except ValidationError as exc:
        print("Invalid input:")
        print(format_validation_errors(exc.errors()))
        return 6
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 130


if __name__ == "__main__":  # pragma: no cover - manual execution path
    sys.exit(main())