#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""careful_rm, the safe rm wrapper

Will notify if more than a few (defined by CUTOFF) files are deleted, or if
directories are deleted recursively. Also, provides a recycle option, which
moves files to the trash can or to /var/$USER_trash.

Recyling can be forced on by the existence of ~/.rm_recycle

Usage: careful_rm.py [-c] [-f | -i] [-dPRrvW] file ..

Arguments
---------
    -c, --recycle         move to trash instead of deleting (forced on by
                          ~/.rm_recycle)
        --direct          force off recycling, even if ~/.rm_recycle exists
        --dryrun          do not actually remove or move files, just print
    -h, --help            display this help and exit

Arguments Passed to rm
----------------------
    -f, --force           ignore nonexistent files and arguments, never prompt
    -i                    prompt before every removal
    -I                    prompt once before removing more than three files, or
                          when removing recursively
    -r, -R, --recursive   remove directories and their contents recursively
    -d, --dir             remove empty directories
    -v, --verbose         explain what is being done

For full help for rm, see `man rm`, note that only the '-i', '-f' and '-v'
options have any meaning in recycle mode, which uses `mv`. Argument order does
not matter.

This tool should ideally be aliased to rm, add this to your bashrc/zshrc:

    if hash careful_rm.py 2>/dev/null; then
        alias rm="$(command -v careful_rm.py)"
    else
        alias rm="rm -I"
    fi
"""
import os
import sys
import shlex as sh
from glob import glob
from getpass import getuser
from platform import system
from subprocess import call, check_output, CalledProcessError
try:
    from builtins import input
except ImportError:
    input = raw_input

__version__ = '1.0b1'

# Don't ask if fewer than this number of files deleted
CUTOFF = 3
DOCSTR = '{0}\nWARNING CUTOFF: {1}\n'.format(__doc__, str(CUTOFF))

# Print on one line if fewer than this number
MAX_LINE = 5

# Where to move files to if recycled system-wide
RECYCLE_BIN = os.path.expandvars('/tmp/{0}_trash'.format(getuser()))

# Home directory recycling
HOME = os.path.expanduser('~')
SYSTEM = system()
if SYSTEM == 'Darwin':
    HOME_TRASH = os.path.join(HOME, '.Trash')
elif SYSTEM == 'Linux':
    HOME_TRASH = os.path.join(HOME, '.local/share/Trash')
else:
    HOME_TRASH = RECYCLE_BIN
if os.path.isdir(HOME_TRASH):
    HAS_HOME = True
else:
    HAS_HOME = False
    HOME_TRASH = RECYCLE_BIN


def yesno(message, def_yes=True):
    """Get a yes or no answer from the user."""
    message += ' [Y/n] ' if def_yes else ' [y/N] '
    ans = input(message)
    if ans:
        return ans.lower() == 'y' or ans.lower() == 'yes'
    return def_yes


def format_list(input_list):
    """Print a list as columns matched to the terminal width.

    From: stackoverflow.com/questions/25026556
    """
    try:
        term_width = int(check_output(['tput', 'cols']).decode().strip())
    except (CalledProcessError, FileNotFoundError, ValueError):
        term_width = 80

    if len(str(input_list)) < term_width:
        return str(input_list).strip('[]')

    repr_list = [repr(x) for x in input_list]
    min_chars_between = 3 # a comma and two spaces
    usable_term_width = term_width - 2
    min_element_width = min(len(x) for x in repr_list) + min_chars_between
    max_element_width = max(len(x) for x in repr_list) + min_chars_between
    if max_element_width >= usable_term_width:
        ncol = 1
        col_widths = [1]
    else:
        # Start with max possible number of columns and reduce until it fits
        ncol = int(min(len(repr_list), usable_term_width/min_element_width))
        while True:
            col_widths = [
                max(
                    len(x) + min_chars_between \
                    for j, x in enumerate(repr_list) if j % ncol == i
                ) for i in range(ncol)
            ]
            if sum( col_widths ) <= usable_term_width:
                break
            else:
                ncol -= 1

    outstr = ""
    for i, x in enumerate(repr_list):
        if i != len(repr_list)-1:
            x += ','
        outstr += x.ljust(col_widths[ i % ncol ])
        if i == len(repr_list) - 1:
            outstr += '\n'
        elif (i+1) % ncol == 0:
            outstr += '\n'

    return outstr


def main(argv=None):
    """The careful rm function."""
    if not argv:
        argv = sys.argv
    if not argv:
        sys.stderr.write(
            'Arguments required\n\n' + DOCSTR
        )
        return 99
    file_sep = '--'  # Used to separate files from args, change to '' if needed
    flags = []
    rec_args = []
    all_files = []
    dryrun     = False
    recycle    = False
    verbose    = False
    recursive  = False
    no_recycle = False
    for arg in argv[1:]:
        if arg == '-h' or arg == '--help':
            sys.stderr.write(DOCSTR)
            return 0
        elif arg == '--recycle' or arg == '-c':
            recycle = True
        elif arg == '--direct':
            recycle = False
            no_recycle = True
        elif arg == '--dryrun':
            dryrun = True
            sys.stderr.write('Not actually removing files.\n')
        elif arg == '--':
            # Everything after this is a file
            file_sep = '--'
            all_files += [
                sh.quote(i) for l in [glob(n) for n in argv[argv.index(arg):]] \
                for i in l
            ]
            break
        elif arg.startswith('-'):
            if 'r' in arg or 'R' in arg:
                recursive = True
            if 'f' in arg:
                rec_args.append('-f')
            if 'i' in arg:
                rec_args.append('-i')
            if 'v' in arg:
                verbose = True
                rec_args.append('-v')
            flags.append(sh.quote(arg))
        else:
            all_files += [sh.quote(i) for i in glob(arg)]
    if os.path.isfile(os.path.join(HOME, '.rm_recycle')):
        recycle = True
    if no_recycle:
        recycle = False
    if verbose:
        if recycle:
            sys.stderr.write('Using recycle instead of remove\n')
        else:
            sys.stderr.write('Using remove instead of recycle\n')
    drs = []
    fls = []
    bad = []
    oth = []
    for fl in all_files:
        if os.path.isdir(fl):
            drs.append(fl)
        elif os.path.isfile(fl):
            fls.append(fl)
        # Anything else, even broken symlinks
        elif os.path.lexists(fl):
            oth.append(fl)
        else:
            bad.append(fl)
    if bad:
        sys.stderr.write(
            'The following files do not match any files\n{0}\n'
            .format(' '.join(bad))
        )
    ld = len(drs)
    if verbose:
        sys.stderr.write(
            'Have {0} dirs, {1} files, {2} other, and {3} non-existent\n'
            .format(ld, len(fls), len(oth), len(bad))
        )
    if recursive:
        if drs:
            dc = 0
            fc = 0
            for dr in drs:
                for i in [os.path.join(dr, d) for d in os.listdir(dr)]:
                    if os.path.isdir(i):
                        dc += 1
                    else:
                        fc += 1
            if dc or fc:
                info = []
                if fc:
                    info.append('{0} subfiles'.format(fc))
                if dc:
                    info.append('{0} subfolders'.format(dc))
            inf = ' and '.join(info)
            msg = 'Recursively deleting '
            if ld < MAX_LINE:
                msg += 'the folders {0}'.format(drs)
                if info:
                    msg += ' with ' + inf
            else:
                msg += '{0} dirs:'.format(ld)
                msg += '\n{0}\n'.format(format_list(drs))
                if info:
                    msg += 'Containing ' + inf
                else:
                    msg += 'Containing no subfiles or directories'
            sys.stderr.write(msg + '\n')
            if not yesno('Really delete?', False):
                return 1
    elif drs:
        if ld < MAX_LINE:
            sys.stderr.write(
                'Directories {0} included but -r not sent\n'
                .format(drs)
            )
        else:
            sys.stderr.write(
                '{0} directories included but -r not sent\n'
                .format(len(drs))
            )
        if not yesno('Continue anyway?'):
            return 2
        drs = []
    if len(fls) >= CUTOFF:
        if len(fls) < MAX_LINE:
            if not yesno('Delete the files {0}?'.format(fls), False):
                return 6
        else:
            sys.stderr.write(
                'Deleting the following {0} files:\n{1}\n'
                .format(len(fls), format_list(fls))
            )
            if not yesno('Delete?', False):
                return 10

    to_delete = drs + fls
    to_delete = ['"' + i + '"' for i in to_delete]
    if verbose:
        sys.stderr.write(
            'Have {0} items to delete\n'.format(len(to_delete)+len(oth))
        )
    if not to_delete and not oth:
        sys.stderr.write('No files or folders to delete\n')
        return 22
    # Handle non-files separately
    if oth:
        sys.stderr.write(
            'The following files cannot be recycled and will be deleted:\n'
        )
        if yesno('Delete?', False):
            if call(sh.split('rm -- {0}'.format(' '.join(oth)))) == 0:
                sys.stderr.write('Done\n')
            else:
                sys.stderr.write('Delete failed!\n')
                return 1
        if not to_delete:
            return 0
    if recycle:
        if not os.path.isdir(RECYCLE_BIN):
            os.makedirs(RECYCLE_BIN)
        # Default to /tmp, use home if Mac OS or if Linux and in the HOME
        # directory (all paths must be inside home, usually true)
        rec_bin = RECYCLE_BIN
        if HAS_HOME:
            if SYSTEM == 'Darwin':
                rec_bin = HOME_TRASH
            else:
                home_count = 0
                for fl in drs + fls:
                    if os.path.abspath(fl).startswith(HOME):
                        home_count += 1
                if home_count == len(to_delete):
                    rec_bin = HOME_TRASH
        cmnd = 'mv {0} {1} {2} "{3}"'.format(
            ' '.join(rec_args), file_sep, ' '.join(to_delete), rec_bin
        )
        if not dryrun:
            sys.stderr.write(
                'All files will be recycled to {0}\n'.format(rec_bin)
            )
    else:
        cmnd = 'rm {0} {1} {2}'.format(
            ' '.join(flags), file_sep, ' '.join(to_delete)
        )
    if dryrun or verbose:
        sys.stdout.write('Command: {0}\n'.format(cmnd))
        if dryrun:
            return 0
    return call(sh.split(cmnd))


if __name__ == '__main__' and '__file__' in globals():
    sys.exit(main())
