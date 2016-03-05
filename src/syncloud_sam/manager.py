import os
import urllib
import tempfile
import tarfile
import shutil
import logging
import logging.handlers
from os.path import join, exists

from syncloud_app import logger
from syncloud_app import runner
from config import SamConfig
from models import AppVersions
from storage import Applications
from versions import Versions


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

    manager = Manager(config, applcations, repo_versions, installed_versions)

    return manager


class Manager:

    def __init__(self, config, applications, repo_versions, installed_versions):
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
                release = f.read().strip()
        else:
            raise Exception('The release is not set')
        return release

    def set_release(self, release):
        with open(self.release_filename, 'w+') as f:
            f.write(release)

    def upgrade(self, app_id):
        app_archive_filename, temp_dir = self.__download(app_id)
        self.remove(app_id)
        self.__install(app_archive_filename, temp_dir)

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
            shutil.rmtree(download_dir)

            self.set_release(release)

            return self.__upgradable_apps()

    def version(self, release, app_id):
        releases_url = self.config.releases_url()
        versions_url = join(releases_url, release, 'versions')
        download_dir = tempfile.mkdtemp()
        downloaded_versions = join(download_dir, 'versions')
        urllib.urlretrieve(versions_url, filename=downloaded_versions)
        versions = Versions(downloaded_versions)
        app_version = versions.version(app_id)
        return app_version


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
        self.run_hook(app_id, 'pre-remove', False)

        app_installed_path = join(self.config.apps_dir(), app_id)
        if exists(app_installed_path):
            shutil.rmtree(app_installed_path)

        self.installed_versions.remove(app_id)
        return "removed successfully"

    def install(self, app_id_or_filename):
        app_archive_filename, temp_dir = self.__download(app_id_or_filename)
        self.__install(app_archive_filename, temp_dir)

    def __install(self, app_archive_filename, temp_dir):
        try:
            self.install_file(app_archive_filename)
        finally:
            if temp_dir:
                self.logger.info("cleanup temp dir {0}".format(temp_dir))
                shutil.rmtree(temp_dir)

    def __download(self, app_id_or_filename):
        app_archive_filename = app_id_or_filename
        temp_dir = None
        if not exists(app_archive_filename):
            app_id = app_id_or_filename
            a = self.get_app(app_id, False)
            version = a.current_version

            download_dir = tempfile.mkdtemp()
            temp_dir = download_dir
            app_filename = '{}-{}-{}.tar.gz'.format(app_id, version, self.config.arch())
            app_url = join(self.config.apps_url(), app_filename)
            app_archive_filename = join(download_dir, app_filename)
            self.logger.info("downloading: {0}".format(app_url))
            urllib.urlretrieve(app_url, filename=app_archive_filename)
        return app_archive_filename, temp_dir

    def install_file(self, filename):
        unpack_dir = tempfile.mkdtemp()
        tarfile.open(filename).extractall(unpack_dir)
        unpack_app_folder = os.listdir(unpack_dir)[0]
        unpack_app_path = join(unpack_dir, unpack_app_folder)

        (app_id, version) = self.read_meta_app_version(unpack_app_path)

        app_installed_path = join(self.config.apps_dir(), app_id)
        if exists(app_installed_path):
            self.remove(app_id)
        shutil.copytree(join(unpack_dir, app_id), app_installed_path)
        shutil.rmtree(unpack_dir)
        self.run_hook(app_id, 'post-install')
        self.installed_versions.update(app_id, version)
        return "installed successfully"

    def read_meta_app_version(self, app_folder):
        app_id_path = join(app_folder, 'META', 'app')
        version_path = join(app_folder, 'META', 'version')
        app_id = open(app_id_path, 'r').read().strip()
        version = open(version_path, 'r').read().strip()
        return app_id, version

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

    def run_hook(self, app_id, action, throw_on_error=True):
        hook_script = join(self.config.apps_dir(), app_id, 'bin', action)
        if not os.path.isfile(hook_script):
            self.logger.info("{} hook is not found, skipping".format(hook_script))
            return

        if not runner.call(' '.join([self.config.run_hook_path(), hook_script]), self.logger, stdout_log_level=logging.INFO, shell=True) == 0:
            message = "unable to run {}".format(hook_script)
            if throw_on_error:
                raise Exception(message)
            else:
                self.logger.error(message)

    def release(self, source, target, override):
        overrides = dict((o.split('=')[0], o.split('=')[1]) for o in override)

        download_dir = tempfile.mkdtemp()
        index_path = join(download_dir, 'index')
        versions_path = join(download_dir, 'versions')

        releases_url = self.config.releases_url()

        index_source_url = join(releases_url, source, 'index')
        versions_source_url = join(releases_url, source, 'versions')

        urllib.urlretrieve(index_source_url, filename=index_path)
        urllib.urlretrieve(versions_source_url, filename=versions_path)

        versions = Versions(versions_path)
        for app, version in overrides.iteritems():
            versions.update(app, version)

        s3_releases_url = releases_url.replace('http:', 's3:')

        index_target_url = join(s3_releases_url, target, 'index')
        versions_target_url = join(s3_releases_url, target, 'versions')

        self.s3_upload(index_path, index_target_url)
        self.s3_upload(versions_path, versions_target_url)

    def s3_upload(self, filename, url):
        command = ' '.join(['s3cmd', 'put', filename, url])
        if not runner.call(command, self.logger, stdout_log_level=logging.INFO, shell=True) == 0:
            message = 'unable to execute "{}"'.format(command)
            raise Exception(message)