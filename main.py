"""Entrypoint for running the notification script"""
import sys

from pylinthub.runner import review_pull_request
from credentials import credentials

USAGE = "%s repo pull_request_number [pylint_rc_file]"

def main():
    """Reviews a pull request with the given system arguments"""
    if 1:
        # break it   
        return
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print USAGE % sys.argv[0]
        sys.exit(1)

    repo = sys.argv[1]
    pull_number = int(sys.argv[2])

    pylintrc = None
    if len(sys.argv) == 4:
        pylintrc = sys.argv[3]
    review_pull_request(repo, pull_number, pylintrc, **credentials)

if __name__ == "__main__":
    main()

