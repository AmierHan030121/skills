import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "imagen.py"


class ModelSelectionTests(unittest.TestCase):
    def dry_run(self, *extra):
        with tempfile.TemporaryDirectory(prefix="imagen-test-") as directory:
            root = Path(directory)
            config = root / "config.toml"
            config.write_text(
                'image_base_url = "https://example.invalid/v1"\n'
                'image_apikey = "offline-test-key"\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--prompt", "test image",
                 "--config", str(config), "--out-dir", str(root),
                 "--dry-run", *extra],
                capture_output=True, text=True, check=True,
            )
            return json.loads(result.stdout)

    def test_default_request_uses_sunburst(self):
        self.assertEqual(self.dry_run()["model"], "gpt-image-2.5-sunburst")

    def test_explicit_model_overrides_default(self):
        self.assertEqual(self.dry_run("--model", "gpt-image-2")["model"], "gpt-image-2")


if __name__ == "__main__":
    unittest.main()
