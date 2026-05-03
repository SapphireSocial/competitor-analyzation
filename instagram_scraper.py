"""Scrape recent Instagram posts for a list of usernames and export to CSV."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass, asdict
from itertools import islice
from pathlib import Path

import instaloader
from instaloader.exceptions import (
    ConnectionException,
    LoginRequiredException,
    ProfileNotExistsException,
    QueryReturnedNotFoundException,
    TooManyRequestsException,
)


POSTS_PER_USER = 50

CSV_FIELDS = [
    "username",
    "shortcode",
    "url",
    "date_utc",
    "post_type",
    "like_count",
    "comment_count",
    "view_count",
    "engagement_rate",
    "follower_count",
    "caption",
]


@dataclass
class PostRow:
    username: str
    shortcode: str
    url: str
    date_utc: str
    post_type: str
    like_count: int
    comment_count: int
    view_count: int | str
    engagement_rate: float
    follower_count: int
    caption: str


def classify_post(post: instaloader.Post) -> str:
    if post.typename == "GraphSidecar":
        return "carousel"
    if post.is_video:
        return "reel" if getattr(post, "product_type", "") == "clips" else "video"
    return "image"


def safe_view_count(post: instaloader.Post) -> int | str:
    if not post.is_video:
        return ""
    return post.video_view_count or 0


def scrape_profile(
    loader: instaloader.Instaloader,
    username: str,
    limit: int,
) -> list[PostRow]:
    profile = instaloader.Profile.from_username(loader.context, username)
    followers = profile.followers or 0
    rows: list[PostRow] = []

    for post in islice(profile.get_posts(), limit):
        likes = post.likes or 0
        comments = post.comments or 0
        engagement = ((likes + comments) / followers) if followers else 0.0
        rows.append(
            PostRow(
                username=username,
                shortcode=post.shortcode,
                url=f"https://www.instagram.com/p/{post.shortcode}/",
                date_utc=post.date_utc.isoformat(),
                post_type=classify_post(post),
                like_count=likes,
                comment_count=comments,
                view_count=safe_view_count(post),
                engagement_rate=round(engagement, 6),
                follower_count=followers,
                caption=(post.caption or "").replace("\n", " ").strip(),
            )
        )
        time.sleep(1)

    return rows


def write_csv(rows: list[PostRow], output: Path) -> None:
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--users", nargs="+", help="Instagram usernames")
    src.add_argument(
        "--users-file",
        type=Path,
        help="Path to a text file with one username per line",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("instagram_posts.csv"),
        help="CSV output path (default: instagram_posts.csv)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=POSTS_PER_USER,
        help=f"Posts per user (default: {POSTS_PER_USER})",
    )
    parser.add_argument(
        "--login-user",
        help="Optional Instagram username to authenticate as (uses session file if available)",
    )
    parser.add_argument(
        "--session-file",
        type=Path,
        help="Optional path to an Instaloader session file",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=5.0,
        help="Seconds to wait between profiles (default: 5)",
    )
    return parser.parse_args()


def load_usernames(args: argparse.Namespace) -> list[str]:
    if args.users:
        return [u.strip().lstrip("@") for u in args.users if u.strip()]
    text = args.users_file.read_text(encoding="utf-8")
    return [line.strip().lstrip("@") for line in text.splitlines() if line.strip()]


def main() -> int:
    args = parse_args()
    usernames = load_usernames(args)
    if not usernames:
        print("No usernames provided.", file=sys.stderr)
        return 2

    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    if args.login_user:
        if args.session_file:
            loader.load_session_from_file(args.login_user, str(args.session_file))
        else:
            loader.load_session_from_file(args.login_user)

    all_rows: list[PostRow] = []
    for i, username in enumerate(usernames):
        print(f"[{i + 1}/{len(usernames)}] Scraping @{username}...", file=sys.stderr)
        try:
            rows = scrape_profile(loader, username, args.limit)
            print(f"  -> {len(rows)} posts", file=sys.stderr)
            all_rows.extend(rows)
        except ProfileNotExistsException:
            print(f"  ! Profile @{username} does not exist.", file=sys.stderr)
        except LoginRequiredException:
            print(
                f"  ! @{username} requires login (likely private). Skipping.",
                file=sys.stderr,
            )
        except TooManyRequestsException:
            print(
                "  ! Rate limited by Instagram. Sleeping 60s before continuing.",
                file=sys.stderr,
            )
            time.sleep(60)
        except (ConnectionException, QueryReturnedNotFoundException) as exc:
            print(f"  ! Error scraping @{username}: {exc}", file=sys.stderr)

        if i < len(usernames) - 1:
            time.sleep(args.delay)

    write_csv(all_rows, args.output)
    print(
        f"Wrote {len(all_rows)} rows from {len(usernames)} profile(s) to {args.output}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
