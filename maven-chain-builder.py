#!/usr/bin/env python

import ConfigParser
import git
import sys

def clone_scm(scm_url):
    git.Git().clone(scm_url)

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
