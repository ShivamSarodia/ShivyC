"""Class containing useful util functions."""

import unittest
from errors import error_collector


class TestUtils(unittest.TestCase):
    """Util functions useful for all tests."""

    def assertIssues(self, issues):
        """Assert that all given issues have been raised in expected order.

        Clears the error_collector after running, so tearDown() can verify
        there are no errors remaining in the collector.

        issues (List[str]) - list of issue descriptions, like
                             "error: expression invalid"

        """
        self.assertEqual(len(error_collector.issues), len(issues))
        for descrip, issue in zip(issues, error_collector.issues):
            self.assertIn(descrip, str(issue))
        error_collector.clear()

    def assertNoIssues(self):
        """Assert that there are no issues in error collector."""
        for issue in error_collector.issues:
            raise issue
