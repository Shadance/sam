import logging

from os.path import dirname, join, isdir, isfile
from os import makedirs, remove

import shutil
import tempfile
import pytest
from syncloud_app import logger

import sys, os
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(join(myPath, '../..')))

print(sys.path)

from syncloud_sam.manager import get_sam
from syncloud_sam.config import SamConfig

from subprocess import check_output
import tarfile

test_dir = dirname(__file__)
logger.init(logging.DEBUG, console=True)

test_temp_dir = '/tmp/sam-tests'

def temp_dir():
    if not isdir(test_temp_dir):
        makedirs(test_temp_dir)
    return tempfile.mkdtemp(dir=test_temp_dir)

def text_file(path, filename, text=''):
    app_path = join(path, filename)
    if not isdir(path):
        makedirs(path)
    if isfile(app_path):
        remove(app_path)
    f = open(app_path, 'w')
    f.write(text)
    f.close()
    return app_path

def get_text(path):
    with open(path, 'r') as f:
        return f.read()

def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

def create_app_version(name, version, architecture, pre_remove=None, post_install=None):
    temp_folder = temp_dir()
    app_folder = join(temp_folder, name)
    app_bin_folder = join(app_folder, 'bin')
    makedirs(app_bin_folder)

    app_script_content='''#!/bin/sh
echo "{}"'''.format(version)
    app_path = text_file(app_bin_folder, name, app_script_content)
    os.chmod(app_path, 0744)

    if pre_remove:
        text_file(app_folder, 'pre-remove', pre_remove)

    if post_install:
        text_file(app_folder, 'post_install', post_install)

    app_meta_folder = join(app_folder, 'META')
    makedirs(app_meta_folder)
    text_file(app_meta_folder, 'app', name)
    text_file(app_meta_folder, 'version', version)

    app_archive = '{}-{}-{}.tar.gz'.format(name, version, architecture)
    app_archive_path = join(temp_folder, app_archive)

    make_tarfile(app_archive_path, app_folder)

    return app_archive_path


def create_release(release, index, versions=None):
    prepare_dir_root = temp_dir()
    prepare_dir = join(prepare_dir_root, 'app-' + release)
    os.makedirs(prepare_dir)

    text_file(prepare_dir, 'index', index)
    if versions:
        text_file(prepare_dir, 'versions', versions)

    archive = shutil.make_archive(release, 'zip', prepare_dir_root)

    return archive


def assert_single_application(applications, id, name, current_version, installed_version):
    assert applications is not None
    assert len(applications) == 1

    test_app = applications[0]
    assert test_app.app.id == id
    assert test_app.app.name == name
    assert test_app.current_version == current_version
    assert test_app.installed_version == installed_version


def one_app_index(required=False, icon=None):
    if icon is None:
        icon_filename = ''
    else:
        icon_filename = ', "icon": "%s"' % icon

    app_index_template = '''{
      "apps" : [
        {
          "name" : "test app",
          "id" : "test-app",
          "type": "admin",
          "required": %s
          %s
        }
      ]
    }'''
    return app_index_template % (str(required).lower(), icon_filename)


class BaseTest:
    def setup(self):
        self.home_dir = temp_dir()
        config_dir = join(self.home_dir, 'config')
        os.makedirs(config_dir)
        self.apps_dir = temp_dir()
        status_dir = temp_dir()
        self.apps_url_dir = temp_dir()
        self.releases_url_dir = temp_dir()
        self.images_url_dir = temp_dir()
        self.images_dir = temp_dir()

        apps_url = 'file://'+self.apps_url_dir
        releases_url = 'file://'+self.releases_url_dir

        self.config = SamConfig(join(config_dir, 'sam.cfg'))
        self.config.set_apps_dir(self.apps_dir)
        self.config.set_status_dir(status_dir)
        self.config.set_apps_url(apps_url)
        self.config.set_releases_url(releases_url)
        self.config.set_temp_dir('/tmp/sam')
        self.config.set_arch('x86_64')
        self.config.set_images_dir(self.images_dir)

        self.run_hook_tool_dir = temp_dir()
        run_hook_content='#!/bin/sh\necho "run_hook executed"'
        run_hook_tool_path = text_file(self.run_hook_tool_dir, "run_hook", run_hook_content)
        self.config.set_run_hook_path(run_hook_tool_path)

        self.sam = get_sam(self.home_dir)

    def create_release(self, release, index, versions=None):
        release_dir = join(self.releases_url_dir, release)
        if os.path.exists(release_dir):
            shutil.rmtree(release_dir)
        os.makedirs(release_dir)

        text_file(release_dir, 'index', index)
        if versions:
            text_file(release_dir, 'versions', versions)

    def create_app_version(self, name, version, pre_remove=None, post_install=None):
        app_path = create_app_version(name, version, 'x86_64', pre_remove, post_install)
        shutil.copy(app_path, self.apps_url_dir)


class TestBasic(BaseTest):

    def test_list(self):
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')
        self.sam.update('release-1.0')
        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0', None)

    def test_install(self):
        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')

        self.sam.update('release-1.0')
        self.sam.install('test-app')

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0', '1.0')

        test_app_path = join(self.apps_dir, 'test-app', 'bin', 'test-app')
        output = check_output(test_app_path, shell=True)
        assert output.strip() == '1.0'

    def test_upgrade(self):
        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')

        self.sam.update('release-1.0')
        self.sam.install('test-app')

        self.create_app_version('test-app', '1.1')
        self.create_release('release-1.1', one_app_index(), 'test-app=1.1')
        self.sam.update('release-1.1')

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.1', '1.0')

        self.sam.install('test-app')

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.1', '1.1')

        test_app_path = join(self.apps_dir, 'test-app', 'bin', 'test-app')
        output = check_output(test_app_path, shell=True)
        assert output.strip() == '1.1'

    def test_remove(self):
        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')

        self.sam.update('release-1.0')
        self.sam.install('test-app')

        self.sam.remove('test-app')

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0', None)


class TestUpdates(BaseTest):

    def test_update_simple(self):
        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')

        self.sam.update('release-1.0')

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0', None)

    def test_update_same_release(self):
        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')

        self.sam.update('release-1.0')

        self.create_app_version('test-app', '1.0.1')
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0.1')

        self.sam.update()

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0.1', None)

    def test_update_new_release(self):
        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')

        self.sam.update('release-1.0')

        self.create_app_version('test-app', '1.1')
        self.create_release('release-1.1', one_app_index(), 'test-app=1.1')

        self.sam.update('release-1.1')

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.1', None)

    def test_update_bootstrap_no_apps_dir(self):
        self.config.set_apps_dir(join(self.config.apps_dir(), 'non_existent'))

        sam = get_sam(self.home_dir)

        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')
        sam.update('release-1.0')

        applications = sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0', None)

    def test_update_download_icon_new(self):
        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(icon='test-app.png'), 'test-app=1.0')

        release_images_url_dir = join(self.releases_url_dir, 'release-1.0', 'images')

        text_file(release_images_url_dir, 'test-app.png', 'Image content')
        text_file(release_images_url_dir, 'test-app.png.md5', 'Image md5 sum')

        self.sam.update('release-1.0')

        icon_path = join(self.config.images_dir(), 'test-app.png')
        icon_md5_path = join(self.config.images_dir(), 'test-app.png.md5')

        assert isfile(icon_path)
        assert isfile(icon_md5_path)

    def test_update_download_icon_no_md5_changes(self):
        image_before_update = 'Image content'

        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(icon='test-app.png'), 'test-app=1.0')

        release_images_url_dir = join(self.releases_url_dir, 'release-1.0', 'images')

        text_file(release_images_url_dir, 'test-app.png', image_before_update)
        text_file(release_images_url_dir, 'test-app.png.md5', 'Image md5 sum')

        self.sam.update('release-1.0')

        image_after_update = 'Image content UPDATED but md5 was not changed'

        text_file(release_images_url_dir, 'test-app.png', image_after_update)

        self.sam.update('release-1.0')

        actual_image = get_text(join(self.config.images_dir(), 'test-app.png'))

        assert actual_image == image_before_update

    def test_update_download_icon_md5_changes(self):
        image_before_update = 'Image content'

        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(icon='test-app.png'), 'test-app=1.0')

        release_images_url_dir = join(self.releases_url_dir, 'release-1.0', 'images')

        text_file(release_images_url_dir, 'test-app.png', image_before_update)
        text_file(release_images_url_dir, 'test-app.png.md5', 'Image md5 sum')

        self.sam.update('release-1.0')

        image_after_update = 'Image content UPDATED'
        image_md5_after_update = 'Image md5 sum UPDATED'

        text_file(release_images_url_dir, 'test-app.png', image_after_update)
        text_file(release_images_url_dir, 'test-app.png.md5', image_md5_after_update)

        self.sam.update('release-1.0')

        actual_image = get_text(join(self.config.images_dir(), 'test-app.png'))

        assert actual_image == image_after_update


class TestUpgradeAll(BaseTest):

    def test_update_usual_app(self):
        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')
        self.sam.update('release-1.0')
        self.sam.install('test-app')

        self.create_app_version('test-app', '1.1')
        self.create_release('release-1.1', one_app_index(), 'test-app=1.1')
        self.sam.update('release-1.1')
        self.sam.upgrade_all()

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.1', '1.1')

    def test_update_required_app(self):
        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(required=True), 'test-app=1.0')

        self.sam.update('release-1.0')
        self.sam.upgrade_all()

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0', '1.0')


class TestHooks(BaseTest):

    def test_remove_hook_good(self):
        pre_remove_content = '#!/bin/sh\nexit 0'

        self.create_app_version('test-app', '1.0', pre_remove=pre_remove_content)
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')

        self.sam.update('release-1.0')

        self.sam.install('test-app')

        self.sam.remove('test-app')

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0', None)

    def test_remove_hook_missing(self):
        self.create_app_version('test-app', '1.0')
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')
        self.sam.update('release-1.0')

        self.sam.install('test-app')

        self.sam.remove('test-app')

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0', None)

    def _test_remove_hook_bad(self):
        pre_remove_content = '#!/bin/sh\nexit 1'

        self.create_app_version('test-app', '1.0', pre_remove=pre_remove_content)
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')

        self.sam.update('release-1.0')

        self.sam.install('test-app')

        try:
            self.sam.remove('test-app')
            assert False
        except Exception, e:
            assert True

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0', '1.0')

    def _test_install_hook_bad(self):
        post_install_content = '#!/bin/sh\nexit 1'

        self.create_app_version('test-app', '1.0', post_install=post_install_content)
        self.create_release('release-1.0', one_app_index(), 'test-app=1.0')

        self.sam.update('release-1.0')

        try:
            self.sam.install('test-app')
            assert False
        except Exception, e:
            assert True

        applications = self.sam.list()
        assert_single_application(applications, 'test-app', 'test app', '1.0', None)
