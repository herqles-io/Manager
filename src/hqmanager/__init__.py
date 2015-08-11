import datetime
import json

import cherrypy
from schematics.exceptions import ModelValidationError, ModelConversionError

from yaml import YAMLError

from hqlib.rabbitmq import RabbitMQ
from hqlib.sql import SQLDB, Base
from hqmanager.messaging import *
import hqmanager.api
from hqmanager.config import parse_config, BaseConfig, RabbitMQConfig, SQLConfig, PathConfig, LDAPConfig
from hqlib.daemon import Daemon
from hqlib.ldap_db import LDAP


class ManagerDaemon(Daemon):
    def __init__(self, args):
        super(ManagerDaemon, self).__init__("Manager")
        self.args = args
        self.base_config = None
        self.path_config = None
        self.sql_config = None
        self.ldap_config = None
        self.rabbitmq_config = None
        self.rabbitmq = None

    def get_pid_file(self):
        return self.path_config.pid

    def get_log_path(self):
        return self.path_config.logs

    def setup(self):

        try:
            self.base_config = parse_config(self.args.config)
        except YAMLError as e:
            self.logger.error("Could not load base config" + str(e))
            return False
        except IOError as e:
            self.logger.error("Could not load worker config " + e.message)
            return False

        try:
            self.base_config = BaseConfig(self.base_config, strict=False)
        except ModelConversionError as e:
            self.logger.error("Could not create base config " + json.dumps(e.message))
            return False

        try:
            self.path_config = PathConfig(self.base_config.paths, strict=False)
        except ModelConversionError as e:
            self.logger.error("Could not create path config " + json.dumps(e.message))
            return False

        try:
            self.path_config.validate()
        except ModelValidationError as e:
            self.logger.error("Could not validate path config " + json.dumps(e.message))
            return False

        try:
            self.sql_config = SQLConfig(self.base_config.sql, strict=False)
        except ModelConversionError as e:
            self.logger.error("Could not create sql config " + json.dumps(e.message))
            return False

        try:
            self.sql_config.validate()
        except ModelValidationError as e:
            self.logger.error("Could not validate sql config " + json.dumps(e.message))
            return False

        if self.base_config.ldap is not None:
            try:
                self.ldap_config = LDAPConfig(self.base_config.ldap, strict=False)
            except ModelConversionError as e:
                self.logger.error("Could not create ldap config " + json.dumps(e.message))
                return False

            try:
                self.ldap_config.validate()
            except ModelValidationError as e:
                self.logger.error("Could not validate ldap config " + json.dumps(e.message))
                return False

        try:
            self.rabbitmq_config = RabbitMQConfig(self.base_config.rabbitmq, strict=False)
        except ModelConversionError as e:
            self.logger.error("Could not create rabbitmq config " + json.dumps(e.message))
            return False

        try:
            self.rabbitmq_config.validate()
        except ModelValidationError as e:
            self.logger.error("Could not validate rabbitmq config " + json.dumps(e.message))
            return False

        return True

    def run(self):
        database = SQLDB(self.sql_config.driver, self.sql_config.host, self.sql_config.port, self.sql_config.database,
                         self.sql_config.username, self.sql_config.password, self.sql_config.pool_size)
        database.connect()

        with database.session() as session:
            Base.metadata.create_all(bind=session.get_bind())

        ldap = None

        if self.ldap_config is not None:
            ldap = LDAP(self.ldap_config.host, self.ldap_config.domain, self.ldap_config.base_dn,
                        self.ldap_config.bind_username, self.ldap_config.bind_password)

        hosts = []
        for host in self.rabbitmq_config.hosts:
            (ip, port) = host.split(":")
            hosts.append((ip, int(port)))

        self.rabbitmq = RabbitMQ(hosts, self.rabbitmq_config.username, self.rabbitmq_config.password,
                                 self.rabbitmq_config.virtual_host)
        self.rabbitmq.setup_database()

        if 'driver' not in self.base_config.identity:
            self.logger.error("Identity Config does not have a driver")
            return False

        identity_module = self.base_config.identity['driver'].split(".")
        module = __import__(self.base_config.identity['driver'])
        identity_module.pop(0)
        for m in identity_module:
            module = getattr(module, m)
        identity = getattr(module, 'IdentityDriver')
        identity = identity()

        if not identity.validate_config(self.base_config.identity):
            self.logger.error("Error validating identity config")
            return False

        identity.db_connections(database=database, rabbitmq=self.rabbitmq, ldap=ldap)

        if 'driver' not in self.base_config.assignment:
            self.logger.error("Assignment Config does not have a driver set")
            return

        assignment_modules = self.base_config.assignment['driver'].split(".")
        module = __import__(self.base_config.assignment['driver'])
        assignment_modules.pop(0)
        for m in assignment_modules:
            module = getattr(module, m)
        assignment = getattr(module, 'AssignmentDriver')
        assignment = assignment()

        if not assignment.validate_config(self.base_config.assignment):
            self.logger.error("Error validating assignment config")
            return False

        assignment.db_connections(database=database, rabbitmq=self.rabbitmq, ldap=ldap)

        RegisterFrameworkSubscriber(self.rabbitmq).start()
        TaskStatusSubscriber(self.rabbitmq, database).start()
        TaskLaunchSubscriber(self.rabbitmq, database).start()
        WorkerRegister(self.rabbitmq, database).start()
        WorkerReload(self.rabbitmq, database).start()
        WorkerGet(self.rabbitmq, database).start()
        Validate(self.rabbitmq, assignment).start()
        hqmanager.api.setup(self.rabbitmq, database, identity, assignment)

        return True

    def on_shutdown(self, signum=None, frame=None):
        cherrypy.engine.exit()
        for subscriber in list(self.rabbitmq.active_subscribers):
            subscriber.stop()

    def on_reload(self, signum=None, frame=None):
        pass


def main(args):
    daemon = ManagerDaemon(args)
    daemon.start()


def unix_time_millis(dt):
    epoch = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=dt.tzinfo)
    delta = dt - epoch
    return int(delta.total_seconds() * 1000.0)
