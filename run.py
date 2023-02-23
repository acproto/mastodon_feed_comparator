from __future__ import annotations

import argparse
import dotenv
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mastodon import Mastodon

from digest import fetch_digest
from renderer import render
from scorers import get_scorers
from thresholds import get_threshold_from_name, get_thresholds

if TYPE_CHECKING:
    from scorers import Scorer
    from thresholds import Threshold


def render_digest(context: dict, output_dir: Path, theme: str = "default") -> None:
    output_html = render(context, theme)
    output_file_path = output_dir / "index.html"
    output_file_path.write_text(output_html)


def list_themes() -> list[str]:
    # Return themes, named by directory in `/templates/themes` and which have an `index.html.jinja` present.
    return list(
        filter(
            lambda dir_name: not dir_name.startswith(".")
            and os.path.exists(f"templates/themes/{dir_name}/index.html.jinja"),
            os.listdir("templates/themes"),
        )
    )


def format_base_url(mastodon_base_url: str) -> str:
    return mastodon_base_url.strip().rstrip("/")


def run(
    hours: int,
    scorer: Scorer,
    threshold: Threshold,
    mastodon_token: str,
    mastodon_base_url: str,
    timeline: str,
    output_dir: Path,
    theme: str,
) -> None:

    print(f"Building digest from the past {hours} hours...")

    mst = Mastodon(
        access_token=mastodon_token,
        api_base_url=mastodon_base_url,
    )

    digest_dict = fetch_digest(mst, hours, scorer, threshold, mastodon_base_url, timeline)

    # 4. Build the digest
    if not digest_dict:
        sys.exit(
            f"No posts or boosts were found for the provided digest arguments. Exiting."
        )
    else:
        render_digest(
            context=digest_dict,
            output_dir=output_dir,
            theme=theme,
        )


if __name__ == "__main__":
    scorers = get_scorers()
    thresholds = get_thresholds()

    arg_parser = argparse.ArgumentParser(
        prog="mastodon_digest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    arg_parser.add_argument(
        "-f",  # for "feed" since t-for-timeline is taken
        default="home",
        dest="timeline",
        help="The timeline to summarize: Expects 'home', 'local' or 'federated', or 'list:id', 'hashtag:tag'",
        required=False,
    )
    arg_parser.add_argument(
        "-n",
        choices=range(1, 25),
        default=12,
        dest="hours",
        help="The number of hours to include in the Mastodon Digest",
        type=int,
    )
    arg_parser.add_argument(
        "-s",
        choices=list(scorers.keys()),
        default="SimpleWeighted",
        dest="scorer",
        help="""Which post scoring criteria to use.
            Simple scorers take a geometric mean of boosts and favs.
            Extended scorers include reply counts in the geometric mean.
            Weighted scorers multiply the score by an inverse square root
            of the author's followers, to reduce the influence of large accounts.
        """,
    )
    arg_parser.add_argument(
        "-t",
        choices=list(thresholds.keys()),
        default="normal",
        dest="threshold",
        help="""Which post threshold criteria to use.
            lax = 90th percentile,
            normal = 95th percentile,
            strict = 98th percentile
        """,
    )
    arg_parser.add_argument(
        "-o",
        default="./render/",
        dest="output_dir",
        help="Output directory for the rendered digest",
        required=False,
    )
    arg_parser.add_argument(
        "--theme",
        choices=list_themes(),
        default="default",
        dest="theme",
        help="Named template theme with which to render the digest",
        required=False,
    )
    args = arg_parser.parse_args()

    # Attempt to validate the output directory
    output_dir = Path(args.output_dir)
    if not output_dir.exists() or not output_dir.is_dir():
        sys.exit(f"Output directory not found: {args.output_dir}")

    # Loosely validate the timeline argument, so that if a completely unexpected string is entered,
    # we explicitly reset to 'Home', which makes the rendered output cleaner.
    timeline = args.timeline.strip().lower()
    validTimelineTypes = ["home", "local", "federated", "hashtag", "list"]
    timelineType, *_ = timeline.split(":", 1)
    if not timelineType in validTimelineTypes:
        timeline = "home"

    # load and validate env
    dotenv.load_dotenv(override=False)

    mastodon_token = os.getenv("MASTODON_TOKEN")
    mastodon_base_url = os.getenv("MASTODON_BASE_URL")

    if not mastodon_token:
        sys.exit("Missing environment variable: MASTODON_TOKEN")
    if not mastodon_base_url:
        sys.exit("Missing environment variable: MASTODON_BASE_URL")

    run(
        args.hours,
        scorers[args.scorer](),
        get_threshold_from_name(args.threshold),
        mastodon_token,
        format_base_url(mastodon_base_url),
        timeline,
        output_dir,
        args.theme,
    )
