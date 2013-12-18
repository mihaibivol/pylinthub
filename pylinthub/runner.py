"""
Module with functions for running pylint integrated with Github.
"""
import linecache
from pylint import lint
from pylint.reporters.text import TextReporter

from pylinthub.github_client import GithubPullReviewClient

PYLINT_ARGS = ["-r", "n",
               "--msg-template='{path}:{line}:{msg}'"]

class PylintWriteHandler(object):
    """Used as TextReporter for parsing output lines from running pylint."""
    def __init__(self, github):
        self.github = github

    def write(self, string):
        """Write wrapper"""
        string = string.strip()
        # Some useless strings are generated
        if string == "" or string.startswith("****"):
            return

        path, line, body = string.split(":")
        context = linecache.getline(path, int(line)).strip()
        self.github.create_review_comment(context, path, body)

def review_pull_request(repository, pull_request, **credentials):
    """Creates inline comments on the given pull request with the
    errors given by pylint"""
    github = GithubPullReviewClient(repository, pull_request, **credentials)

    files = github.get_changed_files()
    files = [f for f in files if f.endswith(".py")]

    handler = PylintWriteHandler(github)
    lint.Run(PYLINT_ARGS + files, reporter=TextReporter(handler), exit=False)

