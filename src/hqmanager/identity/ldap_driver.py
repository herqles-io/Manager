import logging

import ldap as ldap_module

from hqmanager.identity.driver import IdentityAbstractDriver, IdentityMissingDBConnectionException


class IdentityDriver(IdentityAbstractDriver):
    def __init__(self):
        super(IdentityDriver, self).__init__()
        self.ldap = None
        self.logger = logging.getLogger("hq.manager.identity.ldap")

    def db_connections(self, **kwargs):

        if 'ldap' not in kwargs:
            raise IdentityMissingDBConnectionException("Missing ldap connection")

        if kwargs['ldap'] is None:
            raise IdentityMissingDBConnectionException("Missing ldap connection is None")

        self.ldap = kwargs['ldap']

    def validate_config(self, config):

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
        connection = self.ldap.connection_as(self.ldap.bind_username, self.ldap.bind_password)

        criteria = "(&(samaccountname=" + username + "))"
        attributes = ['displayName']
        result = connection.search_s(self.ldap.base_dn, ldap_module.SCOPE_SUBTREE, criteria, attributes)[0][0]
        connection.unbind()

        if result is None:
            return False

        return True
