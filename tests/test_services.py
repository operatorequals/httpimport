import logging

import httpimport
from tests import HttpImportTest


class TestServices(HttpImportTest):

    def test_github_repo(self):
        print("[+] Importing from GitHub")
        with httpimport.github_repo('operatorequals', 'httpimport-test', ref='main'):
            import test_package

        self.assertTrue(test_package)

    def test_bitbucket_repo(self):
        print("[+] Importing from BitBucket")
        with httpimport.bitbucket_repo('operatorequals', 'httpimport-test', ref='main'):
            import test_package

        self.assertTrue(test_package)

    def test_gitlab_repo(self):
        print("[+] Importing from GitLab")
        with httpimport.gitlab_repo('operatorequals', 'httpimport-test', ref='main'):
            import test_package

        self.assertTrue(test_package)
