from abc import ABCMeta, abstractmethod


class IdentityAbstractDriver(object):

    __metaclass__ = ABCMeta

    def __init__(self):
        self.config = None

    @abstractmethod
    def validate_config(self, config):
        return False

    @abstractmethod
    def create_user(self, username, password):
        pass

    @abstractmethod
    def change_password(self, username, password):
        pass

    @abstractmethod
    def delete_user(self, username):
        pass

    @abstractmethod
    def auth(self, username, password):
        return True

    @abstractmethod
    def user_exists(self, username):
        return False
