import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class RepositoryIdentityTests(unittest.TestCase):
    def test_canonical_git_remote_accepts_https_and_ssh_forms(self) -> None:
        https = "https://github.com/ValveSoftware/Proton.git"
        ssh = "git@github.com:ValveSoftware/Proton.git"
        ssh_url = "ssh://git@github.com/ValveSoftware/Proton.git"

        self.assertEqual(main.canonical_git_remote(https), main.canonical_git_remote(ssh))
        self.assertEqual(main.canonical_git_remote(https), main.canonical_git_remote(ssh_url))

    def test_rejects_checkout_from_unexpected_origin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            (work_dir / "Proton").mkdir()

            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                with patch(
                    "main.subprocess.check_output",
                    side_effect=[
                        "true\n",
                        "",
                        "bleeding-edge\n",
                        "https://github.com/example/not-proton.git\n",
                    ],
                ):
                    with self.assertRaisesRegex(RuntimeError, "does not match the expected repository"):
                        main.prepare_proton_repository(
                            "https://github.com/ValveSoftware/Proton.git",
                            "bleeding-edge",
                        )
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
