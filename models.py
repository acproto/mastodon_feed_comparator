from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scorers import Scorer


class ScoredPost:
    def __init__(self, info: dict, scorer: Scorer):
        self.info = info
        self.scorer = scorer
        self._score = None
        self._debug_score = None

    @property
    def url(self) -> str:
        return self.info["url"]

    @property
    def favourites(self) -> int:
        return self.info["favourites_count"]

    @property
    def reblogs(self) -> int:
        return self.info["reblogs_count"]

    @property
    def replies(self) -> int:
        return self.info["replies_count"]

    @property
    def debug_score(self) -> dict:
        self._cache_score()
        return self._debug_score

    @property
    def debug_score_string(self) -> str:
        return "\n".join([f"{key}: {self.debug_score[key]}" for key in self.debug_score])

    def get_home_url(self, mastodon_base_url: str) -> str:
        return f"{mastodon_base_url}/@{self.info['account']['acct']}/{self.info['id']}"

    @property
    def score(self) -> float:
        self._cache_score()
        return self._score

    def _cache_score(self):
        if not self._score or not self._debug_score:
            self._score, self._debug_score = self.scorer.score(self)
