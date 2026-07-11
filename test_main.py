import unittest
from unittest.mock import patch

import main


class MainTests(unittest.TestCase):
    def test_get_build_and_proton_dir_returns_custom_names(self) -> None:
        with patch("builtins.input", side_effect=["custom-build", "custom-dir"]):
            build_name, proton_dir = main.get_build_and_proton_dir("my_build", "proton-bleeding-edge")

        self.assertEqual(build_name, "custom-build")
        self.assertEqual(proton_dir, "custom-dir")

    def test_get_build_and_proton_dir_falls_back_to_defaults(self) -> None:
        total_name_prompts = main.MAX_NAME_ATTEMPTS * 2
        retry_inputs = [""] * total_name_prompts

        with patch("builtins.input", side_effect=retry_inputs):
            build_name, proton_dir = main.get_build_and_proton_dir("my_build", "proton-bleeding-edge")

        self.assertEqual(build_name, "my_build")
        self.assertEqual(proton_dir, "proton-bleeding-edge")


if __name__ == "__main__":
    unittest.main()
