from distutils.version import LooseVersion
import click

from demisto_sdk.commands.common.constants import LAYOUT_BUILT_IN_FIELDS
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS

FROM_VERSION_FOR_NEW_CLASSIFIER = '6.0.0'
TO_VERSION_FOR_OLD_CLASSIFIER = '5.9.9'
CLASSIFICATION_TYPE = 'classification'


class ClassifierValidator(ContentEntityValidator):

    def __init__(self, structure_validator, new_classifier_version=True, ignored_errors=None,
                 print_as_warnings=False, suppress_print=False):
        super().__init__(structure_validator, ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print)
        self.new_classifier_version = new_classifier_version
        self.from_version = ''
        self.to_version = ''

    def is_valid_classifier(self, validate_rn=True, id_set_file=None):
        """Checks whether the classifier is valid or not.

        Returns:
            bool. True if classifier is valid, else False.
        """
        if not self.new_classifier_version:
            return all([
                super().is_valid_file(validate_rn),
                self.is_valid_version(),
                self.is_valid_from_version(),
                self.is_valid_to_version(),
                self.is_to_version_higher_from_version(),
                self.is_valid_type(),
                self.is_incident_field_exist(id_set_file)
            ])

        return all([
            super().is_valid_file(validate_rn),
            self.is_valid_version(),
            self.is_valid_from_version(),
            self.is_valid_to_version(),
            self.is_to_version_higher_from_version(),
            self.is_valid_type()
        ])

    def is_valid_version(self):
        """Checks if version field is valid. uses default method.

        Returns:
            bool. True if version is valid, else False.
        """
        return self._is_valid_version()

    def is_valid_from_version(self):
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        from_version = self.current_file.get('fromVersion', '') or self.current_file.get('fromversion', '')
        if from_version:
            self.from_version = from_version
            if self.new_classifier_version:
                if LooseVersion(from_version) < LooseVersion(FROM_VERSION_FOR_NEW_CLASSIFIER):
                    error_message, error_code = Errors.invalid_from_version_in_new_classifiers()
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        return False
            else:
                if LooseVersion(from_version) >= LooseVersion(FROM_VERSION_FOR_NEW_CLASSIFIER):
                    error_message, error_code = Errors.invalid_from_version_in_old_classifiers()
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        return False

        elif not from_version and self.new_classifier_version:
            error_message, error_code = Errors.missing_from_version_in_new_classifiers()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_valid_to_version(self):
        """Checks if to version field is valid.

        Returns:
            bool. True if to version filed is valid, else False.
        """
        to_version = self.current_file.get('toVersion', '') or self.current_file.get('toversion', '')
        if to_version:
            self.to_version = to_version
            if self.new_classifier_version:
                if LooseVersion(to_version) <= LooseVersion(FROM_VERSION_FOR_NEW_CLASSIFIER):
                    error_message, error_code = Errors.invalid_to_version_in_new_classifiers()
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        return False
            else:
                if LooseVersion(to_version) > LooseVersion(TO_VERSION_FOR_OLD_CLASSIFIER):
                    error_message, error_code = Errors.invalid_to_version_in_old_classifiers()
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        return False

        elif not to_version and not self.new_classifier_version:
            error_message, error_code = Errors.missing_to_version_in_old_classifiers()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_to_version_higher_from_version(self):
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.to_version and self.from_version:
            if LooseVersion(self.to_version) <= LooseVersion(self.from_version):
                error_message, error_code = Errors.from_version_higher_to_version()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False
        return True

    def is_valid_type(self):
        """Checks if type field is valid.

        Returns:
            bool. True if type field is valid, else False.
        """
        if self.new_classifier_version and self.current_file.get('type') != CLASSIFICATION_TYPE:
            error_message, error_code = Errors.invalid_type_in_new_classifiers()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_incident_field_exist(self, id_set_file) -> bool:
        is_valid = True

        if not id_set_file:
            click.secho("Skipping mapper incident field validation. Could not read id_set.json.", fg="yellow")
            return is_valid

        mapper_incident_fields = []

        mapper = self.current_file.get('mapping', {})

        for key, value in mapper.items():
            incident_fields = value.get('internalMapping', {})

            for inc_name, inc_info in incident_fields.items():
                mapper_incident_fields.append(inc_name)

        content_incident_fields = []
        content_all_incident_fields = id_set_file.get('IncidentFields')
        for content_inc_field in content_all_incident_fields:
            for _, inc_field in content_inc_field.items():
                content_incident_fields.append(inc_field.get('name', ''))

        content_indicator_fields = []
        content_all_indicator_fields = id_set_file.get('IndicatorFields')
        for content_ind_field in content_all_indicator_fields:
            for _, ind_field in content_ind_field.items():
                content_indicator_fields.append(ind_field.get('name', ''))

        all_valid_fields = content_indicator_fields + content_incident_fields + LAYOUT_BUILT_IN_FIELDS + BUILT_IN_FIELDS
        invalid_inc_fields_list = []
        for mapper_inc_field in mapper_incident_fields:
            if mapper_inc_field not in all_valid_fields:
                invalid_inc_fields_list.append(mapper_inc_field) if mapper_inc_field not in invalid_inc_fields_list \
                    else None

        if invalid_inc_fields_list:
            error_message, error_code = Errors.invalid_incident_field_in_mapper(invalid_inc_fields_list)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True
