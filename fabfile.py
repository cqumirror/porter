#!/usr/bin/env python

import os

from fabric.api import cd, run, put
from fabric.contrib.files import exists

PROJECT_NAME = "porter"
REPO_URL = "https://github.com/cqumirrors/porter.git"
# where to install the app
DST_HOST = "dev.mirrors.lanunion.org"
APP_ROOT = "/srv/apps"

APP_NAME = PROJECT_NAME     # normally project name equals to app name
APP_CFG = "confs_production/settings.py"
APP_DST = os.path.join(APP_ROOT, APP_NAME)


def git_clone_or_pull(repo_url):
    root = "/tmp/source-git"
    if not exists(root):
        run("mkdir -p {}".format(root))
    with cd(root):
        if not exists(PROJECT_NAME):
            run("git clone {}".format(repo_url))
        with cd(PROJECT_NAME):
            run("git pull")
    app_src = os.path.join(root, PROJECT_NAME)
    return app_src


def prepare_venv(app_src):
    requirements_txt = os.path.join(app_src, "requirements.txt")
    app_venv_name = "venv"

    run("mkdir -p {}".format(APP_DST))
    with cd(APP_DST):
        if not exists(app_venv_name):
            run("virtualenv {}".format(app_venv_name))
        # upgrade pip
        run("venv/bin/pip install --upgrade pip")
        # update requirements.txt and upgrade venv
        run("cp {} .".format(requirements_txt))
        # run("venv/bin/pip install --upgrade -r requirements.txt")
        run("venv/bin/pip install --upgrade tornado")


def put_config_files():
    put(APP_CFG, APP_DST)


def deploy():
    app_src = git_clone_or_pull(REPO_URL)
    prepare_venv(app_src)
    # update configurations
    put_config_files()
    # update app
    app_lib_old = os.path.join(APP_DST, "main.py")
    app_lib_new = os.path.join(app_src, "main.py")
    # remove old app lib
    run("rm -rf {}".format(app_lib_old))
    # copy new app lib to app dst
    run("cp -r {} {}".format(app_lib_new, APP_DST))


def start():
    with cd(APP_DST):
        run("venv/bin/python main.py &")


def all_in_one():
    deploy()
    # start()
