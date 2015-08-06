from hqmanager.identity.driver import IdentityAbstractDriver
from hqlib.ldap_db import LDAP
import ldap as ldap_module
from schematics.exceptions import ModelValidationError, ModelConversionError
from schematics.models import Model
from schematics.types import StringType
from schematics.types.compound import DictType
import json
import logging
from hqmanager.config import LDAPConfig

class IdentityDriver(IdentityAbstractDriver):

    def __init__(self):
        super(IdentityDriver, self).__init__()
        self.ldap_config = None
        self.ldap = None
        self.logger = logging.getLogger("hq.manager.identity.ldap")

    def validate_config(self, config):

        class ConfigValidator(Model):
            ldap = DictType(StringType(), required=True)

        try:
            self.config = ConfigValidator(config, strict=False)
        except ModelConversionError as e:
            self.logger.error("Could not create config for identity LDAP driver " + json.dumps(e.message))
            return False

        try:
            self.config.validate()
        except ModelValidationError as e:
            self.logger.error("Could not validate config for identity LDAP driver " + json.dumps(e.message))
            return False

        try:
            self.ldap_config = LDAPConfig(self.config.ldap)
        except ModelConversionError as e:
            self.logger.error("Could not create ldap config for identity LDAP driver " + json.dumps(e.message))
            return False

        try:
            self.ldap_config.validate()
        except ModelValidationError as e:
            self.logger.error("Could not validate ldap config for identity LDAP driver " + json.dumps(e.message))
            return False

        self.ldap = LDAP(self.ldap_config.host, self.ldap_config.domain, self.ldap_config.base_dn)

        return True

    def delete_user(self, username):
        pass

    def create_user(self, username, password):
        pass

    def change_password(self, username, password):
        pass

    def auth(self, username, password):
        try:
            connection = self.ldap.connection_as(username, password)
        except ldap_module.INVALID_CREDENTIALS:
            return False

        connection.unbind()

        return True

    def user_exists(self, username):
        connection = self.ldap.connection_as(self.ldap_config.bind_username, self.ldap_config.bind_password)

        criteria = "(&(samaccountname="+username+"))"
        attributes = ['displayName']
        result = connection.search_s(self.ldap_config.base_dn, ldap_module.SCOPE_SUBTREE, criteria, attributes)[0][0]
        connection.unbind()

        if result is None:
            return False

        return True
