import os
import urllib
import tempfile
import zipfile
import shutil
import stat
import logging
import logging.handlers
from os.path import join
from syncloud.app import logger
from syncloud.app import runner

from config import SamConfig
from models import AppVersions
from storage import Applications, Versions

def get_sam(config_path):

    config = SamConfig(join(config_path, 'sam.cfg'), ROOT_DIR='')

    apps_dir = config.apps_dir()
    status_dir = config.status_dir()

    app_index_filename = os.path.join(apps_dir, 'index')
    repo_versions_filename = os.path.join(apps_dir, 'versions')

    installed_versions_filename = os.path.join(status_dir, 'installed.apps')

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
        self.release_filename = os.path.join(self.config.status_dir(), 'release')

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
            apps_url_template = self.config.apps_url_template()
            apps_url = apps_url_template.format(release)

            extract_dir = tempfile.mkdtemp()
            archive_filename = os.path.join(extract_dir, 'archive.zip')

            self.logger.info("loading: {0}".format(apps_url))
            urllib.urlretrieve(apps_url, filename=archive_filename)

            extract_to_dir = os.path.join(extract_dir, 'unzipped')

            z = zipfile.ZipFile(archive_filename, 'r')
            z.extractall(extract_to_dir)

            subdirs = [name for name in os.listdir(extract_to_dir) if os.path.isdir(os.path.join(extract_to_dir, name))]

            extracted_apps_dir = os.path.join(extract_to_dir, subdirs[0])

            for filename in [name for name in os.listdir(extracted_apps_dir) if os.path.isfile(os.path.join(extracted_apps_dir, name))]:
                full_filename = os.path.join(extracted_apps_dir, filename)
                st = os.stat(full_filename)
                os.chmod(full_filename, st.st_mode | stat.S_IEXEC)

            shutil.rmtree(self.apps_dir, ignore_errors=True)
            shutil.copytree(extracted_apps_dir, self.apps_dir)

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

    def reconfigure_installed_apps(self):
        self.logger.info("reconfigure installed apps")
        installed_apps = [a for a in self.list() if a.installed_version]
        for application in installed_apps:
            self.run_hook(application.app, 'reconfigure')

    def list(self):
        apps = self.applications.list()
        return [self.get_app_versions(app) for app in apps]

    def remove(self, app_id):
        a = self.get_app(app_id, True)
        app = a.app
        self.run_hook(app, 'pre-remove')
        self.pip.uninstall(app.id)
        self.installed_versions.remove(app.id)
        return "removed successfully"

    def install(self, app_id):
        a = self.get_app(app_id, False)
        app = a.app
        self.pip.install(app.id, a.current_version)
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

        hook_bin = os.path.join(self.config.apps_dir(), app.id, action)
        if not os.path.isfile(hook_bin):
            self.logger.info("{} hook is not found, skipping".format(hook_bin))
            return

        if not runner.call(hook_bin, self.logger, stdout_log_level=logging.INFO, shell=True) == 0:
            raise Exception("unable to run {}".format(hook_bin))