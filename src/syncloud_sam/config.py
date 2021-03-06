from ConfigParser import ConfigParser


class SamConfig:

    def __init__(self, filename):
        self.parser = ConfigParser()
        self.parser.read(filename)
        self.filename = filename

    def save(self):
        with open(self.filename, 'wb') as file:
            self.parser.write(file)

    def section(self, name):
        if not self.parser.has_section(name):
            self.parser.add_section(name)

    def __set_param(self, section, parameter, value):
        self.section(section)
        self.parser.set(section, parameter, value)
        self.save()

    def apps_dir(self):
        return self.parser.get('sam', 'apps_dir')

    def set_apps_dir(self, value):
        self.__set_param('sam', 'apps_dir', value)

    def status_dir(self):
        return self.parser.get('sam', 'status_dir')

    def set_status_dir(self, value):
        self.__set_param('sam', 'status_dir', value)

    def images_dir(self):
        return self.parser.get('sam', 'images_dir')

    def set_images_dir(self, value):
        self.__set_param('sam', 'images_dir', value)

    def temp_dir(self):
        return self.parser.get('sam', 'temp_dir')

    def set_temp_dir(self, value):
        self.__set_param('sam', 'temp_dir', value)

    def apps_url(self):
        return self.parser.get('sam', 'apps_url')

    def set_apps_url(self, value):
        self.__set_param('sam', 'apps_url', value)

    def releases_url(self):
        return self.parser.get('sam', 'releases_url')

    def set_releases_url(self, value):
        self.__set_param('sam', 'releases_url', value)

    def run_hook_path(self):
        return self.parser.get('sam', 'run_hook_path')

    def set_run_hook_path(self, value):
        self.__set_param('sam', 'run_hook_path', value)

    def arch(self):
        return self.parser.get('sam', 'arch')

    def set_arch(self, value):
        self.__set_param('sam', 'arch', value)
