import sys

from pylinthub.runner import review_pull_request
from credentials import credentials

USAGE = "%s repo pull_request_number"

def main():
    if len(sys.argv) != 3:
        print USAGE % sys.argv[0]
        sys.exit(1)

    repo = sys.argv[1]
    pull_number = int(sys.argv[2])

    review_pull_request(repo, pull_number, **credentials)

if __name__ == "__main__":
    main()

