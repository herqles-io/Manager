import cherrypy
import logging
from hqlib.sql.models import Task, JobTarget
from hqmanager import unix_time_millis


class TaskAPIController(object):

    exposed = True

    def __init__(self, database):
        self.logger = logging.getLogger("hq.manager.api.task")
        self.database = database

    @cherrypy.tools.json_out()
    @cherrypy.tools.auth(permission="herqles.task.get")
    def GET(self, task_id=None, job_id=None, page=1):

        if task_id is None:
            tasks = []

            per_page = 20
            offset = (int(page) - 1) * per_page

            with self.database.session() as session:
                task_objects = session.query(Task).join(JobTarget, Task.job_target_id == JobTarget.id)

                if job_id is not None:
                    task_objects = task_objects.filter(JobTarget.job_id == job_id)

                task_objects = task_objects.order_by(Task.id.desc()).limit(per_page).offset(offset)

                for task in task_objects:
                    data = {'id': task.id,
                            'name': task.name,
                            'status': task.status.value,
                            'actions': [],
                            'created_at': unix_time_millis(task.created_at),
                            'updated_at': unix_time_millis(task.updated_at)}

                    for action in task.actions:
                        action_data = {'processor': action.processor}
                        if action.arguments is not None:
                            action_data['arguments'] = action.arguments
                        data['actions'].append(action_data)

                    if task.stopped_at is not None:
                        data['stopped_at'] = unix_time_millis(task.stopped_at)

                    tasks.append(data)

            return {"tasks": tasks}
        else:

            with self.database.session() as session:
                task = session.query(Task).filter(Task.id == task_id).first()

                if task is None:
                    return {}

                data = {'id': task.id,
                        'name': task.name,
                        'status': task.status.value,
                        'actions': [],
                        'created_at': unix_time_millis(task.created_at),
                        'updated_at': unix_time_millis(task.updated_at)}

                for action in task.actions:
                    action_data = {'processor': action.processor}
                    if action.arguments is not None:
                        action_data['arguments'] = action.arguments
                    data['actions'].append(action_data)

                if task.stopped_at is not None:
                    data['stopped_at'] = unix_time_millis(task.stopped_at)

                return data
