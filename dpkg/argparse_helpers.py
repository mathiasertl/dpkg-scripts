import argparse

build_parser = argparse.ArgumentParser(add_help=False)
build_parser.add_argument(
    '--keep-temp-dir', action='store_true', default=False,
    help="Do not delete temporary build directory after build.")
build_parser.add_argument(
    '--upload', action='store_true', default=False,
    help="Upload files to enceladus.htu.")
build_parser.add_argument(
    '--no-pristine', action='store_false', dest='pristine', default=True,
    help="Do not use pristine tars")
