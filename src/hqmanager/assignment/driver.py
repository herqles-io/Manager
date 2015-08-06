from abc import ABCMeta, abstractmethod


class AssignmentAbstractDriver(object):

    __metaclass__ = ABCMeta

    def __init__(self):
        self.config = None

    @abstractmethod
    def validate_config(self, config):
        return False

    @abstractmethod
    def delete_assignment(self, username):
        pass

    @abstractmethod
    def has_permission_user(self, username, permission, exact=False):
        return False

    @abstractmethod
    def has_permission_token(self, token, permission, exact=False):
        return False

    @abstractmethod
    def add_permission(self, username, permission):
        pass

    @abstractmethod
    def remove_permission(self, username, permission):
        pass

    @abstractmethod
    def get_permissions(self, username):
        return []

    @abstractmethod
    def get_token(self, username, force=False):
        return None, 0

    @abstractmethod
    def get_assignment_id(self, username):
        return -1

    @abstractmethod
    def get_username_from_token(self, token):
        return ""

    @abstractmethod
    def validate_token(self, token):
        return False

    @abstractmethod
    def create_assignment(self, username):
        pass

    @abstractmethod
    def has_assignment(self, username):
        pass