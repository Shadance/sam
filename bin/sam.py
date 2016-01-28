#!/usr/bin/env python
import logging
from os.path import join, dirname, normpath, isdir, abspath
from os import listdir
import sys
import argparse

app_path = abspath(join(dirname(__file__), '..'))
sys.path.append(join(app_path, 'src'))

lib_path = join(app_path, 'lib')
libs = [join(lib_path, item) for item in listdir(lib_path) if isdir(join(lib_path, item))]
map(lambda x: sys.path.insert(0, x), libs)

from syncloud_app import main
from syncloud_app import logger
from syncloud_sam.manager import get_sam


def get_arg_parser():
    parser = argparse.ArgumentParser(description='Syncloud application manager')
    parser.add_argument('--debug', action='store_true')

    subparsers = parser.add_subparsers(help='available commands', dest='action')

    subparsers.add_parser('list', help="list apps")

    sub = subparsers.add_parser('install', help="install application")
    sub.add_argument('app_id_or_filename', help="application id or application archive file")

    sub = subparsers.add_parser('remove', help="remove application")
    sub.add_argument('app_id', help="application id")

    sub = subparsers.add_parser('update', help="update apps repository")
    sub.add_argument('--release', default=None, dest='release')

    sub = subparsers.add_parser('upgrade', help="upgrade an app")
    sub.add_argument('app_id', help="application id")

    sub = subparsers.add_parser('release', help="make/update release")
    sub.add_argument('source', help="existing release to copy from")
    sub.add_argument('target', help="release that will be created/updated")
    sub.add_argument('--override', nargs='*', help='apps versions overrides in format: <app>=<version>', default=[])


    #TODO: Not sure why do we need this
    subparsers.add_parser('upgrade_all', help="upgrade apps and install required apps")


    return parser

if __name__ == '__main__':
    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()

    console = True if args.debug else False
    level = logging.DEBUG if args.debug else logging.INFO
    logger.init(level, console, '/var/log/sam.log')

    sam_home = normpath(join(dirname(__file__), '..'))

    sam = get_sam(sam_home)

    main.execute(sam, args)