#!/usr/bin/env python3

import os
import datetime
import logging, traceback
log = logging.getLogger('uws')

from AirImport import importer, converter

def main(data_dir, basedir, use_git = False):
    # Fail early if git is needed
    if use_git:
        from git import Repo

    def s(n):
        return '0' * (2 - len(str(n))) + str(n)
    date = datetime.datetime.now()
    end_date = '{}-{}'.format(s(date.month), s(date.year))
    dirs = [os.path.join(s(date.year), s(date.month))]
    start_date = end_date
    # Download previous month as well on the first day of the month
    if date.day == 1:
        td = datetime.timedelta(days = 1)
        start_date = date - td
        dirs.append(os.path.join(s(start_date.year), s(start_date.month)))
        start_date = '{}-{}'.format(s(start_date.month), s(start_date.year))
    # Set taregt dirs
    (raw_dir, out_dir) = (
        os.path.join(data_dir, 'raw'), os.path.join(data_dir, 'joint'))
    
    # Download data from Umwelt Sachsen
    importer.main(date = start_date, end_date = end_date,
        out_dir = raw_dir, basedir = basedir)    
    # Convert data to joint csv
    for dir in dirs:
        converter.main(data_dir = os.path.join(raw_dir, dir),
            out_dir = os.path.join(out_dir, dir), basedir = basedir)
    # Automatically commit and push
    if use_git:
        for d in ('raw', 'joint'):
            repo = Repo(data_dir)
            index = repo.index
            index.add([os.path.join(d, dir) for dir in dirs])
            index.commit('Updated {} data for {}'.format(d,
                date.strftime('%Y-%m-%d %H:%M')))
            repo.remotes.origin.push()

if __name__ == '__main__':
    from logging import StreamHandler
    import sys
    stdout_logger = StreamHandler(sys.stdout)
    stderr_logger = StreamHandler(sys.stderr)
    log.addHandler(stdout_logger)
    log.addHandler(stderr_logger)
    stdout_logger.setLevel(logging.WARNING)
    stderr_logger.setLevel(logging.ERROR)

    from optparse import OptionParser
    class OptParser(OptionParser):
        def format_epilog(self, formatter):
            return self.epilog

    parser = OptParser(epilog = """
This script is meant to be run regularly in order to generate and push data
automatically to the repository.
""")

    parser.add_option(
        "-d", "--data-dir",
        dest = "data_dir",
        help = u"Directory that contains all data."
    )

    parser.add_option(
        "-b", "--base-dir",
        dest = "basedir",
        default = os.getcwd(),
        help = u"No files outside of this directory may be accessed."
    )

    parser.add_option(
        "-g", "--git",
        action = 'store_true',
        dest = "use_git",
        default = False,
        help = u"No files outside of this directory may be accessed."
    )
 
 
    (options, arguments) = parser.parse_args()

    if not options.data_dir:
        parser.error('Call with --data-dir')

    main(data_dir = options.data_dir, basedir = options.basedir,
        use_git = options.use_git)
