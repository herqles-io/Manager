import json

import cherrypy

from hqlib.rabbitmq.rpc import RPCPublisher


class MainController(object):
    exposed = True

    def __init__(self, rabbitmq, database):
        self.rabbitmq = rabbitmq
        self.database = database

    def index(self):
        return "Manager Index"

    @cherrypy.tools.json_out()
    def ping(self):
        ping = {}

        try:
            with self.database.session():
                ping['sql'] = "ok"
        except Exception as e:
            cherrypy.response.status = 500
            ping['sql'] = e.message

        try:
            connection = self.rabbitmq.syncconnection()
            connection.close()
            ping['rabbitmq'] = "ok"
        except Exception as e:
            cherrypy.response.status = 500
            ping['rabbitmq'] = e.message

        return ping

    @cherrypy.tools.json_out()
    def method_not_allowed(self, **kwargs):
        raise cherrypy.HTTPError(405, "Method not Allowed")

    def jsonify_error(self, status, message, traceback, version):
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json'
        data = {'status': status, 'message': message}

        headers = cherrypy.request.headers

        if 'X-Debug' in headers:
            data['traceback'] = traceback

        return json.dumps(data)

    def auth(self, permission=None, debug=False):
        headers = cherrypy.request.headers

        if 'X-Auth-Token' not in headers:
            raise cherrypy.HTTPError(400, "Missing API Token")

        token = headers['X-Auth-Token']

        publisher = RPCPublisher(self.rabbitmq, "security", "validate")

        output = {'token': token}

        if permission is not None:
            output['permission'] = permission

        correlation_id = publisher.publish(output)

        if correlation_id is None:
            raise cherrypy.HTTPError(500, "Error publishing auth rpc")

        data = publisher.get_data(correlation_id)

        if data is None:
            raise cherrypy.HTTPError(500, "Did not hear back from a manager - security validate")

        if data['code'] != 200:
            raise cherrypy.HTTPError(data['code'], data['error'])

        cherrypy.request.user = {'id': data['user']['id'], 'name': data['user']['name']}


def setup(rabbitmq, database, identity, assignment):

    dispatcher = cherrypy.dispatch.RoutesDispatcher()

    main = MainController(rabbitmq, database)

    cherrypy.tools.auth = cherrypy.Tool("on_start_resource", main.auth)

    dispatcher.connect('main', '/', controller=main, action='index')
    dispatcher.connect('main', '/_ping', controller=main, action='ping')
    dispatcher.connect('main', '/_heartbeat', controller=main, action='ping')

    setup_user(main, dispatcher, identity, assignment)

    setup_job(database, main, dispatcher)

    setup_task(database, main, dispatcher)

    setup_worker(database, main, dispatcher)

    conf = {
        '/': {
            'request.dispatch': dispatcher,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }

    cherrypy.tree.mount(None, config=conf)

    cherrypy.config.update({'engine.autoreload.on': False,
                            'error_page.default': main.jsonify_error,
                            'engine.timeout_monitor.on': False,
                            'server.socket_port': 8080})
    cherrypy.engine.start()


def setup_worker(database, main_controller, dispatcher):
    from hqmanager.api.worker import WorkerAPIController
    worker = WorkerAPIController(database)

    dispatcher.connect('worker:get', '/worker', controller=worker, action='GET', conditions=dict(method=['GET']))

    dispatcher.connect('worker:delete', '/worker/{id}', controller=worker, action='DELETE', conditions=dict(method=['DELETE']))

    dispatcher.connect('worker:405', '/worker', controller=main_controller, action='method_not_allowed')


def setup_job(database, main_controller, dispatcher):
    from hqmanager.api.job import JobAPIController
    job = JobAPIController(database)

    dispatcher.connect('job:get', '/job/{job_id}', controller=job, action='GET', conditions=dict(method=['GET']))

    dispatcher.connect('job:405', '/job', controller=main_controller, action='method_not_allowed')


def setup_task(database, main_controller, dispatcher):
    from hqmanager.api.task import TaskAPIController
    task = TaskAPIController(database)

    dispatcher.connect('task', '/task', controller=task, action='GET', conditions=dict(method=['GET']))
    dispatcher.connect('task:single', '/task/{task_id}', controller=task, action='GET', conditions=dict(method=['GET']))
    dispatcher.connect('task:405', '/task', controller=main_controller, action='method_not_allowed')


def setup_user(main_controller, dispatcher, identity, assignment):
    from hqmanager.api.user import UserAPIController
    user = UserAPIController(identity, assignment)

    # User API
    dispatcher.connect('user', '/user', controller=user, action='index')

    # Add User
    dispatcher.connect('user:add', '/user/add', controller=user, action='add',
                       conditions=dict(method=['POST']))
    dispatcher.connect('user:add:405', '/user/add', controller=main_controller, action='method_not_allowed')

    # Get token
    dispatcher.connect('user:token', '/user/token', controller=user, action='get_token',
                       conditions=dict(method=['PUT']))
    dispatcher.connect('user:token:405', '/user/token', controller=main_controller, action='method_not_allowed')

    # Change password
    dispatcher.connect('user:password', '/user/password', controller=user,
                       action='change_password', conditions=dict(method=['PUT']))
    dispatcher.connect('user:password:405', '/user/password', controller=main_controller, action='method_not_allowed')

    # Add Permissions
    dispatcher.connect('user:permission:add', '/user/permission', controller=user,
                       action='add_permission', conditions=dict(method=['PUT']))
    # dispatcher.connect('user:permission:405', '/user/permission', controller=main_controller,
    #                   action='method_not_allowed')

    # Remove Permissions
    dispatcher.connect('user:permission:delete', '/user/permission', controller=user,
                       action='remove_permission', conditions=dict(method=['DELETE']))
    dispatcher.connect('user:permission:405', '/user/permission', controller=main_controller,
                       action='method_not_allowed')

    # Get User
    dispatcher.connect('user:get', '/user/{username}', controller=user, action='get',
                       conditions=dict(method=['GET']))
    # dispatcher.connect('user:get:405', '/user/{username}', controller=main_controller, action='method_not_allowed')

    # Delete User
    dispatcher.connect('user:delete', '/user/{username}', controller=user, action='delete',
                       conditions=dict(method=['DELETE']))
    dispatcher.connect('user:delete:405', '/user/{username}', controller=main_controller, action='method_not_allowed')
