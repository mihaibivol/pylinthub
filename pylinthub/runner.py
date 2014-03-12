"""
Module with functions for running pylint integrated with Github.
"""
import linecache
from pylint import lint
from pylint.reporters.text import TextReporter

from pylinthub.github_client import GithubPullReviewClient

PYLINT_ARGS = ["-r", "n",
               "--msg-template='{path}#&#&{line}#&#&{msg}'"]

class GithubWriter(object):
    """Abstract class used for adding side effects when parsing pylint
    output."""

    def __init__(self, github):
        self.github = github

    def handle_pylint_error(self, path, line, code, message):
        """Implement this to add side effect when encountering an error
        """
        raise NotImplementedError

    def write(self, string):
        """Write wrapper"""
        string = string.strip()
        # Some useless strings are generated
        if string == "" or string.startswith("****"):
            return

        path, line, message = string.split("#&#&")
        code = linecache.getline(path, int(line)).strip()
        self.handle_pylint_error(path, line, code, message)

    def flush(self):
        """Implement this to add the final side effect, after passing
        through the whole error report."""
        raise NotImplementedError

class GithubInlineWriter(GithubWriter):
    """Writes inline comments with the pylint errors found in the analyzed
    files"""

    def handle_pylint_error(self, path, line, code, message):
        """Post inline message on the pull request"""

        comments = self.github.get_review_comments(code, path)

        #If already commented don't comment again
        if message in [c.body for c in comments]:
            return

        self.github.create_review_comment(code, path, message)

    def flush(self):
        pass

class GithubCommentWriter(GithubWriter):
    """Edits a static comment in the GitHub Pull Request"""
    COMMENT_HEADER = "Linter Errors:"

    def __init__(self, github):
        super(GithubCommentWriter, self).__init__(github)
        self.file_line_code = {}
        self.file_line_messages = {}
        self.candidates = set()
        self._add_candidate_lines()

    def _add_candidate_lines(self):
        """Creates a cache with the code lines that are candidates for
        errors in the pull request."""
        for f in self.github.get_files():
            for line in f.patch.splitlines():
                line = line.lstrip('+')
                self.candidates.add(line)

    def handle_pylint_error(self, path, line, code, message):
        """Appends errors to local structures"""

        # We don't want to receive verbose messages with errors that weren't
        #added in the current pull request
        if code not in self.candidates:
            return

        file_line_key = '%s:%s' % (path, line)

        self.file_line_code[file_line_key] = code
        messages = self.file_line_messages.get(file_line_key, [])
        messages.append(message)
        self.file_line_messages[file_line_key] = messages

    def flush(self):
        """Creates a github comment with the errors found in the file"""
        body = self.COMMENT_HEADER + '\n'

        ## Have keys sorted so the comments are in the correct order
        for file_line in sorted(self.file_line_messages.keys()):
            body += 'In %s:\n' % file_line
            body += '```python\n%s\n```\n' % self.file_line_code[file_line]

            for message in self.file_line_messages[file_line]:
                body += '  * %s\n' % message

            body += '\n'

        self.github.create_or_update_comment(self.COMMENT_HEADER, body)

def review_pull_request(repository, pull_request, pylintrc,
                        inline=False, **credentials):
    """Creates inline comments on the given pull request with the
    errors given by pylint"""
    github = GithubPullReviewClient(repository, pull_request, **credentials)

    files = github.get_changed_files()
    files = [f for f in files if f.endswith(".py")]

    handler = GithubInlineWriter(github) if inline else GithubCommentWriter(github)

    args = PYLINT_ARGS

    if pylintrc is not None:
        # Do not append to the existing constant
        args = args + ["--rcfile %s" % pylintrc]

    lint.Run(PYLINT_ARGS + files, reporter=TextReporter(handler), exit=False)
    handler.flush()

