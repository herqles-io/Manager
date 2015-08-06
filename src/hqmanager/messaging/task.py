from hqlib.rabbitmq.routing import Subscriber as RoutingSubscriber
from hqlib.rabbitmq.rpc import RPCReplyPublisher, RPCPublisher
from hqmanager.messaging.worker import WorkerRunTask
import json
import datetime
from hqlib.sql.models import TaskStatus, Task, Worker


class TaskLaunchSubscriber(RoutingSubscriber):

    def __init__(self, rabbitmq, database):
        super(TaskLaunchSubscriber, self).__init__(rabbitmq, "task", "launch", queue_name="task_launch", qos=1)
        self.database = database

    def message_deliver(self, channel, basic_deliver, properties, body):
        data = json.loads(body)

        self.logger.info("Received task launch "+str(data['task_id']))

        with self.database.session() as session:
            task = session.query(Task).filter(Task.id == data['task_id']).first()

            publisher = RPCReplyPublisher(self.rabbitmq, properties.reply_to, properties.correlation_id)

            if task is None:
                publisher.publish({"error": "Unknown task_id "+data['task_id'], "code": 404})
                publisher.close()
                channel.basic_ack(basic_deliver.delivery_tag)
                return

            if task.status != TaskStatus.PENDING and task.status != TaskStatus.LOST:
                self.logger.warning("Task cannot launch")
                publisher.publish({"error": "Task "+data['task_id']+" does not have PENDING or LOST status", "code": 400})
                publisher.close()
                channel.basic_ack(basic_deliver.delivery_tag)
                return

            worker = session.query(Worker).filter(Worker.id == data['worker_id']).first()

            if worker is None:
                publisher.publish({"error": "Invalid worker id supplied", "code": 400})
                publisher.close()
                channel.basic_ack(basic_deliver.delivery_tag)
                return

            publisher_worker = RPCPublisher(self.rabbitmq, "worker-"+worker.target, "alive-"+worker.framework)
            corr_id = publisher_worker.publish({})

            if corr_id is None:
                publisher.publish({"error": "Worker Alive RPC corr_id is None", "code": 400})
                publisher.close()
                channel.basic_ack(basic_deliver.delivery_tag)
                return

            if publisher_worker.get_data(corr_id) is None:
                publisher.publish({"error": "Worker did not reply it is dead", "code": 400})
                publisher.close()
                channel.basic_ack(basic_deliver.delivery_tag)
                return

            task.status = TaskStatus.STARTING
            session.add(task)
            session.commit()
            session.refresh(task)

            data = {'id': task.id, 'name': task.name, 'actions': []}

            for action in task.actions:
                action_data = {'processor': action.processor, 'arguments': {}}

                if action.arguments is not None:
                    action_data['arguments'] = action.arguments

                data['actions'].append(action_data)

            WorkerRunTask(self.rabbitmq, worker).run(data)

            publisher.publish({"status": task.status.value, "code": 200})
            publisher.close()
            channel.basic_ack(basic_deliver.delivery_tag)


class TaskStatusSubscriber(RoutingSubscriber):

    def __init__(self, rabbitmq, database):
        super(TaskStatusSubscriber, self).__init__(rabbitmq, "task", "task_status", queue_name="task_status", qos=1)
        self.database = database

    def message_deliver(self, channel, basic_deliver, properties, body):
        data = json.loads(body)

        self.logger.info("Received task status "+str(data['task_id'])+" "+data['status'])

        with self.database.session() as session:
            task = session.query(Task).filter(Task.id == data['task_id']).first()

            if task is None:
                self.logger.warning("Unknown task in TaskStatusSubscriber")
                channel.basic_ack(basic_deliver.delivery_tag)
                return

            if data['status'] == TaskStatus.RUNNING.value:
                if task.status != TaskStatus.STARTING and task.status != TaskStatus.RUNNING:
                    self.logger.warning("Task status cannot be set to running. Not in starting or running status ("+task.status.value+")")
                else:
                    task.status = TaskStatus.RUNNING
                    session.add(task)
                    session.commit()

            elif data['status'] == TaskStatus.FINISHED.value:
                if task.status != TaskStatus.RUNNING:
                    self.logger.warning("Task status cannot be set to finished. Not in running status ("+task.status.value+")")
                else:
                    task.status = TaskStatus.FINISHED
                    task.stopped_at = datetime.datetime.now()
                    session.add(task)
                    session.commit()

            elif data['status'] == TaskStatus.FAILED.value:
                task.status = TaskStatus.FAILED
                task.error_message = data['message']
                task.stopped_at = datetime.datetime.now()
                session.add(task)
                session.commit()

        channel.basic_ack(basic_deliver.delivery_tag)
