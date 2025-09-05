import json
import unittest

# The function under test is expected to live in the top-level `find_neighbors.py`.
# It should expose a callable with the following signature:
#     find_neighbors_in_text(text: str, term1: str, term2: str, nearness: int) -> dict
# and return a JSON-serializable structure with keys like:
#     {
#         "count": int,
#         "matches": [
#             {
#                 "snippet": str,
#                 # optional extra metadata as needed
#             },
#             ...
#         ]
#     }
# This test purposefully defines the expected contract but does not modify your source file.

try:
    from find_neighbors import find_neighbors_in_text  # type: ignore
except Exception as exc:  # pragma: no cover - allows test discovery even before impl exists
    find_neighbors_in_text = None  # type: ignore


class FindNeighborsContractTests(unittest.TestCase):
    def setUp(self) -> None:
        # A simple sample text that includes the target terms in different contexts
        self.sample_text = (
            "Alpha beta gamma. Cats and dogs are friendly. "
            "The quick brown fox jumps over the lazy dog. "
            "Cats quickly approach dogs near the yard."
        )

    def test_function_is_exposed(self):
        # Ensure the symbol exists; if not, the test should clearly explain what's missing
        self.assertIsNotNone(
            find_neighbors_in_text,
            msg=(
                "Expected `find_neighbors_in_text` to be importable from `find_neighbors.py`.\n"
                "Please implement: find_neighbors_in_text(text: str, term1: str, term2: str, nearness: int) -> dict"
            ),
        )

    def test_returns_json_serializable_with_expected_shape(self):
        if find_neighbors_in_text is None:
            self.skipTest("`find_neighbors_in_text` not implemented yet")

        term1 = "cats"
        term2 = "dogs"
        nearness = 3

        result = find_neighbors_in_text(self.sample_text, term1, term2, nearness)

        # JSON serializable
        try:
            json.dumps(result)
        except TypeError as te:  # pragma: no cover
            self.fail(f"Result is not JSON serializable: {te}")

        # Expected top-level shape
        self.assertIsInstance(result, dict)
        self.assertIn("count", result)
        self.assertIn("matches", result)
        self.assertIsInstance(result["count"], int)
        self.assertIsInstance(result["matches"], list)
        self.assertEqual(result["count"], len(result["matches"]))

        # At least one match in this sample when nearness=3 (e.g., "Cats and dogs")
        self.assertGreaterEqual(result["count"], 1)

        # Each match should include a snippet string that contains both terms (any order), case-insensitive
        for m in result["matches"]:
            self.assertIsInstance(m, dict)
            self.assertIn("snippet", m)
            self.assertIsInstance(m["snippet"], str)
            snippet_lower = m["snippet"].lower()
            self.assertIn("cats", snippet_lower)
            self.assertIn("dogs", snippet_lower)

    def test_zero_results_when_terms_too_far_apart(self):
        if find_neighbors_in_text is None:
            self.skipTest("`find_neighbors_in_text` not implemented yet")

        term1 = "alpha"
        term2 = "dogs"
        # With nearness very small, likely no adjacency across sentence boundary
        nearness = 0

        result = find_neighbors_in_text(self.sample_text, term1, term2, nearness)
        self.assertIsInstance(result, dict)
        self.assertIn("count", result)
        self.assertIn("matches", result)
        self.assertEqual(result["count"], len(result["matches"]))
        # We expect zero or very few; in this sample, 0 is the strict expectation
        self.assertEqual(result["count"], 0)


if __name__ == "__main__":
    unittest.main()
