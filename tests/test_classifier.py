"""Unit tests for the classifier, using Python's built-in unittest (no extra packages)."""
import unittest

from netra.classifier import classify, FLAKY, ENVIRONMENT, TEST_CODE, PRODUCT_BUG, UNKNOWN
from netra.parser import Failure


def make_failure(error_text: str, status: str = "unexpected", attempts: int = 1) -> Failure:
    """Build a Failure with only the fields the classifier looks at."""
    return Failure(
        file="demo.spec.ts", title="demo", project="chromium", status=status,
        attempts=attempts, error_message=error_text.splitlines()[0] if error_text else "",
        error_location="demo.spec.ts:1", error_text=error_text, duration_ms=0,
    )


class ClassifierTest(unittest.TestCase):
    def test_flaky_when_test_passed_on_retry(self):
        verdict = classify(make_failure("Error: anything", status="flaky", attempts=2))
        self.assertEqual(verdict.category, FLAKY)

    def test_environment_when_server_is_unreachable(self):
        verdict = classify(make_failure("Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:4999/"))
        self.assertEqual(verdict.category, ENVIRONMENT)
        self.assertEqual(verdict.evidence, "net::ERR_CONNECTION_REFUSED")

    def test_test_code_error_when_locator_never_appears(self):
        text = ("TimeoutError: locator.click: Timeout 3000ms exceeded.\nCall log:\n"
                "  - waiting for getByTestId('add-to-cart-button')")
        self.assertEqual(classify(make_failure(text)).category, TEST_CODE)

    def test_test_code_error_on_strict_mode_violation(self):
        text = "Error: strict mode violation: getByRole('button') resolved to 3 elements"
        self.assertEqual(classify(make_failure(text)).category, TEST_CODE)

    def test_product_bug_when_element_shows_wrong_value(self):
        text = ("Error: expect(locator).toHaveText(expected) failed\n"
                'Expected: "1"\nReceived: "2"\nCall log:\n  - locator resolved to <span>2</span>')
        verdict = classify(make_failure(text))
        self.assertEqual(verdict.category, PRODUCT_BUG)
        self.assertIn('Received: "2"', verdict.evidence)

    def test_needs_investigation_when_no_rule_matches(self):
        self.assertEqual(classify(make_failure("Error: something unusual happened")).category, UNKNOWN)


if __name__ == "__main__":
    unittest.main()
