import os
import urllib
import tempfile
import zipfile
import tarfile
import shutil
import stat
import logging
import logging.handlers
from os.path import join, exists
from syncloud.app import logger
from syncloud.app import runner

from config import SamConfig
from models import AppVersions
from storage import Applications, Versions

def get_sam(sam_home):

    config = SamConfig(join(sam_home, 'config', 'sam.cfg'))

    apps_dir = config.apps_dir()
    status_dir = config.status_dir()

    app_index_filename = join(apps_dir, 'index')
    repo_versions_filename = join(apps_dir, 'versions')

    installed_versions_filename = join(status_dir, 'installed.apps')

    installed_versions = Versions(installed_versions_filename)
    repo_versions = Versions(repo_versions_filename, allow_latest=True)
    applcations = Applications(app_index_filename)

    manager = Manager(None, config, applcations, repo_versions, installed_versions)

    return manager


class Manager:

    def __init__(self, pip, config, applications, repo_versions, installed_versions):
        self.pip = pip

        self.config = config
        self.apps_dir = config.apps_dir()

        self.applications = applications
        self.repo_versions = repo_versions
        self.installed_versions = installed_versions
        self.logger = logger.get_logger('sam.manager')
        self.release_filename = join(self.config.status_dir(), 'release')

    def get_release(self):
        if os.path.isfile(self.release_filename):
            with open(self.release_filename, 'r') as f:
                release = f.read()
        else:
            raise Exception('The release is not set')
        return release

    def set_release(self, release):
        with open(self.release_filename, 'w+') as f:
            f.write(release)

    def update(self, release=None):
        self.logger.info("update")

        if not release:
            release = self.get_release()

        if release:
            releases_url = self.config.releases_url()
            download_dir = tempfile.mkdtemp()

            index_url = join(releases_url, release, 'index')
            downloaded_index = join(download_dir, 'index')

            self.logger.info("loading: {0}".format(index_url))
            urllib.urlretrieve(index_url, filename=downloaded_index)

            versions_url = join(releases_url, release, 'versions')
            downloaded_versions = join(download_dir, 'versions')

            self.logger.info("loading: {0}".format(versions_url))
            urllib.urlretrieve(versions_url, filename=downloaded_versions)

            sam_index = join(self.config.apps_dir(), 'index')
            shutil.copyfile(downloaded_index, sam_index)

            sam_versions = join(self.config.apps_dir(), 'versions')
            shutil.copyfile(downloaded_versions, sam_versions)

            self.set_release(release)

            return self.__upgradable_apps()

    def newer_available(self, application):
        if application.installed_version:
            return application.current_version != application.installed_version
        else:
            return application.app.required

    def __upgradable_apps(self):
        return [a for a in self.list() if self.newer_available(a)]

    def upgrade_all(self):
        self.logger.info("upgrade all")
        for application in self.__upgradable_apps():
            self.install(application.app.id)

    def list(self):
        apps = self.applications.list()
        return [self.get_app_versions(app) for app in apps]

    def remove(self, app_id):
        a = self.get_app(app_id, True)
        app = a.app
        self.run_hook(app, 'pre-remove')

        app_installed_path = join(self.config.apps_dir(), app.id)
        if exists(app_installed_path):
            shutil.rmtree(app_installed_path)

        self.installed_versions.remove(app.id)
        return "removed successfully"

    def install(self, app_id):
        a = self.get_app(app_id, False)
        app = a.app

        download_dir = tempfile.mkdtemp()
        app_filename = '{}-{}-{}.tar.gz'.format(app.id, a.current_version, 'x86_64')
        app_url = join(self.config.apps_url(), app_filename)
        downloaded_filename = join(download_dir, app_filename)
        urllib.urlretrieve(app_url, filename=downloaded_filename)
        app_installed_path = join(self.config.apps_dir(), app.id)
        if exists(app_installed_path):
            shutil.rmtree(app_installed_path)
        tarfile.open(downloaded_filename).extractall(self.config.apps_dir())

        self.run_hook(app, 'post-install')
        self.installed_versions.update(app.id, a.current_version)
        return "installed successfully"

    def get_app_versions(self, app):
        latest_version = self.repo_versions.version(app.id)
        installed_version = self.installed_versions.version(app.id)
        self.logger.info('{0}: installed: {1} (latest: {2})'.format(app.id, installed_version, latest_version))
        return AppVersions(app, latest_version, installed_version)

    def get_app(self, app_id, installed=False):
        found = next((a for a in self.list() if a.app.id == app_id), None)

        if not found:
            raise Exception("no such app: {}".format(app_id))

        if not (found.installed_version is not None) == installed:
            if installed:
                raise Exception('{} should be installed but it is not'.format(app_id))
            # else:
            #     raise Exception('{} should not be installed but it is'.format(app_id))

        return found

    def run_hook(self, app, action):

        hook_bin = join(self.config.apps_dir(), app.id, action)
        if not os.path.isfile(hook_bin):
            self.logger.info("{} hook is not found, skipping".format(hook_bin))
            return

        if not runner.call(hook_bin, self.logger, stdout_log_level=logging.INFO, shell=True) == 0:
            raise Exception("unable to run {}".format(hook_bin))