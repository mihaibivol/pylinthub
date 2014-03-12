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

class Violation(object):
    """Class used in representing a style violation."""

    def __init__(self, path, url, line, code, message):
        self.path = path
        self.url = url
        self.line = line
        self.code = code
        self.message = message

class GithubCommentWriter(GithubWriter):
    """Edits a static comment in the GitHub Pull Request"""
    COMMENT_HEADER = "Linter Errors:"

    def __init__(self, github):
        super(GithubCommentWriter, self).__init__(github)
        self.violations = {}
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

        file_violations = self.violations.get(path, [])
        file_violations.append(Violation(path, "", int(line), code, message))
        self.violations[path] = file_violations

    def _get_comment_body(self):
        """Formats a comment body."""
        body = self.COMMENT_HEADER + '\n'

        if len(self.violations) == 0:
            body += "No Errors\n"

        for filename, file_violations in self.violations.iteritems():
            body += 'In %s:\n' % filename

            unique_lines = set([v.line for v in file_violations])

            # Group violations by line of code
            line_violations = {line: [v for v in file_violations
                                        if v.line == line]
                               for line in unique_lines}

            # We want the messages in order so sort them as ints
            # because '11' < '2' in string comparison
            for line in sorted(line_violations.keys()):
                violations = line_violations[line]

                # we will always have at least one violation
                violation = violations[0]
                body += '[%d:](%s) ```%s```\n' % (line, violation.url,
                                                violation.code)

                for violation in violations:
                    body += ' - [ ] %s\n' % violation.message

                body += '\n'

        return body

    def flush(self):
        """Creates a github comment with the errors found in the file"""
        body = self._get_comment_body()
        self.github.create_or_update_comment(self.COMMENT_HEADER, body)

def review_pull_request(repository, pull_request, pylintrc,
                        inline=False, **credentials):
    """Creates inline comments on the given pull request with the
    errors given by pylint"""
    github = GithubPullReviewClient(repository, pull_request, **credentials)

    files = [f.filename for f in github.get_files()]
    files = [f for f in files if f.endswith(".py")]

    handler = GithubInlineWriter(github) if inline else GithubCommentWriter(github)

    args = PYLINT_ARGS

    if pylintrc is not None:
        # Do not append to the existing constant
        args = args + ["--rcfile %s" % pylintrc]

    lint.Run(PYLINT_ARGS + files, reporter=TextReporter(handler), exit=False)
    handler.flush()

