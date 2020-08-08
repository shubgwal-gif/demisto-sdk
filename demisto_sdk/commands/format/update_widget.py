from typing import Tuple

from demisto_sdk.commands.common.tools import LOG_COLORS, print_color
from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class WidgetJSONFormat(BaseUpdateJSON):
    """WidgetJSONFormat class is designed to update widget JSON file according to Demisto's convention.

       Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the JSON to.
    """

    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '',
                 no_validate: bool = False):
        super().__init__(input, output, path, from_version, no_validate)

    def run_format(self) -> int:
        try:
            print_color(f'\n======= Updating file: {self.source_file} =======', LOG_COLORS.WHITE)
            self.update_json()
            self.set_description()
            self.set_isPredefined()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE

        except Exception:
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the widget JSON updater."""
        format = self.run_format()
        return format, SKIP_RETURN_CODE

    def set_isPredefined(self):
        """
        isPredefined is a required field for widget.
        If the key does not exist in the json file, a field will be set with true value.

        """
        if not self.data.get('isPredefined'):
            self.data['isPredefined'] = True
