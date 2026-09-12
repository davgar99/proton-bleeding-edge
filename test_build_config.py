import os
import unittest
from unittest.mock import patch

from build_config import resolve_build_jobs


class ResolveBuildJobsTests(unittest.TestCase):
    def test_defaults_to_detected_cpu_count(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch("build_config.os.cpu_count", return_value=8):
            self.assertEqual(resolve_build_jobs(), 8)

    def test_defaults_to_one_when_cpu_count_is_unknown(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch("build_config.os.cpu_count", return_value=None):
            self.assertEqual(resolve_build_jobs(), 1)

    def test_environment_override_is_honored(self) -> None:
        with patch.dict(os.environ, {"PROTON_BUILD_JOBS": "3"}, clear=True):
            self.assertEqual(resolve_build_jobs(), 3)

    def test_auto_override_uses_detected_cpu_count(self) -> None:
        with patch("build_config.os.cpu_count", return_value=12):
            self.assertEqual(resolve_build_jobs(" auto "), 12)

    def test_blank_override_uses_default(self) -> None:
        with patch.dict(os.environ, {"PROTON_BUILD_JOBS": "  "}, clear=True), patch("build_config.os.cpu_count", return_value=6):
            self.assertEqual(resolve_build_jobs(), 6)

    def test_invalid_override_is_rejected(self) -> None:
        for value in ("0", "-2", "many"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "positive integer"):
                resolve_build_jobs(value)


if __name__ == "__main__":
    unittest.main()
