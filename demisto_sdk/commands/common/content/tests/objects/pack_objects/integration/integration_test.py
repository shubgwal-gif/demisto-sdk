from pathlib import Path

from demisto_sdk.commands.common.content.objects.pack_objects import \
    Integration
from demisto_sdk.commands.common.content.objects_factory import \
    ContentObjectFactory


class TestNotUnifiedIntegration:
    def test_objects_factory(self, datadir):
        obj = ContentObjectFactory.from_path(datadir["sample.yml"])
        assert isinstance(obj, Integration)

    def test_prefix(self, datadir):
        obj = Integration(datadir["sample.yml"])
        assert obj.normalize_file_name() == "integration-sample.yml"

    def test_files_detection(self, datadir):
        obj = Integration(datadir["sample.yml"])
        assert obj.readme.path == Path(datadir["README.md"])
        assert obj.code_path == Path(datadir["sample.py"])
        assert obj.description_path == Path(datadir["sample_description.md"])
        assert obj.png_path == Path(datadir["sample_image.png"])

    def test_is_unify(self, datadir):
        obj = Integration(datadir["sample.yml"])
        assert not obj.is_unify()


class TestUnifiedIntegration:
    def test_objects_factory(self, datadir):
        obj = ContentObjectFactory.from_path(datadir["integration-sample.yml"])
        assert isinstance(obj, Integration)

    def test_prefix(self, datadir):
        obj = Integration(datadir["integration-sample.yml"])
        assert obj.normalize_file_name() == "integration-sample.yml"

    def test_files_detection(self, datadir):
        obj = Integration(datadir["integration-sample.yml"])
        assert obj.readme.path == Path(datadir["integration-sample_README.md"])

    def test_is_unify(self, datadir):
        obj = Integration(datadir["integration-sample.yml"])
        assert obj.is_unify()