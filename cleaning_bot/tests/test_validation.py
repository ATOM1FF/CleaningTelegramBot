import unittest

from utils.validation import normalize_phone, parse_size


class ValidationTests(unittest.TestCase):
    def test_phone_normalization(self):
        self.assertEqual(normalize_phone("+998 90 123 45 67"), "+998901234567")
        self.assertEqual(normalize_phone("901234567"), None)

    def test_size_parsing(self):
        self.assertEqual(parse_size("2x3"), (2.0, 3.0))
        self.assertEqual(parse_size("2,5 × 3"), (2.5, 3.0))
        self.assertIsNone(parse_size("ikki x uch"))


if __name__ == "__main__":
    unittest.main()
