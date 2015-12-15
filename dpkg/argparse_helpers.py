import argparse

build_parser = argparse.ArgumentParser(add_help=False)
build_parser.add_argument(
    '--keep-temp-dir', action='store_true', default=False,
    help="Do not delete temporary build directory after build.")
build_parser.add_argument(
    '-u', '--upload', action='store_true', default=False,
    help="Upload files to enceladus.htu.")
build_parser.add_argument(
    '--no-pristine', action='store_false', dest='pristine', default=True,
    help="Do not use pristine tars")
build_parser.add_argument(
    '--upstream-tree', dest='upstream_tree', default='tag',
    choices=['tag', 'branch', ], metavar='[tag|branch]',
    help="Get upstream sources from tree or branch. Has no effect unless --no-pristine is used.")
build_parser.add_argument(
    '--upstream-branch', dest='upstream_branch', default='debian', metavar='branch',
    help="Branch to use when --git-usptream-tree is used. The default is 'debian'."
)
build_parser.add_argument('-s', '--sa', '--include-source', default=False, action='store_true',
                          help="Include original source even if Debian revision > 1.")
