#!/usr/bin/env python

from configobj import ConfigObj
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
#Config = ConfigParser.ConfigParser()

# Read config file
config = ConfigObj(sys.argv[1])
#Config.read(sys.argv[1])

# Set bomversion if it exists in config file
if config['DEFAULT']['bomversion']:
    bomversion = config['DEFAULT']['bomversion']

# Parse options
for section in config.sections:
    build_cmd = "mvn deploy -DaltDeploymentRepository=tmp::default::file:///tmp"
    if section == 'DEFAULT':
        bomversion = config['DEFAULT']['bomversion']
    for option in config[section]:
        if option == 'scmurl':
#           clone_scm(Config.get(section, option))
            print "Cloning"
        if option == 'dependencyManagement':
            build_cmd = build_cmd + " -DdependencyManagement={depManage}".format(depManage=config[section][option])
        if option == 'groovyScripts':
            build_cmd = build_cmd + " -DgroovyScripts={groovy}".format(groovy=config[section][option])
        if option == 'pluginManagement':
            build_cmd = build_cmd + " -DpluginManagement={plugManage}".format(plugManage=config[section][option])
        if option == 'checkstyle.skip':
            build_cmd = build_cmd + " -Dcheckstyle.skip={chkStyleSkip}".format(chkStyleSkip=config[section][option])
        if option == 'maven.javadoc.skip':
            build_cmd = build_cmd + " -Dmaven.javadoc.skip={javadocSkip}".format(javadocSkip=config[section][option])
        if option == 'version.suffix':
            build_cmd = build_cmd + " -Dversion.suffix={verSuffix}".format(verSuffix=config[section][option])

    with open("build.sh", "a") as build_file:
        build_file.write(build_cmd + "\n")
    print build_cmd
