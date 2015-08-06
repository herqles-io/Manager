import cherrypy
import logging
from hqlib.sql.models import Job
from hqmanager import unix_time_millis


class JobAPIController(object):

    exposed = True

    def __init__(self, database):
        self.logger = logging.getLogger("hq.manager.api.job")
        self.database = database

    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.job.get")
    def GET(self, job_id):

        with self.database.session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if job is None:
                raise cherrypy.HTTPError(404, "Unknown Job ID "+job_id)

            data = {'id': job.id,
                    'name': job.name,
                    'status': job.status.value,
                    'datacenter': job.datacenter,
                    'targets': [],
                    'created_at': unix_time_millis(job.created_at),
                    'updated_at': unix_time_millis(job.updated_at)}

            for job_target in job.targets:
                target_data = {
                    'target': job_target.worker.target,
                    'tasks': []
                }
                if job_target.tags is not None:
                    target_data['tags'] = job_target.tags
                for task in job_target.tasks:
                    task_data = {
                        'id': task.id,
                        'status': task.status.value
                    }
                    target_data['tasks'].append(task_data)
                data['targets'].append(target_data)

            if job.stopped_at is not None:
                data['stopped_at'] = unix_time_millis(job.stopped_at)

            return data
