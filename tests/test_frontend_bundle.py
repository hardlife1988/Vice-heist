"""Packaging checks use temporary paths and never regenerate game math."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "math"))
import build_stake_bundle as bundle


class FrontendBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "static"
        self.output = self.root / "dist"
        self.publish = self.root / "publish_files"
        self.source.mkdir()
        for name in ("index.html", "style.css", "game.js"):
            (self.source / name).write_text(f"source {name}", encoding="utf-8")
        self.assets = {
            "symbols/wild.webp": b"\x00\xffimage",
            "audio/reel_stop.wav": b"\x00\xfeaudio",
            "backgrounds/city.webp": b"\x00\xfdbackground",
            "ui/nested/frame.webp": b"\x00\xfcframe",
        }
        for name, data in self.assets.items():
            path = self.source / "assets" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        paths = patch.multiple(
            bundle, STATIC=str(self.source), DIST=str(self.output),
            OUT=str(self.publish),
        )
        paths.start()
        self.addCleanup(paths.stop)

    def test_clean_output_includes_recursive_binary_assets(self):
        bundle.copy_frontend()
        for name in ("index.html", "style.css", "game.js"):
            self.assertEqual(
                (self.output / name).read_bytes(),
                (self.source / name).read_bytes(),
            )
        for name, data in self.assets.items():
            self.assertEqual((self.output / "assets" / name).read_bytes(), data)

    def test_frontend_only_preserves_math_and_skips_generation(self):
        self.output.mkdir()
        self.publish.mkdir()
        preserved = {}
        for name in (
            "books_base.json", "books_bonus.json", "lookUpTable_base.csv",
            "lookUpTable_bonus.csv", "game_config.json",
        ):
            path = self.output / name
            preserved[path] = b"existing runtime " + name.encode()
        for name in ("index.json", "books_base.jsonl.zst", "math_summary.json"):
            path = self.publish / name
            preserved[path] = b"existing publish " + name.encode()
        for path, data in preserved.items():
            path.write_bytes(data)
        with (
            patch.object(sys, "argv", ["build_stake_bundle.py", "--frontend-only"]),
            patch.object(bundle, "BookBuilder") as builder,
            patch.object(bundle.random, "seed") as seed,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            bundle.main()
        builder.assert_not_called()
        seed.assert_not_called()
        for path, data in preserved.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertEqual(
            (self.output / "assets/audio/reel_stop.wav").read_bytes(),
            self.assets["audio/reel_stop.wav"],
        )

    def test_missing_source_fails_before_changing_output(self):
        self.output.mkdir()
        marker = self.output / "index.html"
        marker.write_text("existing output", encoding="utf-8")
        for name in ("index.html", "style.css", "game.js", "assets"):
            with self.subTest(name=name):
                path = self.source / name
                moved = self.source / f"missing-{name}"
                path.rename(moved)
                try:
                    with self.assertRaisesRegex(FileNotFoundError, str(path)):
                        bundle.copy_frontend()
                    self.assertEqual(marker.read_text(encoding="utf-8"), "existing output")
                finally:
                    moved.rename(path)


if __name__ == "__main__":
    unittest.main()
