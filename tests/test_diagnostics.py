import unittest

from git_ritual.core.diagnostics import ErrorKind, classify, explain

# Messages réels rencontrés lors d'une publication sur GitHub.
CASES = {
    ErrorKind.NOT_FOUND: [
        "ERROR: Repository not found.\nfatal: Could not read from remote repository.\n\n"
        "Please make sure you have the correct access rights\nand the repository exists.",
        "remote: Repository not found.\nfatal: repository 'https://github.com/x/y/' not found",
        "fatal: '/tmp/nope.git' does not appear to be a git repository",
    ],
    ErrorKind.AUTH_SSH: [
        "git@github.com: Permission denied (publickey).\nfatal: Could not read from remote repository.\n\n"
        "Please make sure you have the correct access rights\nand the repository exists.",
    ],
    ErrorKind.AUTH_HTTPS: [
        "Invalid username or token. Password authentication is not supported for Git operations.\n"
        "fatal: Authentication failed for 'https://github.com/Bienvenu945/Dosto_crypt/'",
    ],
    ErrorKind.HOSTKEY: ["Host key verification failed.\nfatal: Could not read from remote repository."],
    ErrorKind.NETWORK: [
        "ssh: Could not resolve hostname github.com: Temporary failure in name resolution",
        "Délai dépassé (30 s) : git",
        "ssh: connect to host github.com port 22: Connection timed out",
    ],
    ErrorKind.REJECTED: [
        " ! [rejected]        main -> main (fetch first)\nerror: failed to push some refs to 'github.com:a/b.git'",
        " ! [rejected]        main -> main (non-fast-forward)\nerror: failed to push some refs",
    ],
    ErrorKind.DIVERGENT: ["hint: You have divergent branches\nfatal: Need to specify how to reconcile divergent branches."],
    ErrorKind.UNRELATED: ["fatal: refusing to merge unrelated histories"],
    ErrorKind.CONFLICT: [
        "CONFLICT (add/add): Merge conflict in README.md\nAutomatic merge failed; fix conflicts and then commit the result.",
    ],
    ErrorKind.NO_COMMITS: ["error: src refspec main does not match any\nerror: failed to push some refs to 'x'"],
    ErrorKind.NO_IDENTITY: ["*** Please tell me who you are.\n\nRun\n  git config --global user.email"],
    ErrorKind.NOTHING_TO_COMMIT: ["On branch main\nnothing to commit, working tree clean"],
}


class Classify(unittest.TestCase):
    def test_known_messages(self):
        for expected, messages in CASES.items():
            for message in messages:
                with self.subTest(expected=expected.name, message=message[:40]):
                    self.assertEqual(classify(message), expected)

    def test_ssh_denied_is_not_mistaken_for_not_found(self):
        # Les deux messages se terminent par la même phrase « repository exists ».
        self.assertEqual(classify(CASES[ErrorKind.AUTH_SSH][0]), ErrorKind.AUTH_SSH)

    def test_unknown_is_other(self):
        self.assertEqual(classify("something odd happened"), ErrorKind.OTHER)
        self.assertEqual(classify(""), ErrorKind.OTHER)

    def test_every_kind_has_an_explanation(self):
        for kind in ErrorKind:
            if kind is ErrorKind.NONE:
                continue
            title, hint = explain(kind)
            self.assertTrue(title and hint, kind)


if __name__ == "__main__":
    unittest.main()
