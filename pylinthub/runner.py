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
        code = linecache.getline(path, int(line)).rstrip('\r\n')
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
    USAGE = ("To check before pushing, run on your build environment: "
             "```pylint -r -n --rcfile $RCFILE $FILE```\n")

    def __init__(self, github):
        super(GithubCommentWriter, self).__init__(github)
        self.violations = {}
        self.file_urls = {}
        self.candidates = set()
        self._add_candidate_lines()
        self._add_file_urls()

    def _add_candidate_lines(self):
        """Creates a cache with the code lines that are candidates for
        errors in the pull request."""
        for changed_file in self.github.get_files():
            # Some patches are empty (eg adding __init__.py)
            if not changed_file.patch:
                continue
            for line in changed_file.patch.splitlines():
                # Comment only on additions
                if not line.startswith('+'):
                    continue
                line = line.lstrip('+')
                self.candidates.add(line)

    def _add_file_urls(self):
        """Populate file_urls member with Pull Request version url for
        the changed files"""
        for changed_file in self.github.get_files():
            self.file_urls[changed_file.filename] = changed_file.blob_url

    def _get_file_url(self, path, line=None):
        """Returns the github url for the file at path at the Pull Request
        version"""
        if line:
            return '%s#L%s' % (self.file_urls[path], line)
        else:
            return self.file_urls[path]

    def handle_pylint_error(self, path, line, code, message):
        """Appends errors to local structures"""

        # We don't want to receive verbose messages with errors that weren't
        #added in the current pull request
        if code not in self.candidates:
            return

        file_violations = self.violations.get(path, [])

        url = self._get_file_url(path, line)

        file_violations.append(Violation(path, url, int(line), code, message))
        self.violations[path] = file_violations

    def _get_comment_body(self):
        """Formats a comment body."""
        body = self.COMMENT_HEADER + '\n'

        if len(self.violations) == 0:
            body += "No Errors! Congrats!\n"

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

                # add a trailing space for the cases when the line is
                # empty and the comment results in ``````.
                code = violation.code + " "
                body += '[%d:](%s) ```%s```\n' % (line, violation.url, code)

                for violation in violations:
                    body += ' - [ ] %s\n' % violation.message

                body += '\n'

        if len(self.violations):
            violation_count = sum([len(v) for v in self.violations.values()])
            total_loc = len(self.candidates)
            body += 'Having __%d__ violations with __%.2f__ violations/line\n' % (
                    violation_count, float(violation_count) / total_loc)

        body += self.USAGE

        body += "Last commit is %s\n" % self.github.pull_request.head.sha
        return body

    def flush(self):
        """Creates a github comment with the errors found in the file"""
        body = self._get_comment_body()
        self.github.create_or_update_comment(self.COMMENT_HEADER, body)

def review_pull_request(repository, pull_request, pylintrc, assignees=None,
                        inline=False, **credentials):
    """Creates inline comments on the given pull request with the
    errors given by pylint"""
    github = GithubPullReviewClient(repository, pull_request, **credentials)

    if assignees and github.get_assignee_name() not in assignees:
        return

    files = [f.filename for f in github.get_files()]
    files = [f for f in files if f.endswith(".py")]

    handler = GithubInlineWriter(github) if inline else GithubCommentWriter(github)

    args = PYLINT_ARGS

    if pylintrc is not None:
        # Do not append to the existing constant
        args = args + ["--rcfile %s" % pylintrc]

    if not files:
        return

    lint.Run(args + files, reporter=TextReporter(handler), exit=False)
    handler.flush()

