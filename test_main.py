import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import main


class MainTests(unittest.TestCase):
    def test_is_valid_name(self):
        self.assertTrue(main.is_valid_name("custom-build_1.0"))
        self.assertFalse(main.is_valid_name("custom build"))

    @patch("main.sleep")
    @patch("builtins.input", side_effect=["", "bad name", "valid-name"])
    def test_get_name_retries_until_valid(self, mock_input, mock_sleep):
        result = main.get_name("Name: ", "fallback-name")

        self.assertEqual(result, "valid-name")
        mock_sleep.assert_not_called()

    @patch("main.sleep")
    @patch("builtins.input", side_effect=["", "bad name", ""])
    def test_get_name_uses_default_after_invalid_attempts(
        self,
        mock_input,
        mock_sleep,
    ):
        result = main.get_name("Name: ", "fallback-name")

        self.assertEqual(result, "fallback-name")
        mock_sleep.assert_called_once_with(1)

    @patch("main.os.cpu_count", return_value=4)
    @patch("main.subprocess.run")
    def test_build_proton_uses_custom_build_name(self, mock_run, mock_cpu_count):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "Proton"
            source_dir.mkdir()

            dist_dir = main.build_proton(source_dir, "custom-build")

        build_dir = source_dir / main.PROTON_BUILD_DIRECTORY
        self.assertEqual(dist_dir, build_dir / main.PROTON_DIST_DIRECTORY)
        mock_run.assert_any_call(
            ["../configure.sh", "--enable-ccache", "--build-name=custom-build"],
            cwd=build_dir,
            check=True,
        )
        mock_run.assert_any_call(
            ["make", "-j4", "redist"],
            cwd=build_dir,
            check=True,
        )

    @patch("main.sleep")
    @patch("main.subprocess.run")
    @patch("main.get_git_revision", side_effect=["local", "remote"])
    def test_prepare_proton_source_updates_existing_repo(
        self,
        mock_revision,
        mock_run,
        mock_sleep,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_dir = Path(temp_dir)
            (workspace_dir / main.PROTON_SOURCE_DIRECTORY).mkdir()

            source_dir = main.prepare_proton_source(workspace_dir)

        expected_dir = Path(temp_dir) / main.PROTON_SOURCE_DIRECTORY
        self.assertEqual(source_dir, expected_dir)
        mock_run.assert_any_call(
            ["git", "fetch", "--recurse-submodules"],
            cwd=expected_dir,
            check=True,
        )
        mock_run.assert_any_call(
            ["git", "pull", "--recurse-submodules"],
            cwd=expected_dir,
            check=True,
        )
        mock_sleep.assert_called_once_with(main.BUILD_READY_DELAY_SECONDS)

    def test_install_proton_replaces_existing_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dist_dir = temp_path / "dist"
            install_dir = temp_path / "compatibilitytools.d" / "custom-build"
            dist_dir.mkdir()
            (dist_dir / "version").write_text("new build", encoding="utf-8")
            install_dir.mkdir(parents=True)
            (install_dir / "version").write_text("old build", encoding="utf-8")

            main.install_proton(dist_dir, install_dir)

            self.assertTrue((install_dir / "version").exists())
            self.assertEqual(
                (install_dir / "version").read_text(encoding="utf-8"),
                "new build",
            )


if __name__ == "__main__":
    unittest.main()
