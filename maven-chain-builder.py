#!/usr/bin/env python

from configobj import ConfigObj
import git
from glob import glob
import logging
import os
import random
import shutil
import string
import sys

# Constants
SEPARATORS = ['?', '#']
SPECIAL_OPTIONS = [ 'scmurl', 'patches','skipTests','buildrequires',
                    'jvm_options', 'maven_options', 'type' ]
RAND_DIR_NAME_LENGTH = 5


def clone_project(git_url, project, directory):
    """ Clone git repo """
    start_wd = os.getcwd()
    os.chdir(directory)
    logger.info('Changed dir: %s', directory)
    if not os.path.exists(project):
        logger.info('Cloning: %s', project)
        git.Git().clone(git_url)
    logger.info('Returning to: %s', start_wd)
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
    os.chdir(directory)
    logger.info('Changed dir: %s', directory)
    logger.info('Checking out the branch: %s', branch)
    (git.Git(project)).checkout(branch)
    logger.info('Returning to: %s', start_wd)
    os.chdir(start_wd)

def apply_patch(patch_dir, project, patch_repo_name):
    start_wd = os.getcwd()
    os.chdir(project)
    logger.info('Changed dir: %s', project)
    proj = git.Repo(project)
    logger.info('Looking for patches in %s', patch_dir)
    patches = glob(patch_dir + '/*.patch')
    logger.info('The patches are %s', patches)
    for p in patches:
        logger.info('Applying patch %s in %s', p, project)
        proj.git.execute(['git', 'am', '--ignore-space-change', p])
    shutil.rmtree('/tmp/' + patch_repo_name)
    logger.info('Returning to: %s', start_wd)
    os.chdir(start_wd)

def clone_patch(url, project_path):
    patch_url = get_git_url(url)
    patch_project_name = get_project_name(url)
    patch_branch = get_branch(url)
    subdir = get_subdir(url)
    patch_path = '/tmp/' + patch_project_name + '/' + subdir
    clone_project(patch_url, patch_project_name, '/tmp')
    logger.info('Checking out the branch: %s', patch_branch)
    checkout(patch_branch, patch_project_name, '/tmp')
    apply_patch(patch_path, project_path, patch_project_name)

def set_jvm_options(value):
    logger.info('Setting MAVEN_OPTS to: %s', value)
    os.environ["MAVEN_OPTS"] = value

def setup_logger(logger_name, logger_file):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(logger_file)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def build(project, build_cmd, subdir, logger_file):
    if subdir:
        build_path = project + '/' + subdir
    else:
        build_path = project
    start_wd = os.getcwd()
    os.chdir(build_path)
    logger.info('The build command is: %s', build_cmd)
    logger.info('Changed dir: %s', build_path)
    logger.info('Running build!')
    os.system(build_cmd + " >> {logFile} 2>&1".format(logFile=logger_file))
    os.chdir(start_wd)

def create_random_directory(start_path):
    rand_string = ''.join(random.choice(string.letters + string.digits) for _ in range(5))
    rand_dir = start_path + '/' + rand_string
    if not os.path.exists(rand_dir):
        os.makedirs(rand_dir)
        return rand_dir
    else: return ""

# ===== Main =====
if not os.path.exists('/var/log/maven'):
    os.makedirs('/var/log/maven')
root_logger = setup_logger('root','/var/log/maven/maven-chain-builder.log')

# Read config file
root_logger.info("Reading config file")
try:
    config = ConfigObj(sys.argv[1], list_values=False, _inspec=True)
except Exception as e:
    print "No config file present"
    sys.exit(2)

# Set globally git username and email
root_logger.info("Setting globally git username and user email")
os.system("git config --global user.name MavenBuild")
os.system("git config --global user.email MavenBuild@itsame.mario")

# Parse options
for section in config.sections:
    root_logger.info("Processing %s", section)
    logger_file = '/var/log/maven/maven-chain-' + section
    logger = setup_logger(section, logger_file)
    logger.info('====================== %s ====================', section)
    skip_build = False
    project_subdir=None
    build_cmd = "mvn deploy -B -q -DaltDeploymentRepository=tmp::default::file:///tmp "
    rand_dir = create_random_directory('/tmp')
    if section == 'DEFAULT':
        skip_build = True
    for option in config[section]:
        if option in SPECIAL_OPTIONS:
            if option == 'scmurl':
                project_name = get_project_name(config[section][option])
                logger.info('Project name: %s', project_name)
                branch = get_branch(config[section][option])
                git_url = get_git_url(config[section][option])
                project_path = rand_dir + '/' + project_name
                logger.info('Project path: %s', project_path)
                project_top_dir = rand_dir
                clone_project(git_url, project_name, project_top_dir)
                checkout(branch, project_name, project_top_dir)
                if '?' in config[section][option] :
                    project_subdir = get_subdir(config[section][option])
            if option == 'skipTests':
                build_cmd = build_cmd + "-DskipTests "
            if option == 'buildrequires':
                pass
            if option == 'type' and config[section][option] == 'wrapper':
               skip_build = True
            if option == 'maven_options':
                build_cmd = build_cmd + config[section][option] + " "
            if option == 'patches':
                clone_patch(config[section][option], project_path)
            if option == 'jvm_options':
                set_jvm_options(config[section][option])
        else:
            build_cmd = build_cmd + "-D{option}={value} ".format(option=option, value=config[section][option])
    if not skip_build:
        skip_build = False
        build(project_path, build_cmd, project_subdir, logger_file)
    shutil.rmtree(rand_dir)
