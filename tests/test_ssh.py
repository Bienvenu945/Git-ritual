import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import shell, ssh


def result(code, text=""):
    return shell.CommandResult(("ssh",), code, "", text)


class SshTesting(unittest.TestCase):
    def check(self, code, text):
        with mock.patch.object(ssh.shell, "run", return_value=result(code, text)):
            return ssh.test_github()

    def test_success_extracts_username(self):
        r = self.check(1, "Hi Bienvenu945! You've successfully authenticated, but GitHub does not provide shell access.")
        self.assertEqual((r.status, r.username), ("ok", "Bienvenu945"))

    def test_denied_hostkey_network_error(self):
        self.assertEqual(self.check(255, "git@github.com: Permission denied (publickey).").status, "denied")
        self.assertEqual(self.check(255, "Host key verification failed.").status, "hostkey")
        self.assertEqual(self.check(255, "ssh: Could not resolve hostname github.com").status, "network")
        self.assertEqual(self.check(1, "weird").status, "error")

    def test_known_host(self):
        with mock.patch.object(ssh.shell, "run", return_value=shell.CommandResult(("x",), 0, "# Host github.com found", "")):
            self.assertTrue(ssh.known_host())
        with mock.patch.object(ssh.shell, "run", return_value=shell.CommandResult(("x",), 1, "", "")):
            self.assertFalse(ssh.known_host())


class Keys(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        p = mock.patch.dict(os.environ, {"HOME": self._tmp.name})
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_find_public_keys_prefers_ed25519(self):
        d = Path(self._tmp.name, ".ssh"); d.mkdir()
        for name in ("id_rsa.pub", "id_ed25519.pub", "notes.txt"):
            (d / name).write_text("k")
        self.assertEqual([p.name for p in ssh.find_public_keys()], ["id_ed25519.pub", "id_rsa.pub"])

    def test_no_ssh_dir(self):
        self.assertEqual(ssh.find_public_keys(), [])

    def test_generate_key_command_and_never_overwrites(self):
        with mock.patch.object(ssh.shell, "run", return_value=result(0)) as run:
            public = ssh.generate_key("me@example.com")
        self.assertEqual(public.name, "id_ed25519.pub")
        args = run.call_args.args[0]
        self.assertEqual(args[:5], ["ssh-keygen", "-q", "-t", "ed25519", "-C"])
        self.assertEqual(args[-2:], ["-N", ""])
        (Path(self._tmp.name) / ".ssh" / "id_ed25519").write_text("existing")
        with self.assertRaises(ssh.SshError):
            ssh.generate_key("me@example.com")
        self.assertEqual((Path(self._tmp.name) / ".ssh" / "id_ed25519").read_text(), "existing")

    @unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen requis")
    def test_real_generation(self):
        public = ssh.generate_key("me@example.com")
        self.assertTrue(ssh.public_key_text(public).startswith("ssh-ed25519 "))
        self.assertEqual(oct(public.parent.stat().st_mode & 0o777), "0o700")


if __name__ == "__main__":
    unittest.main()
