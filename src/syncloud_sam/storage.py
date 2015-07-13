import convertible

import models


class Applications:

    def __init__(self, filename):
        self.filename = filename

    def list(self):
        apps_data = convertible.read_json(self.filename, models.Apps)
        if not apps_data:
            return []
        return apps_data.apps