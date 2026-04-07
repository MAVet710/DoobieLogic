import unittest

from doobielogic.verification import is_trusted_source, verify_sources


class TestVerification(unittest.TestCase):
    def test_is_trusted_source(self):
        self.assertTrue(is_trusted_source("https://cannabis.ca.gov/"))
        self.assertTrue(is_trusted_source("https://www.mass.gov/info-details/cannabis"))
        self.assertFalse(is_trusted_source("https://random-blog.example.com/cannabis"))

    def test_verify_sources(self):
        ok, trusted, untrusted = verify_sources(
            [
                "https://cannabis.ca.gov/",
                "https://example.org/post",
            ]
        )
        self.assertTrue(ok)
        self.assertEqual(len(trusted), 1)
        self.assertEqual(len(untrusted), 1)


if __name__ == "__main__":
    unittest.main()
