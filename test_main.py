import os
import tempfile
import unittest
from pathlib import Path

import main


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
                    main.move_proton_dir(str(home), "custom-proton", True)
            finally:
                os.chdir(old_cwd)

            self.assertTrue(marker.exists())
            self.assertTrue(symlink.is_symlink())

    def test_rejects_invalid_directory_name_when_called_directly(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            with self.assertRaisesRegex(ValueError, "Invalid Proton directory name"):
                main.move_proton_dir(home, "../outside", False)


if __name__ == "__main__":
    unittest.main()
