from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from api import fetch_posts_and_boosts
from thresholds import Threshold
from scorers import SimpleWeightedScorer


if TYPE_CHECKING:
    from scorers import Scorer
    from mastodon import Mastodon


def fetch_digest(
        mst: Mastodon,
        mastodon_base_url: str = None,
        hours: int = 12,
        scorer: Scorer = None,
        threshold: Threshold = Threshold.NORMAL,
        timeline: str = 'home',
        limit: int = None):
    if not scorer:
        scorer = SimpleWeightedScorer()
    # 1. Fetch all the posts and boosts from our home timeline that we haven't interacted with
    posts, boosts = fetch_posts_and_boosts(hours, mst, timeline, scorer)

    # 2. Score them, and return those that meet our threshold
    threshold_posts = threshold.posts_meeting_criteria(posts)
    threshold_boosts = threshold.posts_meeting_criteria(boosts)

    # 3. Sort posts and boosts by score, descending
    threshold_posts = sorted(
        threshold_posts, key=lambda post: post.score, reverse=True
    )
    threshold_boosts = sorted(
        threshold_boosts, key=lambda post: post.score, reverse=True
    )

    # 4. Build the digest
    if len(threshold_posts) == 0 and len(threshold_boosts) == 0:
        return None
    else:
        return {
                "hours": hours,
                "posts": threshold_posts[:limit] if limit else threshold_posts,
                "boosts": threshold_boosts[:limit] if limit else threshold_boosts,
                "mastodon_base_url": mastodon_base_url,
                "rendered_at": datetime.utcnow().strftime("%B %d, %Y at %H:%M:%S UTC"),
                "timeline_name": timeline,
                "threshold": threshold.get_name(),
                "scorer": scorer.get_name(),
                "scorer_values": scorer.get_values(),
            }
