import tempfile
import unittest
from pathlib import Path

from ceurws.utils.download import Download


class TestDownload(unittest.TestCase):
    """
    test download
    """

    def test_downloadBackupFile(self):
        """
        test downloadBackupFile
        """
        url = "https://github.com/WolfgangFahl/pyCEURmake/archive/refs/tags/v0.4.0.tar.gz"
        with tempfile.TemporaryDirectory() as tmpdir:
            name = "pyCEURmake-0.4.0"
            temp_dir = Path(tmpdir)
            target_dir = temp_dir.joinpath(name)
            zip_file = temp_dir.joinpath(f"{name}.gz")
            self.assertFalse(zip_file.exists())
            Download.downloadBackupFile(url, fileName=name, targetDirectory=temp_dir)
            self.assertTrue(zip_file.exists())
            self.assertTrue(zip_file.is_file())
            self.assertTrue(target_dir.exists())


if __name__ == "__main__":
    unittest.main()
