"""
Module that provides an API for Github Pull Request review comment
integration
"""
from github import Github

class GithubPullReviewClient(object):
    def __init__(self, repository, pull_request, **credentials):
        self.github = Github(**credentials)
        self.repo = self.github.get_repo(repository)
        self.pull_request = self.repo.get_pull(pull_request)

    def create_review_comment(self, code_context, filename, body):
        """Creates a comment on the latest commit that affected
        the line that matches code_context. This method will only
        comment added or existent code.
        :param code_context: line of code that should match
        :param filename: file modified
        :param body: string
        :rtype: github.PullRequestComment.PullRequestComment
        e.g.
        For
        foo.txt
        + some code here
        - some bad code
        self.create_review_comment("some code here", "foo.txt", "blah")
        will create a comment under "some code here"
        """
        for commit in self.pull_request.get_commits().reversed:
            filenames = [f.filename for f in commit.files]
            if filename not in filenames:
                continue

            file_index = filenames.index(filename)
            patch = commit.files[file_index].patch
            
            position = self._get_comment_position(patch, code_context)

            if position == -1:
                continue

            comment = self.pull_request.create_review_comment(body, commit, 
                                                              filename,
                                                              position)
            return comment
        return None

    def create_or_update_comment(self, comment_header, body):
        """Creates a comment or updates a pull request comment that
        begins with comment_header
        :param comment_header: header to match for the edited comment
        :param body: body of the new comment
        """

        for comment in self.pull_request.get_issue_comments():
            if comment.body.startswith(comment_header):
                comment.edit(body)
                break
        else:
            self.pull_request.create_issue_comment(body)

    def get_changed_files(self):
        """Returns the files added or chaned in the pull request"""
        filenames = set()
        for commit in self.pull_request.get_commits():
            files = commit.files
            changed = [f.filename for f in files if f.status != 'removed']
            removed = [f.filename for f in files if f.status == 'removed']
            filenames = filenames.union(changed).difference(removed)

        return list(filenames)

    def get_review_comments(self, code_context, filename):
        """Get the review comments that match the given code context
        :param code_context: string
        :param filename: string
        :rtype: github.PullRequestComment.PullRequestComment
        """
        return [c for c in self.pull_request.get_review_comments()
                if c.path == filename and
                self._get_comment_position(c.diff_hunk, code_context) != -1]

    def _get_comment_position(self, patch, code_context):
        """Return the position in the commit for the given code_context
        """
        patch_lines = patch.splitlines()
        for index, line in enumerate(patch_lines):
            # We want to remove any trailing characters that are used
            # for patching purposes

            # These are added lines
            line = line.lstrip("+")

            if line == code_context:
                # Comment will be below code_context
                return index

        return -1


