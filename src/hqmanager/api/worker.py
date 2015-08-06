import cherrypy
import logging
from hqlib.sql.models import Worker
import datetime
from hqmanager import unix_time_millis


class WorkerAPIController(object):

    exposed = True

    def __init__(self, database):
        self.logger = logging.getLogger("hq.manager.api.worker")
        self.database = database

    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.worker.get")
    def GET(self, framework=None, target=None, datacenter=None):

        workers = []

        with self.database.session() as session:
            worker_objects = session.query(Worker).filter(Worker.deleted == False).order_by(Worker.id.asc())

            if framework is not None:
                worker_objects = worker_objects.filter(Worker.framework == framework)

            if target is not None:
                worker_objects = worker_objects.filter(Worker.target == target)

            if datacenter is not None:
                worker_objects = worker_objects.filter(Worker.datacenter == datacenter)

            for worker in worker_objects:
                data = {'id': worker.id,
                        'target': worker.target,
                        'framework': worker.framework,
                        'datacenter': worker.datacenter,
                        'tags': worker.tags,
                        'created_at': unix_time_millis(worker.created_at),
                        'updated_at': unix_time_millis(worker.updated_at)}

                workers.append(data)

        return {"workers": workers}

    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.worker.delete")
    def DELETE(self, id):

        # TODO: delete the exchange

        with self.database.session() as session:
            worker = session.query(Worker).filter(Worker.id == id).filter(Worker.deleted == False).first()

            if worker is None:
                raise cherrypy.HTTPError(404, "Unknown worker")

            worker.deleted = True
            worker.deleted_at = datetime.datetime.now()
            session.commit()
            return {str(worker.id): "deleted"}
