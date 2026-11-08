import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import safety, shell, storage
from utils import paths, validators as v


class Safety(unittest.TestCase):
    def test_risky_files(self):
        found = safety.risky_files([
            "app.py", ".env", "config/.env.local", "keys/server.pem", "id_ed25519",
            ".env.example", "id_ed25519.pub", "credentials-prod.json", "README.md",
        ])
        self.assertEqual(found, [".env", "config/.env.local", "keys/server.pem", "id_ed25519", "credentials-prod.json"])

    def test_add_to_gitignore_is_idempotent_and_anchored(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".gitignore").write_text("node_modules")  # sans retour ligne final
            safety.add_to_gitignore(tmp, [".env", "keys/a.pem"])
            safety.add_to_gitignore(tmp, [".env"])
            self.assertEqual((Path(tmp) / ".gitignore").read_text().splitlines(), ["node_modules", "/.env", "/keys/a.pem"])

    def test_python_detection_and_default_gitignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(safety.looks_like_python(tmp))
            (Path(tmp) / "pkg").mkdir(); (Path(tmp) / "pkg" / "m.py").write_text("")
            self.assertTrue(safety.looks_like_python(tmp))
            safety.write_default_gitignore(tmp)
            self.assertIn("__pycache__/", (Path(tmp) / ".gitignore").read_text())
            (Path(tmp) / ".gitignore").write_text("custom\n")
            safety.write_default_gitignore(tmp)  # n'écrase pas
            self.assertEqual((Path(tmp) / ".gitignore").read_text(), "custom\n")


class Storage(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        p = mock.patch.dict(os.environ, {"GIT_RITUAL_HOME": str(Path(self._tmp.name) / "h")})
        p.start(); self.addCleanup(p.stop); self.addCleanup(self._tmp.cleanup)

    def test_defaults_roundtrip_and_invalid_values(self):
        self.assertEqual(storage.load_settings(), storage.DEFAULT_SETTINGS)
        s = storage.load_settings(); s["github_username"] = "me"; s["accent"] = "pink"
        self.assertTrue(storage.save_settings(s))
        loaded = storage.load_settings()
        self.assertEqual((loaded["github_username"], loaded["accent"]), ("me", "cyan"))
        storage.settings_path().write_text("{broken")
        self.assertEqual(storage.load_settings(), storage.DEFAULT_SETTINGS)

    def test_defaults_are_not_shared_between_loads(self):
        storage.load_settings()["recent_projects"].append("x")
        self.assertEqual(storage.load_settings()["recent_projects"], [])

    def test_recent_projects_unique_ordered_limited(self):
        for i in range(12):
            storage.add_recent_project(f"/p{i}")
        storage.add_recent_project("/p5")
        recents = storage.load_settings()["recent_projects"]
        self.assertEqual(recents[0], "/p5")
        self.assertEqual(len(recents), storage.RECENT_LIMIT)
        self.assertEqual(len(set(recents)), len(recents))


class Paths(unittest.TestCase):
    def test_resolve_and_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp).resolve()
            (tmp / "proj").mkdir(); (tmp / "file.txt").write_text("x")
            self.assertEqual(paths.resolve_project_path(str(tmp / "proj")), tmp / "proj")
            self.assertEqual(paths.resolve_project_path(f'"{tmp / "proj"}"'), tmp / "proj")
            self.assertEqual(paths.resolve_project_path("proj", base_dir=tmp), tmp / "proj")
            with self.assertRaises(v.ValidationError): paths.resolve_project_path("")
            with self.assertRaises(v.ValidationError): paths.resolve_project_path(str(tmp / "absent"))
            with self.assertRaises(v.ValidationError): paths.resolve_project_path(str(tmp / "file.txt"))
            with self.assertRaises(v.ValidationError): paths.resolve_project_path(str(tmp), home=tmp)
            with self.assertRaises(v.ValidationError): paths.resolve_project_path("/")


class Validators(unittest.TestCase):
    def test_all(self):
        self.assertEqual(v.validate_username("Bienvenu945"), "Bienvenu945")
        for bad in ("", "-x", "a b", "a_b"):
            with self.subTest(bad=bad), self.assertRaises(v.ValidationError): v.validate_username(bad)
        self.assertEqual(v.validate_repo_name("Dosto_crypt"), "Dosto_crypt")
        for bad in ("", "..", "a/b", "a b"):
            with self.subTest(bad=bad), self.assertRaises(v.ValidationError): v.validate_repo_name(bad)
        for ok in ("main", "feature/login", "v1.0"):
            self.assertEqual(v.validate_branch(ok), ok)
        for bad in ("", "-x", "a..b", "/x", "x/", "a b", "x.lock", "a//b"):
            with self.subTest(bad=bad), self.assertRaises(v.ValidationError): v.validate_branch(bad)
        self.assertEqual(v.validate_email(" a@b.co "), "a@b.co")
        with self.assertRaises(v.ValidationError): v.validate_email("nope")
        with self.assertRaises(v.ValidationError): v.validate_name("  ")
        with self.assertRaises(v.ValidationError): v.validate_commit_message(" ")


class Shell(unittest.TestCase):
    def test_run_missing_tool_and_timeout(self):
        with self.assertRaises(shell.ToolMissingError) as ctx:
            shell.run(["definitely-not-a-tool-xyz"])
        self.assertEqual(ctx.exception.tool, "definitely-not-a-tool-xyz")
        r = shell.run(["sleep", "5"], timeout=1)
        self.assertEqual(r.returncode, 124)
        self.assertIn("Délai dépassé", r.output)

    def test_output_and_english_messages(self):
        r = shell.run(["python3", "-c", "import os,sys; print(os.environ['LC_ALL']); sys.stderr.write('err')"])
        self.assertEqual(r.output, "err\nC")
        self.assertTrue(r.ok)


if __name__ == "__main__":
    unittest.main()
