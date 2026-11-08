import shutil
import unittest

from git_ritual.core import git_ops
from git_ritual.core.diagnostics import ErrorKind
from tests.support import GitCase, run_git


@unittest.skipUnless(shutil.which("git"), "git requis")
class LocalRepo(GitCase):
    def test_init_uses_requested_branch_even_before_first_commit(self):
        repo = self.make_project()
        self.assertFalse(repo.is_repo())
        repo.init("main")
        self.assertTrue(repo.is_repo())
        self.assertEqual(repo.current_branch(), "main")
        self.assertFalse(repo.has_commits())

    def test_changes_commit_and_clean_state(self):
        repo = self.make_project(files={"a.txt": "x", "dir/b.txt": "y", "sp ace.txt": "z"})
        repo.init()
        paths = sorted(c.path for c in repo.changes())
        self.assertEqual(paths, ["a.txt", "dir/b.txt", "sp ace.txt"])
        self.assertTrue(all(c.untracked for c in repo.changes()))
        self.assertTrue(repo.add_all().ok)
        self.assertTrue(repo.commit("Initial commit").ok)
        self.assertEqual(repo.changes(), [])
        self.assertTrue(repo.has_commits())
        self.assertEqual(len(repo.log()), 1)

    def test_nothing_to_commit_is_classified(self):
        repo = self.make_project()
        repo.init()
        repo.add_all(); repo.commit("one")
        out = repo.commit("two")
        self.assertFalse(out.ok)
        self.assertEqual(out.kind, ErrorKind.NOTHING_TO_COMMIT)

    def test_rename_detection_does_not_duplicate(self):
        repo = self.make_project()
        repo.init(); repo.add_all(); repo.commit("one")
        run_git(repo.path, "mv", "a.txt", "renamed.txt")
        self.assertEqual([c.path for c in repo.changes()], ["renamed.txt"])

    def test_rename_branch_before_and_after_commit(self):
        repo = self.make_project()
        repo.init("master")
        self.assertTrue(repo.rename_branch("main").ok)
        self.assertEqual(repo.current_branch(), "main")
        repo.add_all(); repo.commit("one")
        self.assertTrue(repo.rename_branch("dev").ok)
        self.assertEqual(repo.current_branch(), "dev")

    def test_nested_repo_detection(self):
        parent = self.make_project("parent")
        parent.init()
        child = self.root / "parent" / "child"
        child.mkdir()
        self.assertEqual(git_ops.Repo(child).parent_repo(), parent.path.resolve())
        self.assertFalse(git_ops.Repo(child).is_repo())

    def test_identity_roundtrip(self):
        git_ops.set_identity("Ada", "ada@example.com")
        self.assertEqual(git_ops.get_identity(), ("Ada", "ada@example.com"))

    def test_commit_without_identity_is_classified(self):
        (self.home / ".gitconfig").write_text("")
        repo = self.make_project()
        repo.init(); repo.add_all()
        out = repo.commit("x")
        self.assertFalse(out.ok)
        self.assertEqual(out.kind, ErrorKind.NO_IDENTITY)


@unittest.skipUnless(shutil.which("git"), "git requis")
class RemoteWorkflows(GitCase):
    def published(self, name="proj", files=None):
        remote = self.make_bare_remote(f"{name}.git")
        repo = self.make_project(name, files)
        repo.init(); repo.add_all(); repo.commit("Initial commit")
        self.assertTrue(repo.set_remote(str(remote)).ok)
        return repo, remote

    def test_check_remote_ok_even_when_empty_and_not_found(self):
        remote = self.make_bare_remote()
        self.assertTrue(git_ops.check_remote(str(remote)).ok)
        bad = git_ops.check_remote(str(self.root / "absent.git"))
        self.assertFalse(bad.ok)
        self.assertEqual(bad.kind, ErrorKind.NOT_FOUND)
        self.assertFalse(git_ops.check_remote("-oProxyCommand=x").ok)

    def test_set_remote_adds_then_updates(self):
        repo = self.make_project(); repo.init()
        self.assertIsNone(repo.get_remote_url())
        repo.set_remote("/a.git"); self.assertEqual(repo.get_remote_url(), "/a.git")
        repo.set_remote("/b.git"); self.assertEqual(repo.get_remote_url(), "/b.git")

    def test_push_and_sync_state(self):
        repo, remote = self.published()
        self.assertIsNone(repo.ahead_behind())
        out = repo.push("main")
        self.assertTrue(out.ok, out.output)
        self.assertEqual(repo.ahead_behind(), (0, 0))
        (repo.path / "b.txt").write_text("new")
        repo.add_all(); repo.commit("second")
        self.assertEqual(repo.ahead_behind(), (1, 0))

    def test_push_without_commit_is_classified(self):
        remote = self.make_bare_remote()
        repo = self.make_project(); repo.init(); repo.set_remote(str(remote))
        out = repo.push("main")
        self.assertEqual(out.kind, ErrorKind.NO_COMMITS)

    def test_rejected_then_merge_then_push(self):
        """Scénario réel : GitHub a créé un README, on a des fichiers différents en local."""
        repo, remote = self.published(files={"app.py": "print(1)\n"})
        other = self.root / "other"
        run_git(self.root, "clone", str(remote), str(other))  # dépôt vide
        (other / "LICENSE").write_text("MIT\n")
        run_git(other, "add", "-A"); run_git(other, "commit", "-m", "Add license")
        run_git(other, "push", "origin", "HEAD:main")

        rejected = repo.push("main")
        self.assertFalse(rejected.ok)
        self.assertEqual(rejected.kind, ErrorKind.REJECTED)

        merged = repo.pull_merge("main")
        self.assertTrue(merged.ok, merged.output)
        self.assertTrue((repo.path / "LICENSE").exists())
        self.assertTrue(repo.push("main").ok)

    def _conflict_setup(self):
        repo, remote = self.published(files={"README.md": "mine\n"})
        other = self.root / "other"
        run_git(self.root, "init", "-b", "main", str(other))
        (other / "README.md").write_text("theirs\n")
        run_git(other, "add", "-A"); run_git(other, "commit", "-m", "readme")
        run_git(other, "push", str(remote), "main")
        out = repo.pull_merge("main")
        return repo, out

    def test_add_add_conflict_keep_mine(self):
        repo, out = self._conflict_setup()
        self.assertFalse(out.ok)
        self.assertEqual(out.kind, ErrorKind.CONFLICT)
        self.assertTrue(repo.merge_in_progress())
        self.assertEqual(repo.conflicted_files(), ["README.md"])
        result = repo.resolve_conflicts("ours")
        self.assertTrue(result.ok, result.output)
        self.assertEqual((repo.path / "README.md").read_text(), "mine\n")
        self.assertFalse(repo.merge_in_progress())
        self.assertTrue(repo.push("main").ok)

    def test_add_add_conflict_keep_theirs(self):
        repo, _ = self._conflict_setup()
        self.assertTrue(repo.resolve_conflicts("theirs").ok)
        self.assertEqual((repo.path / "README.md").read_text(), "theirs\n")

    def test_conflict_abort(self):
        repo, _ = self._conflict_setup()
        self.assertTrue(repo.abort_merge().ok)
        self.assertFalse(repo.merge_in_progress())
        self.assertEqual((repo.path / "README.md").read_text(), "mine\n")

    def test_resolve_strategy_validated(self):
        repo = self.make_project(); repo.init()
        with self.assertRaises(ValueError):
            repo.resolve_conflicts("force")


if __name__ == "__main__":
    unittest.main()
