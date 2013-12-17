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

    def get_changed_files(self):
        """Returns the files added or chaned in the pull request"""
        filenames = set()
        for commit in self.pull_request.get_commits():
            files = commit.files
            changed = [f.filename for f in files if f.status != 'deleted']
            removed = [f.filename for f in files if f.status == 'deleted']
            filenames = filenames.union(changed).difference(removed)

        return filenames

    def get_review_comment(self, code_context, filename):
        """Get a Review Comment that matches the given code context
        :param code_context: string
        :param filename: string
        :rtype: github.PullRequestComment.PullRequestComment
        """
        for comment in self.pull_request.get_review_comment:
            if comment.path != filename:
                continue

            position = self._get_comment_position(comment.diff_hunk,
                                                  code_context)

            if position != -1:
                return comment

        return None

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
                return index + 1

        return -1


