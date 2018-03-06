# Careful rm

A wrapper for rm that adds more useful warnings and an optional recycle/trash mode

Can be used as a drop-in replacement for `rm` on any Linux or MacOS system with
Python > 2.6. With no arguments or configuration, it will warn you if you
delete more than 3 files or any directories, and will print the files and
folders to delete to the console when prompting for approval (something `rm -I`
does not do).

All `rm` commands are implemented here. In addition, passing `-c` will result
in files being trashed/recycled instead of deleted. Applescript is used on
MacOS, otherwise the best trash location is chosen (see below). Most files can
be restored using GUI tools (e.g. Nautilus/Finder), as the default Trash
folders and metadata are used (e.g. *Put Back* works on Mac).

Ideally, this tool should be symlinked to `rm` and the file
`~/.rm_recycle_home` should be created, which will make recycling automatic
only for files in your home directory. This will provide a great deal of safety
without majorly messing up any sys-admin work.

## Usage

```
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
```

## Installation

To use this `rm` wrapper, the best way to go is to install the repo as a ZSH or
Bash plugin (see below). However, you can just put it into your `$PATH` and use
it directly. e.g.:

1. `cd /usr/local/bin`
2. `wget https://raw.githubusercontent.com/MikeDacre/careful_rm/master/careful_rm.py`

Ideally it should be *aliased to rm*. To facilitate that, you can use the
`careful_rm.alias.sh` file or just add this to your config (e.g. `.bashrc`):

    if hash careful_rm.py 2>/dev/null; then
        alias rm="$(command -v careful_rm.py)"
    else
        alias rm="rm -I"
    fi

### Requirements

- An `sh` style shell, preferably `zsh`, `fish`, or `bash`
- Python version 2.6+, no additional modules required

*It should work almost everywhere*

(**Note**: Windows maintainer wanted, it doesn't work there)

### General Install

With any `sh` like shell (`sh`, `bash`, `fish`, `zsh`)

1. `cd ~`
2. `git clone git@github.com:MikeDacre/careful_rm.git`
3. `echo "source ~/careful_rm/careful_rm.alias.sh" >> .bashrc`

### ZSH

ZSH offers some great ways to install as a plugin and stay up to date.

#### [Antigen](github.com/zsh-users/antigen)

If you're using [Antigen](github.com/zsh-users/antigen), just add
`antigen bundle MikeDacre/careful_rm` to your `.zshrc` file where you're
loading your other zsh plugins.

#### [Oh-My-Zsh](https://github.com/robbyrussell/oh-my-zsh)

1. `mkdir -p ~/oh-my-zsh/custom/plugins`
2. `cd ~/oh-my-zsh/custom/plugins`
3. `git clone git@github.com:MikeDacre/careful_rm.git`
4. add `plugins+=(careful_rm)` to the right place in your `~/.zshrc`

#### [Zgen](tarjoilija/zgen)

If you're using [Zgen](tarjoilija/zgen), add `zgen load MikeDacre/careful_rm` to your
`.zshrc` file where you're loading your other zsh plugins.

## Rationale and Implementation

`rm` is a powerful *nix tool that simply drops a file from the drive index. It
doesn't delete it or put it in a Trash can, it just de-indexes it which makes
the file hard to recover unless you want to put in the work, and pretty easy to
recover if you are willing to spend a few hours trying (use `shred` to actually
secure erase files).

`careful_rm.py` is inspired by the `-I` interactive mode of `rm` and by
[safe-rm](https://github.com/kaelzhang/shell-safe-rm). `safe-rm` adds a recycle
bin mode to rm, and the `-I` interactive mode adds a prompt if you delete more
than a handful of files or recursively delete a directory. `ZSH` also has an
option to warn you if you recursively rm a directory.

These are all great, but I found them unsatisfying. What I want is for rm to be
quick and not bother me for single file deletions (so `rm -i` is out), but to let
me know when I am deleting a lot of files, and *to actually print a list of files
that are about to be deleted*. I also want it to have the option to trash/recycle
my files instead of just straight deleting them.... like `safe-rm`, but not so
intrusive.

`careful_rm.py` is fundamentally a simple `rm` wrapper, that accepts all of the
same commands as `rm`, but with a few additional options features. In the source
code `CUTOFF` is set to **3**, so deleting more files than that will prompt the
user. Also, deleting a directory will prompt the user separately with a count of
all files and subdirectories within the folders to be deleted.

Furthermore, `careful_rm.py` implements a few fully integrated trash mode that
can be toggled on with `-c`. It can also be forced on by adding a file at
`~/.rm_recycle`, or toggled on only for `$HOME` (the best idea), by
`~/.rm_recycle_home`. The mode can be disabled on the fly by passing `--direct`,
which forces off recycle mode.

The recycle mode tries to find the best location to recycle to on MacOS or
Linux, on MacOS it also tries to use Apple Script to trash files, which means
the original location is preserved (note Applescript can be slow, you can
disable it by adding a `~/.no_apple_rm` file, but *Put Back* won't work). The
*best* location for trashes goes in this order:

1. `$HOME/.Trash` on Mac or `$HOME/.local/share/Trash` on Linux
2. `<mountpoint>/.Trashes` on Mac or `<mountpoint>/.Trash-$UID` on Linux
3. `/tmp/$USER_trash`

Always the best trash can to avoid Volume hopping is favored, as moving across
file systems is slow. If the trash does not exist, the user is prompted to
create it, they then also have the option to fall back to the root trash
(`/tmp/$USER_trash`) or just `rm` the files.

`/tmp/$USER_trash` is almost always used for deleting system/root files, but
**note** that you most likely do not want to save those files, and straight
`rm` is generally better.
