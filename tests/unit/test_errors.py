import unittest
from firefly_cli.errors import FireflyError, ConfigError, ApiError, ResolutionError

class TestErrors(unittest.TestCase):
    def test_subclassing(self):
        for cls in (ConfigError, ApiError, ResolutionError):
            self.assertTrue(issubclass(cls, FireflyError))

    def test_api_error_carries_status_and_body(self):
        e = ApiError(422, {"message": "bad"})
        self.assertEqual(e.status, 422)
        self.assertEqual(e.body, {"message": "bad"})
        self.assertIn("422", str(e))

if __name__ == "__main__":
    unittest.main()
