import unittest
from unittest.mock import patch

from reviewtally.data_collection import ReviewDataContext, collect_review_data


def _make_pr(number: int) -> dict:
    return {"number": number, "created_at": "2019-11-17T10:00:00Z"}


def _make_review(login: str, *, rubber_stamp: bool, comments: int = 0) -> dict:
    return {
        "user": {"login": login},
        "comment_count": comments,
        "pull_number": 1,
        "submitted_at": "2019-11-17T17:43:43Z",
        "is_rubber_stamp": rubber_stamp,
    }


def _reviews() -> list[dict]:
    return [
        _make_review("alice", rubber_stamp=False, comments=3),
        _make_review("bob", rubber_stamp=True),
        _make_review("bob", rubber_stamp=False, comments=1),
    ]


class TestRubberStampCollection(unittest.TestCase):
    BOB_TOTAL_REVIEWS = 2
    BOB_RUBBER_STAMPS = 1
    BOB_REVIEWS_EXCLUDED = 1
    BOB_COMMENTS_EXCLUDED = 1

    def _run(self, *, exclude: bool) -> dict:
        reviewer_stats: dict = {}
        context = ReviewDataContext(
            org_name="octocat",
            repo="Hello-World",
            pull_requests=[_make_pr(1)],
            reviewer_stats=reviewer_stats,
            exclude_rubber_stamps=exclude,
        )
        with patch(
            "reviewtally.data_collection."
            "get_reviewers_with_comments_for_pull_requests",
            return_value=_reviews(),
        ):
            collect_review_data(context)
        return reviewer_stats

    def test_rubber_stamps_counted_by_default(self) -> None:
        stats = self._run(exclude=False)
        assert stats["bob"]["rubber_stamps"] == self.BOB_RUBBER_STAMPS
        # All reviews still counted toward the tally
        assert stats["bob"]["reviews"] == self.BOB_TOTAL_REVIEWS
        assert stats["alice"]["rubber_stamps"] == 0
        assert stats["alice"]["reviews"] == 1

    def test_rubber_stamps_excluded_from_tally(self) -> None:
        stats = self._run(exclude=True)
        # Still tracked for context
        assert stats["bob"]["rubber_stamps"] == self.BOB_RUBBER_STAMPS
        # But dropped from the review/comment counts
        assert stats["bob"]["reviews"] == self.BOB_REVIEWS_EXCLUDED
        assert stats["bob"]["comments"] == self.BOB_COMMENTS_EXCLUDED
        assert stats["alice"]["reviews"] == 1


if __name__ == "__main__":
    unittest.main()
