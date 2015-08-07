import cherrypy


class UserAPIController(object):

    exposed = True

    def __init__(self, identity, assignment):
        self.identity = identity
        self.assignment = assignment

    def index(self):
        return "User api Index"

    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    @cherrypy.tools.auth(permission="herqles.user.add")
    def add(self):

        data = cherrypy.request.json

        if 'username' not in data:
            raise cherrypy.HTTPError(400, "Missing username")

        if 'password' not in data:
            raise cherrypy.HTTPError(400, "Missing Password")

        output = {data['username']: True, 'identity': False, 'assignment': False}

        if not self.identity.user_exists(data['username']):
            self.identity.create_user(data['username'], data['password'])
            output['identity'] = True

        if not self.assignment.has_assignment(data['username']):
            self.assignment.create_assignment(data['username'])
            output['assignment'] = True

        return output

    @cherrypy.tools.json_out()
    @cherrypy.tools.auth()  # If the username is the requests username allow them to see
    def get(self, username):
        headers = cherrypy.request.headers

        if not self.assignment.has_assignment(username):
            raise cherrypy.HTTPError(404, "User does not exist")

        if username != self.assignment.get_username_from_token(headers['X-Auth-Token']):
            if not self.assignment.has_permission_token(headers['X-Auth-Token'], 'herqles.user.get'):
                raise cherrypy.HTTPError(403, "Invalid permissions")

        permissions = self.assignment.get_permissions(username)

        return {'username': username, 'permissions': permissions}

    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.user.delete")
    def delete(self, username):

        if not self.assignment.has_assignment(username):
            raise cherrypy.HTTPError(404, "User does not exist")

        self.identity.delete_user(username)
        self.assignment.delete_assignment(username)

        return {username: "deleted"}

    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def get_token(self):
        data = cherrypy.request.json

        if 'username' not in data or 'password' not in data:
            raise cherrypy.HTTPError(400, "Username and password required")

        if not self.identity.auth(data['username'], data['password']):
            raise cherrypy.HTTPError(401, "Invalid username or password")

        if not self.assignment.has_assignment(data['username']):
            raise cherrypy.HTTPError(404, "User does not exist")

        (token, expire_at) = self.assignment.get_token(data['username'])
        return {"token": token, 'expire_at': long(expire_at)}

    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    @cherrypy.tools.auth()  # We only need to check permissions sometimes
    def change_password(self):
        headers = cherrypy.request.headers
        data = cherrypy.request.json

        if 'username' in data:
            if not self.assignment.has_permission_token(headers['X-Auth-Token'], 'herqles.user.password'):
                raise cherrypy.HTTPError(403, "Invalid permissions")

            username = data['username']

            if not self.assignment.has_assignment(username):
                raise cherrypy.HTTPError(404, "User does not exist")
        else:
            username = self.assignment.get_username_from_token(headers['X-Auth-Token'])

        if 'password' not in data:
            raise cherrypy.HTTPError(400, "Missing password")

        self.identity.change_password(username, data['password'])

        self.assignment.get_token(username, force=True)

        return {username: "password and token updated"}

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.user.permission.add")
    def add_permission(self):
        data = cherrypy.request.json
        username = data['username']
        permission = data['permission']

        if not self.assignment.has_assignment(username):
            raise cherrypy.HTTPError(404, "User does not exist")

        if self.assignment.has_permission_user(username, permission):
            raise cherrypy.HTTPError(400, "User already has permission "+permission)

        self.assignment.add_permission(username, permission)

        return {"username": username, permission: "added"}

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.user.permission.delete")
    def remove_permission(self):
        data = cherrypy.request.json
        username = data['username']
        permission = data['permission']

        if not self.assignment.has_assignment(username):
            raise cherrypy.HTTPError(404, "User does not exist")

        if self.assignment.has_permission_user(username, permission, exact=True) is False:
            raise cherrypy.HTTPError(400, "User does not have pemrission "+permission)

        return {"username": username, permission: "deleted"}
