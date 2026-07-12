import unittest
from unittest.mock import patch

import main


class MainTests(unittest.TestCase):
    def test_is_valid_name_rejects_dot_only_names(self) -> None:
        self.assertTrue(main.is_valid_name("custom-dir"))
        self.assertFalse(main.is_valid_name("."))
        self.assertFalse(main.is_valid_name(".."))

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
            """Pretend only the final compatibilitytools.d target already exists."""
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

    def test_update_existing_proton_repo_uses_upstream_and_ff_only_pull(self) -> None:
        with (
            patch("main.os.chdir"),
            patch("main.subprocess.run") as mock_run,
            patch("main.subprocess.check_output", side_effect=[b"local", b"remote"]) as mock_check_output,
        ):
            main.update_existing_proton_repo()

        self.assertEqual(
            mock_check_output.call_args_list,
            [
                unittest.mock.call(["git", "rev-parse", "@"]),
                unittest.mock.call(["git", "rev-parse", "@{u}"]),
            ],
        )
        self.assertIn(
            unittest.mock.call(["git", "pull", "--ff-only", "--recurse-submodules"], check=True),
            mock_run.call_args_list,
        )

    def test_move_proton_dir_stages_redist_before_replacing_existing_install(self) -> None:
        home_dir = "/home/tester"
        proton_dir = "custom-dir"
        target_dir = f"{home_dir}/.steam/root/compatibilitytools.d/{proton_dir}"

        with patch("main.os.path.exists", return_value=False), patch("main.subprocess.run") as mock_run:
            main.move_proton_dir(home_dir, proton_dir, proton_dir_exists=True)

        self.assertEqual(
            [call.args[0] for call in mock_run.call_args_list],
            [
                ["cp", "-r", "redist", f"{target_dir}.tmp"],
                ["rm", "-rf", target_dir],
                ["mv", f"{target_dir}.tmp", target_dir],
            ],
        )


if __name__ == "__main__":
    unittest.main()
