# competitor-analyzation

Instagram competitor scraping with [Instaloader](https://instaloader.github.io/).

## Install

```bash
pip install -r requirements.txt
```

## Usage

Scrape the last 50 posts for each username and write them to a CSV:

```bash
python instagram_scraper.py --users nike adidas puma --output posts.csv
```

Or read usernames from a file (one per line):

```bash
python instagram_scraper.py --users-file competitors.txt --output posts.csv
```

### Useful flags

- `--limit N` — posts per user (default 50)
- `--delay SECONDS` — pause between profiles (default 5)
- `--login-user USER` — authenticate using an existing Instaloader session
- `--session-file PATH` — explicit session file path

### Authenticating

Public profiles work without login but Instagram aggressively rate-limits
anonymous scraping. To use a session, log in once with the Instaloader CLI:

```bash
instaloader --login YOUR_USERNAME
```

Then pass `--login-user YOUR_USERNAME` to the script.

## CSV columns

`username, shortcode, url, date_utc, post_type, like_count, comment_count,
view_count, engagement_rate, follower_count, caption`

- `post_type` is one of `image`, `carousel`, `video`, `reel`.
- `view_count` is empty for non-video posts.
- `engagement_rate` is `(likes + comments) / followers`, rounded to 6 decimals.
