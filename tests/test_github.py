import unittest
from unittest import mock

from core import github as gh
from core import shell
from utils.validators import ValidationError


class ParseTarget(unittest.TestCase):
    def test_ssh_url(self):
        t = gh.parse_target("git@github.com:Bienvenu945/Dosto_crypt.git")
        self.assertEqual((t.url, t.owner, t.name), ("git@github.com:Bienvenu945/Dosto_crypt.git", "Bienvenu945", "Dosto_crypt"))
        self.assertEqual(t.web_url, "https://github.com/Bienvenu945/Dosto_crypt")

    def test_accidental_space_after_colon_is_fixed(self):
        # Erreur réelle : « git@github.com: Bienvenu945/dosto-crypt.git »
        t = gh.parse_target("git@github.com: Bienvenu945/dosto-crypt.git")
        self.assertEqual(t.url, "git@github.com:Bienvenu945/dosto-crypt.git")

    def test_https_github_is_converted_to_ssh(self):
        t = gh.parse_target("https://github.com/Bienvenu945/Dosto_crypt/")
        self.assertEqual(t.url, "git@github.com:Bienvenu945/Dosto_crypt.git")

    def test_slug_and_bare_name(self):
        self.assertEqual(gh.parse_target("me/repo").url, "git@github.com:me/repo.git")
        self.assertEqual(gh.parse_target("repo", default_owner="me").url, "git@github.com:me/repo.git")
        self.assertEqual(gh.parse_target("repo.git", default_owner="me").name, "repo")

    def test_bare_name_needs_owner(self):
        with self.assertRaises(ValidationError):
            gh.parse_target("repo")

    def test_other_hosts_are_kept(self):
        t = gh.parse_target("git@gitlab.com:me/proj.git")
        self.assertEqual((t.url, t.host, t.is_github, t.web_url), ("git@gitlab.com:me/proj.git", "gitlab.com", False, None))

    def test_local_paths_are_kept_as_is(self):
        self.assertEqual(gh.parse_target("/tmp/my repo.git").url, "/tmp/my repo.git")
        self.assertEqual(gh.parse_target("file:///tmp/r.git").url, "file:///tmp/r.git")

    def test_rejects_dangerous_or_garbage_input(self):
        for bad in ("", "   ", "-oProxyCommand=x", "ext::sh -c id", "a/b/c/d", "https://github.com/onlyowner"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                gh.parse_target(bad, default_owner="me")

    def test_is_bare_name(self):
        self.assertTrue(gh.is_bare_name("dosto-crypt"))
        self.assertFalse(gh.is_bare_name("me/repo"))
        self.assertFalse(gh.is_bare_name("git@github.com:a/b.git"))


class Suggestions(unittest.TestCase):
    def test_hyphen_vs_underscore_and_case(self):
        # Cas réel : saisi « dosto-crypt », créé « Dosto_crypt ».
        self.assertEqual(gh.suggest_names("dosto-crypt", ["Dosto_crypt", "autre-chose"]), ["Dosto_crypt"])

    def test_no_suggestion_when_exact_or_unrelated(self):
        self.assertEqual(gh.suggest_names("abc", ["abc"]), [])
        self.assertEqual(gh.suggest_names("zzzz", ["Dosto_crypt"]), [])


class GhHelpers(unittest.TestCase):
    def test_create_repo_command(self):
        ok = shell.CommandResult(("gh",), 0, "", "")
        with mock.patch.object(gh.shell, "run", return_value=ok) as run:
            gh.create_repo("me", "repo", private=True, description="Desc")
        self.assertEqual(run.call_args.args[0], ["gh", "repo", "create", "me/repo", "--private", "--description", "Desc"])
        with mock.patch.object(gh.shell, "run", return_value=ok) as run:
            gh.create_repo("me", "repo", private=False)
        self.assertEqual(run.call_args.args[0][-1], "--public")

    def test_list_repos(self):
        out = shell.CommandResult(("gh",), 0, "a\nb\n", "")
        with mock.patch.object(gh.shell, "run", return_value=out):
            self.assertEqual(gh.list_repos("me"), ["a", "b"])
        fail = shell.CommandResult(("gh",), 1, "", "not logged in")
        with mock.patch.object(gh.shell, "run", return_value=fail):
            self.assertEqual(gh.list_repos("me"), [])

    def test_gh_not_installed(self):
        with mock.patch.object(gh.shell, "which", return_value=None):
            self.assertFalse(gh.gh_available())
            self.assertFalse(gh.gh_logged_in())


if __name__ == "__main__":
    unittest.main()
