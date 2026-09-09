import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import main


class PrepareProtonRepositoryTests(unittest.TestCase):
    def test_rejects_symlink_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work_dir = root / "work"
            work_dir.mkdir()
            real_checkout = root / "real-proton"
            real_checkout.mkdir()
            (work_dir / "Proton").symlink_to(real_checkout, target_is_directory=True)

            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                with self.assertRaisesRegex(RuntimeError, "file or symlink"):
                    main.prepare_proton_repository("https://example.invalid/Proton.git", "bleeding-edge")
            finally:
                os.chdir(old_cwd)

    def test_rejects_dirty_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            (work_dir / "Proton").mkdir()

            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                with patch("main.subprocess.check_output", side_effect=["true\n", " M local.txt\n"]):
                    with self.assertRaisesRegex(RuntimeError, "uncommitted changes"):
                        main.prepare_proton_repository("https://example.invalid/Proton.git", "bleeding-edge")
            finally:
                os.chdir(old_cwd)

    def test_rejects_wrong_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            (work_dir / "Proton").mkdir()

            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                with patch("main.subprocess.check_output", side_effect=["true\n", "", "stable\n"]):
                    with self.assertRaisesRegex(RuntimeError, "expected 'bleeding-edge'"):
                        main.prepare_proton_repository("https://example.invalid/Proton.git", "bleeding-edge")
            finally:
                os.chdir(old_cwd)

    def test_fast_forward_update_synchronizes_submodules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            (work_dir / "Proton").mkdir()
            successful = MagicMock(returncode=0)

            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                with (
                    patch(
                        "main.subprocess.check_output",
                        side_effect=[
                            "true\n",
                            "",
                            "bleeding-edge\n",
                            "https://example.invalid/Proton.git\n",
                            "local-sha\n",
                            "remote-sha\n",
                        ],
                    ),
                    patch("main.subprocess.run", return_value=successful) as run,
                ):
                    main.prepare_proton_repository("https://example.invalid/Proton.git", "bleeding-edge")
            finally:
                os.chdir(old_cwd)

            run.assert_any_call(
                ["git", "-C", "Proton", "merge", "--ff-only", "FETCH_HEAD"],
                check=True,
            )
            run.assert_any_call(
                ["git", "-C", "Proton", "submodule", "update", "--init", "--recursive"],
                check=True,
            )


class MoveProtonDirTests(unittest.TestCase):
    def test_rejects_symlink_destination_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home = root / "home"
            compatibility_tools = home / ".steam" / "root" / "compatibilitytools.d"
            compatibility_tools.mkdir(parents=True)

            real_target = compatibility_tools / "existing-tool"
            real_target.mkdir()
            marker = real_target / "keep.txt"
            marker.write_text("keep", encoding="utf-8")

            symlink = compatibility_tools / "custom-proton"
            symlink.symlink_to(real_target, target_is_directory=True)

            work_dir = root / "work"
            work_dir.mkdir()
            (work_dir / "dist").mkdir()

            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                with self.assertRaisesRegex(ValueError, "symlink"):
                    main.move_proton_dir(str(home), "custom-proton")
            finally:
                os.chdir(old_cwd)

            self.assertTrue(marker.exists())
            self.assertTrue(symlink.is_symlink())

    def test_rejects_broken_symlink_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home = root / "home"
            compatibility_tools = home / ".steam" / "root" / "compatibilitytools.d"
            compatibility_tools.mkdir(parents=True)
            symlink = compatibility_tools / "custom-proton"
            symlink.symlink_to(compatibility_tools / "missing-target", target_is_directory=True)

            work_dir = root / "work"
            work_dir.mkdir()
            (work_dir / "dist").mkdir()

            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                with self.assertRaisesRegex(ValueError, "symlink"):
                    main.move_proton_dir(str(home), "custom-proton")
            finally:
                os.chdir(old_cwd)

            self.assertTrue(os.path.lexists(symlink))
            self.assertTrue(symlink.is_symlink())

    def test_rejects_invalid_directory_names_when_called_directly(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            for invalid_name in ("../outside", "/tmp/outside", "nested/tool"):
                with self.subTest(invalid_name=invalid_name):
                    with self.assertRaisesRegex(ValueError, "Invalid Proton directory name"):
                        main.move_proton_dir(home, invalid_name)

    def test_copy_failure_preserves_existing_install_and_cleans_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home = root / "home"
            compatibility_tools = home / ".steam" / "root" / "compatibilitytools.d"
            target = compatibility_tools / "custom-proton"
            target.mkdir(parents=True)
            marker = target / "keep.txt"
            marker.write_text("old install", encoding="utf-8")

            work_dir = root / "work"
            dist = work_dir / "dist"
            dist.mkdir(parents=True)
            (dist / "new.txt").write_text("new install", encoding="utf-8")

            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                with patch("main.shutil.copytree", side_effect=OSError("disk full")):
                    with self.assertRaisesRegex(OSError, "disk full"):
                        main.move_proton_dir(str(home), "custom-proton")
            finally:
                os.chdir(old_cwd)

            self.assertEqual(marker.read_text(encoding="utf-8"), "old install")
            leftovers = [path.name for path in compatibility_tools.iterdir() if path.name.startswith(".custom-proton.")]
            self.assertEqual(leftovers, [])

    def test_activation_failure_restores_existing_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home = root / "home"
            compatibility_tools = home / ".steam" / "root" / "compatibilitytools.d"
            target = compatibility_tools / "custom-proton"
            target.mkdir(parents=True)
            marker = target / "keep.txt"
            marker.write_text("old install", encoding="utf-8")

            work_dir = root / "work"
            dist = work_dir / "dist"
            dist.mkdir(parents=True)
            (dist / "new.txt").write_text("new install", encoding="utf-8")

            real_rename = os.rename

            def rename_with_activation_failure(src: str, dst: str) -> None:
                if Path(src).name.startswith(".custom-proton.new-") and Path(dst) == target:
                    raise OSError("activation failed")
                real_rename(src, dst)

            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                with patch("main.os.rename", side_effect=rename_with_activation_failure):
                    with self.assertRaisesRegex(OSError, "activation failed"):
                        main.move_proton_dir(str(home), "custom-proton")
            finally:
                os.chdir(old_cwd)

            self.assertEqual(marker.read_text(encoding="utf-8"), "old install")
            self.assertFalse((target / "new.txt").exists())
            leftovers = [path.name for path in compatibility_tools.iterdir() if path.name.startswith(".custom-proton.")]
            self.assertEqual(leftovers, [])

    def test_successful_replacement_removes_backup_and_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home = root / "home"
            compatibility_tools = home / ".steam" / "root" / "compatibilitytools.d"
            target = compatibility_tools / "custom-proton"
            target.mkdir(parents=True)
            (target / "old.txt").write_text("old install", encoding="utf-8")

            work_dir = root / "work"
            dist = work_dir / "dist"
            dist.mkdir(parents=True)
            (dist / "new.txt").write_text("new install", encoding="utf-8")

            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                main.move_proton_dir(str(home), "custom-proton")
            finally:
                os.chdir(old_cwd)

            self.assertEqual((target / "new.txt").read_text(encoding="utf-8"), "new install")
            self.assertFalse((target / "old.txt").exists())
            leftovers = [path.name for path in compatibility_tools.iterdir() if path.name.startswith(".custom-proton.")]
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
