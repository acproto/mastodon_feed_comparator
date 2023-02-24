from __future__ import annotations

import importlib
import inspect
from abc import ABC, abstractmethod
from datetime import datetime
from math import sqrt
from typing import TYPE_CHECKING

from scipy import stats

if TYPE_CHECKING:
    from models import ScoredPost


class Weight(ABC):
    @classmethod
    @abstractmethod
    def weight(cls, scored_post: ScoredPost):
        pass


class UniformWeight(Weight):
    @classmethod
    def weight(cls, scored_post: ScoredPost) -> UniformWeight:
        return 1


class InverseFollowerWeight(Weight):
    @classmethod
    def weight(cls, scored_post: ScoredPost) -> InverseFollowerWeight:
        # Zero out posts by accounts with zero followers (it happens), or less (count is -1 when the followers count is hidden)
        if scored_post.info["account"]["followers_count"] <= 0:
            weight = 0
        else:
            # inversely weight against how big the account is
            weight = 1 / sqrt(scored_post.info["account"]["followers_count"])

        return weight


class Scorer(ABC):
    @abstractmethod
    def score(self, scored_post: ScoredPost) -> (int, dict):
        """
        Returns a tuple of the score and a debug dictionary of the score components.
        :param scored_post:
        :return: A tuple of the score and a debug dictionary of the score components
        """
        pass

    @classmethod
    def get_name(cls):
        return cls.__name__.replace("Scorer", "")

    def get_values(self):
        return {}


class SimpleScorer(UniformWeight, Scorer):
    
    def score(self, scored_post: ScoredPost) -> (int, dict):
        if scored_post.reblogs or scored_post.favourites:
            # If there's at least one metric
            # We don't want zeros in other metrics to multiply that out
            # Inflate every value by 1
            metric_average = stats.gmean(
                [
                    scored_post.reblogs + 1,
                    scored_post.favourites + 1,
                ]
            )
        else:
            metric_average = 0
        weight = super().weight(scored_post)
        return metric_average * weight, dict(
            reblogs=scored_post.reblogs,
            favourites=scored_post.favourites,
            engagement_score=metric_average,
            weight=weight,
            equation='(Geometric mean of reblogs, favourites) * weight'
        )


class SimpleWeightedScorer(InverseFollowerWeight, SimpleScorer):

    def score(self, scored_post: ScoredPost) -> (int, dict):
        engagement_score, engagement_score_debug = super().score(scored_post)
        weight = super().weight(scored_post)
        engagement_score_debug.update(dict(weight=weight))
        return engagement_score * weight, engagement_score_debug


class ExtendedSimpleScorer(UniformWeight, Scorer):

    def score(self, scored_post: ScoredPost) -> (int, dict):
        if (
            scored_post.reblogs
            or scored_post.favourites
            or scored_post.replies
        ):
            # If there's at least one metric
            # We don't want zeros in other metrics to multiply that out
            # Inflate every value by 1
            metric_average = stats.gmean(
                [
                    scored_post.reblogs + 1,
                    scored_post.favourites + 1,
                    scored_post.replies + 1,
                ],
            )
        else:
            metric_average = 0
        weight = super().weight(scored_post)
        return metric_average * weight, dict(
            reblogs=scored_post.reblogs,
            favourites=scored_post.favourites,
            replies=scored_post.replies,
            engagement_score=metric_average,
            weight=weight,
            equation='(Geometric mean of reblogs, favourites, replies) * weight'
        )


class ExtendedSimpleWeightedScorer(InverseFollowerWeight, ExtendedSimpleScorer):

    def score(self, scored_post: ScoredPost) -> (int, dict):
        engagement_score, engagement_score_debug = super().score(scored_post)
        weight = super().weight(scored_post)
        engagement_score_debug.update(dict(weight=weight))
        return engagement_score * weight, engagement_score_debug
    

class AllFactorsWeightedScorer(Scorer):

    def __init__(self, favourites_weight=0, reblogs_weight=0, replies_weight=0, inverse_follower_boost=False):
        """Initialize the all factors weighted score with the provided weights.

        :param favourites_weight: [0.0-2.0] Importance of favorites in the score.
        :param reblogs_weight: [0.0-2.0] Importance of reblogs in the score.
        :param replies_weight: [0.0-2.0] Importance of replies in the score.
        :param inverse_follower_boost: Whether to boost posts from people with fewer followers.
        """
        self._favourites_weight = favourites_weight
        self._reblogs_weight = reblogs_weight
        self._replies_weight = replies_weight
        self._inverse_follower_boost = inverse_follower_boost

    def score(self, scored_post: ScoredPost):
        """Returns the score according to the AllFactorsWeighted algorithm.

        The score is calculated as the geometric mean of
        (the weight of each engagement factor * the count of each engagement factor)
        and multiplied by the inverse follower weight if inverse_follower_boost is True.

        If all engagement factors are all 0, returns the date of the post (for a timeline feed).

        :param scored_post: the post to score
        :return: The score and a debug dict with the score parts.
        """
        # Score is:
        # 1) The geometric mean of: weight of each post factor * count of each post factor
        # 2) Multiply by the inverse follower weight if provided
        if not scored_post.reblogs and not scored_post.favourites and not scored_post.replies:
            return 0, dict(message='No reblogs, favourites, or replies.')

        # If no engagement score parts.
        if not self._reblogs_weight and not self._favourites_weight and not self._replies_weight:
            return (datetime.timestamp(scored_post.info['created_at']),
                    dict(message='No engagement component, score is post timestamp.'))
        # Add one to each engagement metric so we can keep any that should be weighted
        # in the geometric mean.
        favourites_factor = (scored_post.favourites + 1) * self._favourites_weight
        reblogs_factor = (scored_post.reblogs + 1) * self._reblogs_weight
        replies_factor = (scored_post.replies + 1) * self._replies_weight
        engagement_score = stats.gmean(
            list(filter(
                lambda x: x > 0,
                [favourites_factor, reblogs_factor, replies_factor])),
        )
        inverse_follower_weight = 1 if not self._inverse_follower_boost else InverseFollowerWeight.weight(scored_post)
        debug_dict = dict(
            reblogs=scored_post.reblogs,
            replies=scored_post.replies,
            favourites=scored_post.favourites,
            favourites_factor=favourites_factor,
            reblogs_factor=reblogs_factor,
            replies_factor=replies_factor,
            engagement_score=engagement_score,
            inverse_follower_weight=inverse_follower_weight,
            equation='(Geometric mean of favourites_factor, reblogs_factor, replies_factor) * inverse_follower_weight'
        )
        debug_dict.update(self.get_values())
        return engagement_score * inverse_follower_weight, debug_dict

    def get_values(self):
        return dict(
            favourites_weight=self._favourites_weight,
            reblogs_weight=self._reblogs_weight,
            replies_weight=self._replies_weight,
            inverse_follower_boost=self._inverse_follower_boost
        )
    

def get_scorers():
    all_classes = inspect.getmembers(importlib.import_module(__name__), inspect.isclass)
    scorers = [c for c in all_classes if c[1] != Scorer and issubclass(c[1], Scorer)]
    return {scorer[1].get_name(): scorer[1] for scorer in scorers}
