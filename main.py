"""Entrypoint for running the notification script"""
import sys

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from pylinthub.runner import review_pull_request
from credentials import credentials

USAGE = "%s repo pull_request_number [pylint_rc_file]"

def get_arguments():
    """Adds commandline arguments"""
    arg_parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('-r', '--repo',
            nargs = 1,
            required = True,
            type = str,
            help = 'Repository of the Pull Request')

    arg_parser.add_argument('-n', '--pull_number',
            nargs=1,
            required=True,
            type=int,
            help='Pull Request number')

    arg_parser.add_argument('-rc', '--rcfile',
            nargs = 1,
            required = False,
            type = str,
            help = 'Pylint rc file')

    arg_parser.add_argument('-a', '--assignees',
            nargs = '+',
            required = False,
            type = str,
            help = ('Pull Request assignees for which the script is ran. '
                    'If not set the script will run for any assignee'))



    return arg_parser.parse_args(sys.argv[1:])

def main():
    """Reviews a pull request with the given system arguments"""
    args = vars(get_arguments())

    pull_number = args['pull_number'][0]
    repo = args['repo'][0]
    pylintrc = args['rcfile'][0] if args['rcfile'] else None
    assignees = args['assignees']

    review_pull_request(repo, pull_number, pylintrc, assignees, **credentials)

if __name__ == "__main__":
    main()

