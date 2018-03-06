#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""careful_rm, the safe rm wrapper

Will notify if more than a few (defined by CUTOFF) files are deleted, or if
directories are deleted recursively. Also, provides a recycle option, which
moves files to the trash can or to /var/$USER_trash.

Recyling can be forced on by the existence of ~/.rm_recycle, recycling only
the files below $HOME can be forced on with ~/.rm_recycle_home. *Generally
this is the best option for Linux, where recycling all files isn't a great
idea.

Passing -s or --shred will invoke shred on every file prior to removing them
and will disable recycle mode. Passing --direct will force disable recycle
mode without enabling shred.

Note: splits files, directories, and other non-files (e.g. sockets) and
handles them separately. non-files are always deleted with rm after checking
with the user.

Usage: careful_rm.py [-c] [-f | -i] [-dPRrvW] file ..

Arguments
---------
    -c, --recycle         move to trash instead of deleting (forced on by
                          ~/.rm_recycle)
    -s, --shred           run shred on all files (recursively if directories
                          included) prior to deleting, override recycle
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
import signal
import shlex as sh
from glob import glob
from getpass import getuser
from platform import system
from datetime import datetime as dt
from collections import defaultdict as dd
from subprocess import call, Popen, PIPE, CalledProcessError
try:
    from builtins import input
except ImportError:
    # For old versions of python 2
    input = raw_input

__version__ = '1.0b7'

# Don't ask if fewer than this number of files deleted
CUTOFF = 3
DOCSTR = '{0}\nWARNING CUTOFF: {1}\n'.format(__doc__, str(CUTOFF))

# Print on one line if fewer than this number
MAX_LINE = 2

# Where to move files to if recycled system-wide
RECYCLE_BIN = os.path.expandvars('/tmp/{0}_trash'.format(getuser()))


###############################################################################
#                   Compatability Functions for Python 2.6+                   #
###############################################################################


def quote(s):
    """Return a shell-escaped version of the string *s*."""
    if hasattr(sh, 'quote'):
        return sh.quote(s)
    if not s:
        return "''"

    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "'" + s.replace("'", "'\"'\"'") + "'"


def run(cmd, shell=False, check=False, get=True):
    """Replicate getstatusoutput from subprocess."""
    if not shell and isinstance(cmd, str):
        cmd = sh.split(cmd)
    if get:
        pp = Popen(cmd, shell=shell, stdout=PIPE, stderr=PIPE)
        out, err = pp.communicate()
    else:
        pp = Popen(cmd, shell=shell)
        pp.communicate()
    if not isinstance(out, str):
        out = out.decode()
    if not isinstance(err, str):
        err = err.decode()
    code = pp.returncode
    if check and code != 0:
        if get:
            sys.stderr.write(
                'Command failed\nSTDOUT:\n{0}\nSTDERR:\n{1}\n'
                .format(out, err)
            )
        raise CalledProcessError(code, cmd)
    if get:
        return code, out.rstrip(), err.rstrip()
    return code


def check_output(cmd, shell=False):
    """Return STDOUT for cmd."""
    _, stdout, _ = run(cmd, shell=shell, check=True, get=True)
    return stdout


###############################################################################
#               Constants the need the python compat functions                #
###############################################################################


# Home directory recycling
UID = os.getuid()
HOME = os.path.expanduser('~')
SYSTEM = system()
if SYSTEM == 'Darwin':
    HOME_TRASH = os.path.join(HOME, '.Trash')
    HAS_OSA = call('hash osascript 2>/dev/null', shell=True) == 0
    if HAS_OSA:
        OSA = check_output('command -pv osascript', shell=True).strip()
elif SYSTEM == 'Linux':
    HOME_TRASH = os.path.join(HOME, '.local/share/Trash')
else:
    HOME_TRASH = None

# Does the HOME trash exist?
HAS_HOME = os.path.isdir(HOME_TRASH)

# File shredding
if call('hash gshred 2>/dev/null', shell=True) == 0:
    SHRED = 'gshred'
elif call('hash shred 2>/dev/null', shell=True) == 0:
    SHRED = 'shred'
else:
    SHRED = None

# Linux trashinfo template
TRASHINFO = """\
[Trash Info]
Path={path}
DeletionDate={date}
"""
TIMEFMT = '%Y-%m-%dT%H:%M:%S'


###############################################################################
#                         Catch Keyboard Interruption                         #
###############################################################################

def catch_keyboard(sig, frame):
    """Catch Keyboard Interruption."""
    sys.stderr.write('\nKeyboard Interrupt Detected, Exiting\n')
    sys.exit(1)

signal.signal(signal.SIGINT, catch_keyboard)


###############################################################################
#                              Helper Functions                               #
###############################################################################


def get_ans(message, options, default=None):
    """Get an answer from user from list.

    Params
    ------
    messsage : str
        Message for user
    options : list
        Options to chose from
    default : str, optional
        Default option, must be in options

    Returns
    -------
    answer : str
    """
    if default:
        assert default in options
        default = default.lower()
    options = [i.lower() for i in options]
    str_options = []
    for opt in options:
        if opt == default:
            str_options.append(opt.upper())
        else:
            str_options.append(opt)

    message += ' [{0}] '.format('/'.join(str_options))
    while True:
        ans = input(message)
        if not isinstance(ans, str):
            ans = ans.decode()
        ans = ans.strip().lower()
        if ans:
            if ans in options:
                return ans
        elif default:
            return default
        sys.stderr.write('Invalid choice {0}, try again\n'.format(ans))


def yesno(message, def_yes=True):
    """Get a yes or no answer from the user."""
    ans = get_ans(message, ['y', 'n'], 'y' if def_yes else 'n')
    return ans == 'y'


def format_list(input_list):
    """Print a list as columns matched to the terminal width.

    From: stackoverflow.com/questions/25026556
    """
    try:
        term_width = int(check_output(['tput', 'cols']).strip())
    except (CalledProcessError, OSError, ValueError):
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


def get_mount(fl):
    """Return the mountpoint for fl."""
    test_path = fl
    while test_path:
        if os.path.ismount(test_path) or test_path == '/':
            return test_path
        test_path = os.path.dirname(test_path)
    return '/'


def get_trash(fl=None):
    """Return the trash can for the file/dir fl."""
    # Default trash locations
    v_trash_mac = os.path.join('.Trashes', str(UID))
    v_trash_lin = '.Trash-{0}'.format(UID)
    v_trash = v_trash_mac if SYSTEM == 'Darwin' else v_trash_lin

    # Get absolute path to location of interest
    if not fl:
        if sys.argv and len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
            fl = sys.argv[1]
        else:
            fl = os.path.curdir
    fl = os.path.abspath(fl)

    mnt = get_mount(fl)
    if mnt == '/':
        if HAS_HOME and fl.startswith(HOME):
            trash = HOME_TRASH
        else:
            trash = RECYCLE_BIN
    elif mnt == HOME:
        trash = HOME_TRASH
    else:
        trash = os.path.join(mnt, v_trash)

    return trash

###############################################################################
#                              Deletion Helpers                               #
###############################################################################


def recycle_files(files, mv_flags, try_apple=True, verbose=False, dryrun=False):
    """Identify best recycle bins for files and then try to recycle them.

    Params
    ------
    files : list of str
        Files, directories, or something else to recycle
    mv_flags : list of str
        Flags to pass to mv
    try_apple : bool, optional
        Try to use apple script, only means anything on Darwin, default True.
    verbose : bool, optional
        Print extra info
    dryrun : bool
        Don't actually move anything

    Returns
    -------
    list
        List of failed files, empty on success
    """
    # Get the longest path first, so we can pick the best mountpoints
    # We need absolute paths for recycling
    files = sorted(
        [os.path.abspath(i) for i in files],
        key=lambda x: len(x), reverse=True
    )

    # Try applescript first on MacOS
    if try_apple and SYSTEM == 'Darwin' and HAS_OSA:
        if verbose:
            sys.stderr.write('Attempting to use applescript\n')
        new_fls = []
        if dryrun:
            sys.stderr.write(
                'Moving {0} to Trash with Finder via Applescript\n'
                .format(files)
            )
            return []
        for fl in files:
            if recycle_darwin(fl, verbose=verbose) != 0:
                new_fls.append(fl)
        if new_fls:
            sys.stderr.write(
                'Applescript failed on:\n{0}\n'.format(format_list(new_fls))
            )
            files = new_fls
        else:
            return []

    # Get a mount point for all files
    bins = dd(list)
    gotn = tuple()
    for fl in files:
        # Load the ones we have found already quickly
        if fl.startswith(gotn):
            for d in gotn:
                if fl.startswith(d):
                    bins[d].append(fl)
                    break
        else:
            mnt = get_mount(fl)
            bins[mnt].append(fl)
            gotn += (mnt,)

    # Build final list of recycle bins
    trashes = {}
    to_delete = []
    for mount, file_list in bins.items():
        r_trash = get_trash(mount)
        if os.path.isdir(r_trash):
            trashes[r_trash] = file_list
        else:
            ans = get_ans(
                ('Mount {0} has no trash at {1}.\n' +
                 'Skip, create, use (root) {2}, or delete files?')
                .format(mount, r_trash, RECYCLE_BIN),
                ['skip', 'create', 'root', 'del']
            )
            if ans == 'create':
                os.makedirs(r_trash)
                if SYSTEM == 'Linux':
                    for f in ['expunged', 'files', 'info']:
                        os.makedirs(os.path.join(r_trash, f))
                trashes[r_trash] = file_list
            elif ans == 'root':
                if RECYCLE_BIN not in trashes:
                    trashes[RECYCLE_BIN] = []
                trashes[RECYCLE_BIN] += file_list
            elif ans == 'del':
                to_delete += file_list
            elif ans == 'skip':
                # Just don't add the files to the trashes dict
                pass
            else:
                raise Exception('Invalid response {0}'.format(ans))

    # Do the deed, one file at a time (for metadata)
    for trash, file_list in trashes.items():
        for fl in file_list:
            if dryrun:
                sys.stderr.write('Moving {0} to {1}\n'.format(fl, trash))
            if not dryrun and recycle_file(fl, trash, mv_flags) != 0:
                to_delete.append(fl)

    # Check if user wants to try to force delete files
    if to_delete:
        sys.stderr.write(
            'Failed to recycle:\n{0}\n'.format(format_list(to_delete))
        )
        if yesno('Attempt to fully delete with rm?', False):
            return to_delete

    return []


def recycle_file(fl, trash, mv_flags=None):
    """Move one file to trash, do kung-foo on Linux.

    If on Linux, file moved to trash/files unless trash==RECYCLE_BIN. Will
    also create a trashinfo file. If not Linux, file just moved to trash
    directly.

    Params
    -------
    fl : str
    trash : str
    mv_flags : list of str
        Flags to pass to mv

    Returns
    -------
    exit_code : int
        0 on success, something else on failure
    """
    if mv_flags:
        mv_flags = ' '.join(mv_flags)
    else:
        mv_flags = ""

    if trash == RECYCLE_BIN or SYSTEM != 'Linux':
        return call(
            sh.split('mv {0} -- {1} {2}'.format(
                mv_flags, quote(fl), quote(trash)
            ))
        )
    trash_can = os.path.join(trash, 'files')
    err = call(
        sh.split('mv {0} -- {1} {2}'.format(
            mv_flags, quote(fl), quote(trash_can)
        ))
    )
    if err == 0:
        now = dt.now()
        info_file = os.path.join(
            trash, 'info', os.path.basename(fl) + '.trashinfo'
        )
        with open(info_file, 'w') as trash_info:
            trash_info.write(
                TRASHINFO.format(path=fl, date=now.strftime(TIMEFMT))
            )
    return err


def recycle_darwin(fl, verbose=False):
    """Move fl (file or dir) to trash on MacOS using applescript.

    Returns
    -------
    exit_code : int
        0 on success, something else on failure
    """
    cmnd = (
        '{0} -e '
        '"tell application \\"Finder\\" to delete POSIX file \\"{1}\\"" '
        '>/dev/null 2>/dev/null'
    ).format(OSA, os.path.abspath(fl))
    if verbose:
        sys.stderr.write(cmnd + '\n')
    return call(cmnd, shell=True)



def shred_files(sfls, shred_args, verbose=False, dryrun=False):
    """Call shred on sfls."""
    cmd = '{0} {1} -- {2}'.format(
        SHRED, ' '.join(shred_args),
        ' '.join([quote(i) for i in sfls])
    )
    if dryrun or verbose:
        sys.stderr.write('Running: {0}\n'.format(cmd))
    if not dryrun:
        return call(sh.split(cmd))
    return 0


###############################################################################
#                         Core Function—Run As Script                         #
###############################################################################


def main(argv=None):
    """The careful rm function."""
    if not argv:
        argv = sys.argv
    sys.argv = None
    if not argv:
        sys.stderr.write(
            'Arguments required\n\n' + DOCSTR
        )
        return 99
    file_sep = '--'  # Used to separate files from args, change to '' if needed
    flags = []
    rec_args = []
    shred_args = ['-z']
    all_files = []
    shred      = False  # Shred (destroy) files prior to deletion
    dryrun     = False  # Don't do anything, just print commands
    verbose    = False  # Print extra info
    recursive  = False  # Delete stuff in directories
    no_recycle = False  # Force off recycling
    recycle    = os.path.isfile(os.path.join(HOME, '.rm_recycle'))
    recycle_hm = os.path.isfile(os.path.join(HOME, '.rm_recycle_home'))
    for arg in argv[1:]:
        if arg == '-h' or arg == '--help':
            sys.stderr.write(DOCSTR)
            return 0
        elif arg == '-c' or arg == '--recycle':
            recycle = True
        elif arg == '--direct':
            no_recycle = True
        elif arg == '-s' or arg == '--shred':
            shred = True
        elif arg == '--dryrun':
            dryrun = True
            sys.stderr.write('Dry Run. Not actually removing files.\n\n')
        elif arg == '--get-trash':
            # Print trash for next arg and immediately exit
            tindex = argv.index(arg)+1
            tpath = argv[tindex] if len(argv) > tindex else os.curdir
            sys.stdout.write(get_trash(tpath))
            return 0
        elif arg == '--':
            # Everything after this is a file
            file_sep = '--'
            all_files += [
                i for l in [glob(n) for n in argv[argv.index(arg):]] \
                for i in l
            ]
            break
        elif arg == '-':
            # Read files in from STDIN
            all_files += [
                i for l in \
                [glob(n) for n in sys.stdin.read().strip().split()] \
                for i in l
            ]
        elif arg.startswith('-'):
            if 'r' in arg or 'R' in arg:
                recursive = True
            if 'c' in arg:
                arg = arg.replace('c', '')
                recycle = True
            if 's' in arg:
                arg = arg.replace('s', '')
                shred = True
            if 'f' in arg:
                rec_args.append('-f')
                shred_args.append('-f')
            if 'i' in arg:
                rec_args.append('-i')
            if 'v' in arg:
                verbose = True
                rec_args.append('-v')
                shred_args.append('-v')
            flags.append(quote(arg))
        else:
            all_files += glob(arg)
    if shred and (recycle or recycle_hm):
        sys.stderr.write('Recycle disabled because shred is in use\n')
        recycle = False
        recycle_hm = False
        no_recycle = True
    if no_recycle and (recycle or recycle_hm):
        sys.stderr.write('Recycle foreced off\n')
        recycle = False
        recycle_hm = False

    if shred:
        if not SHRED:
            sys.stderr.write(
                'Cannot use shred as neither shred nor gshred '
                'are in your path\n'
            )
            return 4
        sys.stderr.write('All files will be destroyed with shred\n')
    if verbose:
        if recycle:
            sys.stderr.write('Using recycle instead of remove\n\n')
        elif shred:
            sys.stderr.write('Using shred+remove instead of recycle\n\n')
        else:
            sys.stderr.write('Using remove instead of recycle\n\n')
    drs = []
    fls = []
    bad = []
    oth = []
    for fl in all_files:
        if os.path.isdir(fl):
            drs.append(fl)
        elif os.path.isfile(fl) or os.path.islink(fl):
            fls.append(fl)
        # Anything else, even broken symlinks
        elif os.path.lexists(fl):
            oth.append(fl)
        # Should not happen as glob would reject
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
            'Have {0} dirs, {1} files/links, {2} other, and {3} non-existent\n'
            .format(ld, len(fls), len(oth), len(bad))
        )

    # Directory handling
    if drs and not recursive:
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
        ans = get_ans(
            '\nAdd -r, ignore dirs, or cancel?', ['add', 'ignore', 'cancel'],
            default='cancel'
        )
        if ans == 'add':
            flags.append('-r')
            recursive = True
        elif ans == 'ignore':
            drs = []
        elif ans == 'cancel':
            return 2
        else:
            raise Exception('Invalid response {0}'.format(ans))
        sys.stderr.write('\n')

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
            info = []
            if dc or fc:
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
                    msg += '\nThey contain ' + inf
                else:
                    msg += '\nThey contain no subfiles or directories'
            sys.stderr.write(msg + '\n')
            if not yesno('Really delete?', False):
                return 1
            sys.stderr.write('\n')

    # File handling
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
        sys.stderr.write('\n')

    # Build final lists
    to_delete = drs + fls
    to_recycle = []
    if recycle:
        to_recycle = to_delete
        to_delete  = []
    elif recycle_hm:
        for fl in to_delete:
            if os.path.abspath(fl).startswith(HOME):
                to_recycle.append(fl)
                to_delete.remove(fl)
    if verbose:
        sys.stderr.write(
            'Have {0} items to delete and {1} item to recycle\n\n'
            .format(len(to_delete)+len(oth), len(to_recycle))
        )
    if not to_delete and not oth and not to_recycle:
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
        sys.stderr.write('\n')

    # Shred here
    if shred:
        failed = []
        if drs:
            if verbose:
                sys.stderr.write(
                    'Recursively shredding files in the following dirs:\n{0}\n'
                    .format(format_list(drs))
                )
            for dr in drs:
                for wroot, wdirs, wfiles in os.walk(dr):
                    if verbose:
                        sys.stderr.write('Shredding in {0}\n'.format(wroot))
                    if wfiles:
                        sfls = [os.path.join(wroot, i) for i in wfiles]
                        if shred_files(sfls, shred_args, verbose, dryrun) != 0:
                            failed.append(os.path.join(dr, wroot))
                    elif verbose:
                        sys.stderr.write('No files to shred\n')
        if fls:
            if shred_files(fls, shred_args, verbose, dryrun) != 0:
                failed += fls
        if failed:
            sys.stderr.write(
                'shred FAILED on the following files and dirs:\n{0}\n\n'.format(
                    format_list(failed)
                )
            )
            msg = 'Continue with deletion anyway (data may not be scrubbed)?'
            if not yesno(msg, False):
                return 13
            sys.stderr.write('\n')

    # Recycle here
    if to_recycle:
        if not os.path.isdir(RECYCLE_BIN):
            os.makedirs(RECYCLE_BIN)
        try_apple = SYSTEM == 'Darwin' and not \
            os.path.isfile(os.path.join(HOME, '.no_apple_rm'))
        to_delete += recycle_files(
            to_recycle, mv_flags=rec_args, try_apple=try_apple,
            verbose=verbose, dryrun=dryrun
        )

    # And finally.... the rm wrapper itself, attempts to quote and isolate
    # file names to increase the number of things we could delete (e.g. files
    # that start with '-' or contain '@', '*', or '~'
    if to_delete:
        cmnd = 'rm {0} {1} {2}'.format(
            ' '.join(flags), file_sep,
            ' '.join([quote(i) for i in to_delete])
        )

        if dryrun or verbose:
            if verbose:
                sys.stderr.write('Actually running rm\n')
            sys.stdout.write('Running: {0}\n'.format(cmnd))
            if dryrun:
                return 0

        return call(sh.split(cmnd))

    return 0


# The End
if __name__ == '__main__' and '__file__' in globals():
    sys.exit(main())
