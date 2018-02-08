#!/usr/bin/env python
# Copyright 2016 Arie Bregman
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ConfigParser
import git
from glob import glob
import logging
import os
import random
import shutil
import string
import sys
import time

# Constants
SEPARATORS = ['?', '#']
SPECIAL_OPTIONS = ['scmurl', 'patches', 'skipTests', 'buildrequires',
                   'jvm_options', 'maven_options', 'type',
                   'default_properties', 'properties']
IGNORE_OPTIONS = ['redhat_version', 'bom_version']
RAND_DIR_NAME_LENGTH = 5


def clone_project(git_url, project, directory, logger):
    """Clone git repo """
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


def get_commit(url):
    return (url.split('#')[1])


def get_git_url(url):
    for sep in SEPARATORS:
        if sep in url:
            url = url.split(sep)[0]
    if 'git+' in url:
        url = url.split('git+')[1]
    return url


def get_subdir(url):
    return (url.split('?')[1]).split('#')[0]


def checkout(commit, project, directory, logger):
    start_wd = os.getcwd()
    os.chdir(directory)
    logger.info('Changed dir: %s', directory)
    logger.info('Checking out the commit: %s', commit)
    (git.Git(project)).checkout(commit)
    logger.info('Returning to: %s', start_wd)
    os.chdir(start_wd)


def apply_patch(patch_dir, project, patch_repo_name, logger):
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
        git_log = proj.git.execute(['git', 'log', '-5', '--pretty'])
        logger.info('git log after applying patch: \n%s', git_log)

    shutil.rmtree('/tmp/' + patch_repo_name)
    logger.info('Returning to: %s', start_wd)
    os.chdir(start_wd)


def clone_patch(url, project_path, logger):
    patch_url = get_git_url(url)
    patch_project_name = get_project_name(url)
    patch_commit = get_commit(url)
    subdir = get_subdir(url)
    patch_path = '/tmp/' + patch_project_name + '/' + subdir
    clone_project(patch_url, patch_project_name, '/tmp', logger)
    logger.info('Checking out the commit: %s', patch_commit)
    checkout(patch_commit, patch_project_name, '/tmp', logger)
    apply_patch(patch_path, project_path, patch_project_name, logger)


def set_jvm_options(value, logger):
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


def build(project, build_cmd, subdir, logger_file, logger):
    if subdir:
        build_path = project + '/' + subdir
    else:
        build_path = project
    start_wd = os.getcwd()
    os.chdir(build_path)
    logger.info('The build command is: %s', build_cmd)
    logger.info('Changed dir: %s', build_path)
    logger.info('Running build!')
    exit_code = os.system(build_cmd + " >> {logFile} 2>&1".format(logFile=logger_file))
    if exit_code != 0:
        msg="ERROR: Building of %s failed, stopping building the chain" % project
        logger.info(msg)
	print(msg)
        sys.exit(2)
    
    os.chdir(start_wd)


def create_random_directory(start_path):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    rand_string = 'maven-chain-builder.' + timestamp + '.' + ''.join(
        random.choice(string.letters + string.digits) for _ in range(5))
    rand_dir = start_path + '/' + rand_string
    if not os.path.exists(rand_dir):
        os.makedirs(rand_dir)
        return rand_dir
    else:
        return ""


def replace_project(patched_project_path, original_project, logger):
    shutil.rmtree(original_project)
    logger.info('Removed the original project: {}'.format(original_project))
    shutil.copytree(patched_project_path, original_project)
    logger.info('Copied patched project to: {}'.format(patched_project_path))


def read_config(config_f):
    """Returns configuration."""
    try:
        config = ConfigParser.ConfigParser()
        config.read(config_f)
    except Exception as e:
        print(str(e))
        sys.exit(2)

    return config


def main():
    """Main program loop."""
    # Create logs dir and setup the main logger
    if not os.path.exists('/var/log/maven'):
        os.makedirs('/var/log/maven')
    root_logger = setup_logger(
        'root', '/var/log/maven/maven-chain-builder.log')

    root_logger.info("Reading config file {}".format(sys.argv[1]))
    config = read_config(sys.argv[1])

    # Set patched project name
    root_logger.info("Patched project is: {}".format(sys.argv[2]))
    patched_project_path = '/tmp/patched/' + sys.argv[2]

    # Set globally git username and email
    root_logger.info("Setting globally git username and user email")
    os.system("git config --global user.name MavenBuild")
    os.system("git config --global user.email MavenBuild@itsame.mario")

    # Parse chain file
    for section in config.sections():

        # Initialize section/build variables
        skip_build = False
        build_cmd = "mvn deploy -B -q -T 0.7C " + \
            "-DaltDeploymentRepository=tmp::default::file:///tmp "
        project_subdir = None
        rand_dir = create_random_directory('/tmp')

        # Handle section logging
        root_logger.info(
            "Processing section: %s. Creating new log file", section)
        logger_file = '/var/log/maven/maven-chain-' + section
        logger = setup_logger(section, logger_file)
        logger.info('====================== %s ====================', section)

        for option in config.options(section):
            if option in SPECIAL_OPTIONS:
                if option == 'scmurl':
                    project_name = get_project_name(
                        config.get(section, option))
                    commit = get_commit(config.get(section, option))
                    git_url = get_git_url(config.get(section, option))
                    project_path = rand_dir + '/' + project_name
                    project_top_dir = rand_dir
                    clone_project(
                        git_url, project_name, project_top_dir, logger)
                    checkout(commit, project_name, project_top_dir, logger)
                    if '?' in config.get(section, option):
                        project_subdir = get_subdir(
                            config.get(section, option))
                    if project_name == sys.argv[2]:
                        logger.info("Found match to the patched project name!.\
                                    Replacing the original: {}".format(
                                    project_name))
                        replace_project(patched_project_path, project_path, logger)
                    logger.info('Project name: %s', project_name)
                    logger.info('Project path: %s', project_path)
                if option == 'skipTests':
                    build_cmd = build_cmd + "-DskipTests "
                if option == 'buildrequires':
                    pass
                if option == 'type' and config.get(
                   section, option) == 'wrapper':
                    skip_build = True
                if option == 'maven_options':
                    build_cmd = build_cmd + config.get(section, option) + " "
                if option == 'patches':
                    clone_patch(
                        config.get(section, option), project_path, logger)
                if option == 'jvm_options':
                    set_jvm_options(config.get(section, option), logger)
                if option == 'properties':
                    logger.info("Detected properties")
                    properties = config.get(section, option)
                    options = [y for y in (
                        x.strip() for x in properties.splitlines()) if y]
                    for opt in options:
                        if opt == 'skipTests':
                            build_cmd = build_cmd + "-DskipTests "
                        else:
                            build_cmd = build_cmd + "-D{} ".format(opt)
            elif option not in IGNORE_OPTIONS:
                build_cmd = build_cmd + "-D{option}={value} ".format(option=option, value=config.get(section, option))

        # If the section is not 'DEFAULT', then build.
        if not skip_build:
            build(project_path, build_cmd, project_subdir, logger_file, logger)
            skip_build = False

        # Remove temp build dir
        shutil.rmtree(rand_dir)

if __name__ == '__main__':
    main()
