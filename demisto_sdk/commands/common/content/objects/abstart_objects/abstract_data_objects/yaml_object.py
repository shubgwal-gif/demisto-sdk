from typing import Union

from ruamel.yaml import YAML
from wcmatch.pathlib import Path

from dictionary_based_object import DictionaryBasedObject


class YAMLObject(DictionaryBasedObject):
    def __init__(self, path: Union[Path, str], file_name_prefix: str = ""):
        super().__init__(path=self._fix_path(path), file_name_prefix=file_name_prefix)
        self._yaml = YAML(typ='rt')
        self._yaml.preserve_quotes = True
        self._yaml.width = 50000

    @staticmethod
    def _fix_path(path: Union[Path, str]):
        path = Path(path)
        if path.is_dir():
            try:
                path = next(path.glob([f"*.yaml", f"*.yml"]))
            except Exception as e:
                raise BaseException(f"Unable to find yaml/yml file in path {path}, Full error: {e}")
        elif not (path.is_file() or path.suffix in ["yaml", "yml"]):
            raise BaseException(f"Unable to find yaml/yml file in path {path}")

        return path

    def _unserialize(self) -> dict:
        try:
            self._as_dict = self._yaml.load(self.path)
        except Exception as e:
            raise BaseException(f"{self._path} is not valid yaml file, Full error: {e}")

    def _serialize(self, dest: Path):
        try:
            self._yaml.dump(data=self._as_dict, stream=self.path)
        except Exception as e:
            raise BaseException(f"{self.path} unable to dump yaml object to {dest}: {e}")

        return dest
