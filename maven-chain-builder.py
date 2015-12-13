#!/usr/bin/env python

import ConfigParser
import git
import os
import sys

# Constants
SEPARATORS = ['?', '#']

def clone_scm(scm_url):
    for sep in SEPARATORS:
        if sep in scm_url:
            git_url = scm_url.split(sep, 1)[0]
            break
    # Clone git repo
    if not os.path.exists((git_url.split('/')[-1]).split('.git')[0]):
        git.Git().clone(git_url)

# ===== Main =====
# Create ConfigParser instance
Config = ConfigParser.ConfigParser()

# Read config file
Config.read(sys.argv[1])

# Parse options
for section in Config.sections():
    options = Config.options(section)
    for option in options:
        if option == 'scmurl':
            clone_scm(Config.get(section, option))
