import atexit
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Optional

import requests
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import (get_content_path, print_warning,
                                               run_command_os)

NO_HTML = '<!-- NOT_HTML_DOC -->'
YES_HTML = '<!-- HTML_DOC -->'


class ReadMeValidator(BaseValidator):
    """ReadMeValidator is a validator for readme.md files
        In order to run the validator correctly please make sure:
        - Node is installed on you machine
        - make sure that the module '@mdx-js/mdx', 'fs-extra', 'commander' are installed in node-modules folder.
            If not installed, the validator will print a warning with the relevant module that is missing.
            please install it using "npm install *missing_module_name*"
        - 'DEMISTO_README_VALIDATION' environment variable should be set to True.
            To set the environment variables, run the following shell commands:
            export DEMISTO_README_VALIDATION=True
    """

    # Static var to hold the mdx server process
    _MDX_SERVER_PROCESS: Optional[subprocess.Popen] = None
    _MDX_SERVER_LOCK = Lock()

    def __init__(self, file_path: str, ignored_errors=None, print_as_warnings=False, suppress_print=False):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print)
        self.content_path = get_content_path()
        self.file_path = Path(file_path)
        self.pack_path = self.file_path.parent
        self.node_modules_path = self.content_path / Path('node_modules')

    def is_valid_file(self) -> bool:
        """Check whether the readme file is valid or not
        Returns:
            bool: True if env configured else Fale.
        """
        if os.environ.get('DEMISTO_README_VALIDATION') or os.environ.get('CI'):
            return all([
                self.is_image_path_valid(),
                self.is_mdx_file()
            ])
        else:
            print_warning(f"Skipping README validation of {self.file_path}")
            return True

    def mdx_verify(self) -> bool:
        mdx_parse = Path(__file__).parent.parent / 'mdx-parse.js'
        # run the java script mdx parse validator
        _, stderr, is_not_valid = run_command_os(f'node {mdx_parse} -f {self.file_path}', cwd=self.content_path,
                                                 env=os.environ)
        if is_not_valid:
            error_message, error_code = Errors.readme_error(stderr)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def mdx_verify_server(self) -> bool:
        if not ReadMeValidator._MDX_SERVER_PROCESS:
            ReadMeValidator.start_mdx_server()
        with open(self.file_path, 'r') as f:
            readme_content = f.read()
        response = requests.post('http://localhost:6161', data=readme_content.encode('utf-8'), timeout=10)
        if response.status_code != 200:
            error_message, error_code = Errors.readme_error(response.text)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_mdx_file(self) -> bool:
        html = self.is_html_doc()
        valid = self.are_modules_installed_for_verify(self.content_path)
        if valid and not html:
            # add to env var the directory of node modules
            os.environ['NODE_PATH'] = str(self.node_modules_path) + os.pathsep + os.getenv("NODE_PATH", "")
            if os.getenv('DEMISTO_MDX_CMD_VERIFY'):
                return self.mdx_verify()
            else:
                return self.mdx_verify_server()
        return True

    @staticmethod
    @lru_cache(None)
    def are_modules_installed_for_verify(content_path: str) -> bool:
        """ Check the following:
            1. npm packages installed - see packs var for specific pack details.
            2. node interperter exists.
        Returns:
            bool: True If all req ok else False
        """
        missing_module = []
        valid = True
        # Check node exist
        stdout, stderr, exit_code = run_command_os('node -v', cwd=content_path)
        if exit_code:
            print_warning(f'There is no node installed on the machine, Test Skipped, error - {stderr}, {stdout}')
            valid = False
        else:
            # Check npm modules exsits
            packs = ['@mdx-js/mdx', 'fs-extra', 'commander']
            for pack in packs:
                stdout, stderr, exit_code = run_command_os(f'npm ls {pack}', cwd=content_path)
                if exit_code:
                    missing_module.append(pack)
        if missing_module:
            valid = False
            print_warning(f"The npm modules: {missing_module} are not installed, Test Skipped, use "
                          f"'npm install <module>' to install all required node dependencies")
        return valid

    def is_html_doc(self) -> bool:
        txt = ''
        with open(self.file_path, 'r') as f:
            txt = f.read(4096).strip()
        if txt.startswith(NO_HTML):
            return False
        if txt.startswith(YES_HTML):
            return True
        # use some heuristics to try to figure out if this is html
        return txt.startswith('<p>') or txt.startswith('<!DOCTYPE html>') or ('<thead>' in txt and '<tbody>' in txt)

    def is_image_path_valid(self) -> bool:
        with open(self.file_path) as f:
            readme_content = f.read()
        invalid_paths = re.findall(
            r'(\!\[.*?\]|src\=)(\(|\")(https://github.com/demisto/content/(?!raw).*?)(\)|\")', readme_content,
            re.IGNORECASE)
        if invalid_paths:
            for path in invalid_paths:
                path = path[2]
                alternative_path = path.replace('blob', 'raw')
                error_message, error_code = Errors.image_path_error(path, alternative_path)
                self.handle_error(error_message, error_code, file_path=self.file_path)
            return False
        return True

    @staticmethod
    def start_mdx_server():
        with ReadMeValidator._MDX_SERVER_LOCK:
            if not ReadMeValidator._MDX_SERVER_PROCESS:
                mdx_parse_server = Path(__file__).parent.parent / 'mdx-parse-server.js'
                ReadMeValidator._MDX_SERVER_PROCESS = subprocess.Popen(['node', str(mdx_parse_server)],
                                                                       stdout=subprocess.PIPE, text=True)
                line = ReadMeValidator._MDX_SERVER_PROCESS.stdout.readline()
                if 'MDX server is listening on port' not in line:
                    ReadMeValidator.stop_mdx_server()
                    raise Exception(f'Failed starting mdx server. stdout: {line}.')

    @staticmethod
    def stop_mdx_server():
        if ReadMeValidator._MDX_SERVER_PROCESS:
            ReadMeValidator._MDX_SERVER_PROCESS.terminate()
            ReadMeValidator._MDX_SERVER_PROCESS = None


atexit.register(ReadMeValidator.stop_mdx_server)
