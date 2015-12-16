#!/usr/bin/env python

from configobj import ConfigObj
import git
from glob import glob
import os
import shutil
import sys

# Constants
SEPARATORS = ['?', '#']
SPECIAL_OPTIONS = [ 'scmurl', 'patches','skipTests','buildrequires','jvm_options' ]

def clone_project(git_url, project, directory):
    """ Clone git repo """
    start_wd = os.getcwd()
    os.chdir(directory)
    if not os.path.exists(project):
        print "Cloning: {proj}".format(proj = project)
        git.Git().clone(git_url)
    os.chdir(start_wd)

def get_project_name(url):
    return (url.split('.git')[0]).split('/')[-1]

def get_branch(url):
    return (url.split('#')[1])

def get_git_url(url):
    for sep in SEPARATORS:
        if sep in url:
            url = url.split(sep)[0]
    return url

def get_subdir(url):
    return (url.split('?')[1]).split('#')[0]

def checkout(branch, project, directory):
    start_wd = os.getcwd()
    os.chdir('/home/' + sys.argv[2])
    (git.Git(project)).checkout(branch)
    os.chdir(start_wd)

def apply_patch(patch_dir, project, patch_repo_name):
    start_wd = os.getcwd()
    os.chdir(project)
    proj = git.Repo(project)
    patches = glob(patch_dir + '/*.patch')
    for p in patches:
        print('Arie is gay, and the patch is: {}'.format(p))
        proj.git.execute(['git', 'apply', p])
    shutil.rmtree('/tmp/' + patch_repo_name)
    os.chdir(start_wd)

def clone_patch(url, project_path):
    start_wd = os.getcwd()
    patch_url = get_git_url(url)
    patch_project_name = get_project_name(url)
    patch_branch = get_branch(url)
    subdir = get_subdir(url)
    patch_path = '/tmp/' + patch_project_name + '/' + subdir
    clone_project(patch_url, patch_project_name, '/tmp')
    print "Cloning patch: {patchProj}".format(patchProj = patch_project_name)
    checkout(patch_branch, patch_project_name, '/tmp')
    apply_patch(patch_path, project_path, patch_project_name)
    os.chdir(start_wd)

def set_jvm_options(value):
    os.environ["MAVEN_OPTS"] = value

def build(project, build_cmd, subdir):
    if subdir:
        build_path = project + '/' + subdir
    else:
        build_path = project
    start_wd = os.getcwd()
    os.chdir(build_path)
    print "The build command is: {buildCmd}".format(buildCmd=build_cmd)
    print "Entered {buildDir}".format(buildDir = build_path)
    print "Running build!"
    os.system(build_cmd)
    os.chdir(start_wd)

# ===== Main =====
# Read config file
config = ConfigObj(sys.argv[1], list_values=False, _inspec=True)

# Set bomversion if it exists in config file
if config['DEFAULT']['bomversion']:
    bomversion = config['DEFAULT']['bomversion']

# Parse options
for section in config.sections:
    print "----------------------------------"
    skip_build = False
    project_subdir=None
    build_cmd = "mvn deploy -DaltDeploymentRepository=tmp::default::file:///tmp"
    if section == 'DEFAULT':
        bomversion = config['DEFAULT']['bomversion']
        skip_build = True
    for option in config[section]:
        if option in SPECIAL_OPTIONS:
            if option == 'scmurl':
                project_name = get_project_name(config[section][option])
                print "Project name: {projName}".format( projName = project_name )
                branch = get_branch(config[section][option])
                print "Branch to checkout: {branch}".format( branch = branch )
                git_url = get_git_url(config[section][option])
                print "Cloning: {gitUrl}".format( gitUrl = git_url )
                project_path = '/home/' + sys.argv[2] + '/' + project_name
                project_top_dir = '/home/' + sys.argv[2]
                clone_project(git_url, project_name, project_top_dir)
                checkout(branch, project_name, project_path)
                if '?' in config[section][option] :
                    project_subdir = get_subdir(config[section][option])
            if option == 'skipTests':
                build_cmd = build_cmd + " -DskipTests"
            if option == 'buildrequires':
                pass
            if option == 'maven_options':
                build_cmd = build_cmd + config[section][option]
            if option == 'patches':
                clone_patch(config[section][option], project_path)
            if option == 'jvm_options':
                set_jvm_options(config[section][option])
        else:
            build_cmd = build_cmd + " -D{option}={value}".format(option=option, value=config[section][option])
    if not skip_build:
        skip_build = False
        build(project_path, build_cmd, project_subdir)
