"""Installation instructions for careful_rm."""
import os
from setuptools import setup

import careful_rm  # For version

VERSION=careful_rm.__version__
GITHUB='https://github.com/MikeDacre/careful_rm'

REQUIREMENTS = []


def read(fname):
    """Read the contents of a file in this dir."""
    with open(os.path.join(os.path.dirname(__file__), fname)) as fin:
        return fin.read()


# Actual setup instructions
setup(
    name         = "careful_rm",
    version      = VERSION,
    author       = "Mike Dacre",
    author_email = "mike.dacre@gmail.com",
    description  = (
        "A safe wrapper for rm that adds useful warnings and an "
        "optional recycle/trash mode"
    ),
    keywords = (
        "zsh coreutils rm bash shell wrapper trash-mode macos macosx "
        "linux command-line oh-my-zsh antigen alternative"
    ),
    long_description = read('README.rst'),
    license = "MIT",

    # URLs
    url = GITHUB,
    download_url='{0}/archive/v{1}.tar.gz'.format(GITHUB, VERSION),

    # Actual packages/modules
    # Packages are directories with __init__.py files
    # Modules are python scripts (minus the .py)
    #  packages=["careful_rm"],
    py_modules=['careful_rm'],

    # Entry points and scripts
    # Entry points are functions that can use sys.argv (e.g. main())
    # Scripts are independent pieces of code intended to be executed as is
    entry_points = {
        'console_scripts': [
            'careful_rm = careful_rm:main',
            'rm_trash = careful_rm:get_trash',
        ],
    },
    #  scripts = [],

    # Data files
    #  data_files = [],

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
    ],

    # Requirements
    requires=REQUIREMENTS,
    install_requires=REQUIREMENTS,
    #  tests_require=[],
)
