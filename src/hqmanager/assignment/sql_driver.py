import random
import hashlib
import base64
import datetime
import logging
import json

from schematics.exceptions import ModelValidationError, ModelConversionError
from schematics.models import Model
from schematics.types import StringType

from hqlib.sql.models import UserAssignment, Token, Permission
from hqmanager.assignment.driver import AssignmentAbstractDriver, AssignmentMissingDBConnectionException
from hqmanager import unix_time_millis


class AssignmentDriver(AssignmentAbstractDriver):
    def __init__(self):
        super(AssignmentDriver, self).__init__()
        self.logger = logging.getLogger("hq.manager.assignment.sql")
        self.database = None

    def db_connections(self, **kwargs):
        if 'database' not in kwargs:
            raise AssignmentMissingDBConnectionException("Missing sql connection")

        self.database = kwargs['database']

    def validate_config(self, config):

        class ConfigValidator(Model):
            admin_username = StringType(required=True)

        try:
            self.config = ConfigValidator(config, strict=False)
        except ModelConversionError as e:
            self.logger.error("Could not create config for assignment SQL driver " + json.dumps(e.message))
            return False

        try:
            self.config.validate()
        except ModelValidationError as e:
            self.logger.error("Could not validate config for assignment SQL driver " + json.dumps(e.message))
            return False

        if not self.has_assignment(self.config.admin_username):
            self.create_assignment(self.config.admin_username)

        return True

    def get_assignment_id(self, username):
        with self.database.session() as session:
            assignment = session.query(UserAssignment).filter(UserAssignment.username == username).first()
            return assignment.id

    def validate_token(self, token):
        with self.database.session() as session:
            token = session.query(Token).filter(Token.token == token).first()
            if token is None:
                return False
            if unix_time_millis(token.updated_at) < \
                    unix_time_millis(datetime.datetime.now() - datetime.timedelta(hours=3)):
                return False
        return True

    def remove_permission(self, username, permission):
        with self.database.session() as session:
            session.query(Permission).join(UserAssignment, UserAssignment.id == Permission.user_assignment_id). \
                filter(UserAssignment.username == username). \
                filter(Permission.permission == permission).delete()
            session.commit()

    def has_permission_user(self, username, permission, exact=False):

        if username == self.config.admin_username:
            return True

        with self.database.session() as session:
            perms = session.query(Permission).join(UserAssignment, UserAssignment.id == Permission.user_assignment_id). \
                filter(UserAssignment.username == username)

            for perm in perms:
                perm_split = perm.permission.split(".")
                permission_split = permission.split(".")

                matches = True

                if len(permission_split) >= len(perm_split):
                    for i in range(0, len(perm_split)):
                        if perm_split[i] == permission_split[i]:
                            continue
                        elif perm_split[i] == "*" and exact is False:
                            continue
                        else:
                            matches = False
                            break
                else:
                    matches = False

                if matches is False:
                    continue

                return True

        return False

    def has_permission_token(self, token, permission, exact=False):
        return self.has_permission_user(self.get_username_from_token(token), permission, exact)

    def has_assignment(self, username):
        with self.database.session() as session:
            assignment = session.query(UserAssignment).filter(UserAssignment.username == username).first()
        if assignment is None:
            return False
        return True

    def get_username_from_token(self, token):
        with self.database.session() as session:
            assignment = session.query(UserAssignment).join(Token, Token.id == UserAssignment.token_id). \
                filter(Token.token == token).first()

            return assignment.username

    def get_token(self, username, force=False):
        with self.database.session() as session:
            assignment = session.query(UserAssignment).filter(UserAssignment.username == username).first()
            if assignment.token is None:
                assignment.token = Token()

            if assignment.token.token is None or unix_time_millis(assignment.token.updated_at) < \
                    unix_time_millis(datetime.datetime.now() - datetime.timedelta(hours=3)) or force:
                token = base64.b64encode(hashlib.sha256(str(random.getrandbits(256))).digest(),
                                         random.choice(['rA', 'aZ', 'gQ', 'hH', 'hG', 'aR', 'DD'])).rstrip('==')
                assignment.token.token = token

            token = assignment.token
            session.add(token)
            session.commit()
            return token.token, unix_time_millis(token.updated_at + datetime.timedelta(hours=3))

    def get_permissions(self, username):
        permissions = []
        with self.database.session() as session:
            assignment = session.query(UserAssignment).filter(UserAssignment.username == username).first()

            for perm in assignment.permissions:
                permissions.append(perm.permission)
        assignment.permissions.append(perm)
        session.commit()

        return permissions

    def delete_assignment(self, username):
        with self.database.session() as session:
            session.query(UserAssignment).filter(UserAssignment.username == username).delete()
            session.commit()

    def create_assignment(self, username):
        with self.database.session() as session:
            assignment = UserAssignment(username=username)
            session.add(assignment)
            session.commit()
            session.refresh(assignment)

    def add_permission(self, username, permission):
        with self.database.session() as session:
            assignment = session.query(UserAssignment).filter(UserAssignment.username == username).first()
            perm = Permission(permission=permission)
