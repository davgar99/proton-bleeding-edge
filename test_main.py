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

        with patch("builtins.input", side_effect=retry_inputs), patch("main.sleep"):
            build_name, proton_dir = main.get_build_and_proton_dir("my_build", "proton-bleeding-edge")

        self.assertEqual(build_name, "my_build")
        self.assertEqual(proton_dir, "proton-bleeding-edge")

    def test_get_build_and_proton_dir_can_mix_custom_and_default_names(self) -> None:
        retry_inputs = ["custom-build"] + ([""] * main.MAX_NAME_ATTEMPTS)

        with patch("builtins.input", side_effect=retry_inputs), patch("main.sleep"):
            build_name, proton_dir = main.get_build_and_proton_dir("my_build", "proton-bleeding-edge")

        self.assertEqual(build_name, "custom-build")
        self.assertEqual(proton_dir, "proton-bleeding-edge")

    def test_main_passes_selected_build_name_to_configure(self) -> None:
        def fake_exists(path: str) -> bool:
            return path != "Proton" and path.endswith("/custom-dir")

        with (
            patch("main.os.path.exists", side_effect=fake_exists),
            patch("main.os.chdir"),
            patch("main.os.makedirs"),
            patch("main.os.cpu_count", return_value=4),
            patch("main.sleep"),
            patch("main.user_query", side_effect=[("custom-build", "custom-dir"), None]),
            patch("main.subprocess.run") as mock_run,
        ):
            main.main()

        self.assertIn(
            ["../configure.sh", "--enable-ccache", "--build-name=custom-build"],
            [call.args[0] for call in mock_run.call_args_list],
        )


if __name__ == "__main__":
    unittest.main()
