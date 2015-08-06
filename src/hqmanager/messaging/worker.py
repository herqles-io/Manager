from hqlib.rabbitmq.routing import Subscriber as RoutingSubscriber
from hqlib.rabbitmq.routing import Publisher as RoutingPublisher
from hqlib.rabbitmq.rpc import RPCReplyPublisher
import json
from hqlib.sql.models import Worker


class WorkerRunTask(RoutingPublisher):

    def __init__(self, rabbitmq, worker):
        super(WorkerRunTask, self).__init__(rabbitmq, "worker-"+worker.target, "run-"+worker.framework)

    def run(self, task):
        self.publish(task)
        self.close()


class WorkerRegister(RoutingSubscriber):

    def __init__(self, rabbitmq, database):
        super(WorkerRegister, self).__init__(rabbitmq, "worker", "register", queue_name="worker_register", qos=1)
        self.database = database

    def message_deliver(self, channel, basic_deliver, properties, body):

        data = json.loads(body)

        with self.database.session() as session:
            worker = session.query(Worker).filter(Worker.target == data['target']).\
                filter(Worker.framework == data['framework']).filter(Worker.deleted == False).first()

            if worker is not None:
                worker.tags = data['tags']
            else:
                worker = Worker(target=data['target'], framework=data['framework'], datacenter=data['datacenter'],
                                tags=data['tags'])
                session.add(worker)
            session.commit()

            publisher = RPCReplyPublisher(self.rabbitmq, properties.reply_to, properties.correlation_id)
            publisher.publish({"id": str(worker.id)})
            publisher.close()

        channel.basic_ack(basic_deliver.delivery_tag)


class WorkerReload(RoutingSubscriber):

    def __init__(self, rabbitmq, database):
        super(WorkerReload, self).__init__(rabbitmq, "worker", "reload", queue_name="worker_reload", qos=1)
        self.database = database

    def message_deliver(self, channel, basic_deliver, properties, body):
        data = json.loads(body)

        with self.database.session() as session:
            worker = session.query(Worker).filter(Worker.target == data['target']). \
                filter(Worker.framework == data['framework']).filter(Worker.deleted == False).first()

            if worker is not None:
                worker.tags = data['tags']
                session.commit()

        channel.basic_ack(basic_deliver.delivery_tag)


class WorkerGet(RoutingSubscriber):

    def __init__(self, rabbitmq, database):
        super(WorkerGet, self).__init__(rabbitmq, "worker", "get", queue_name="worker_get", qos=1)
        self.database = database

    def message_deliver(self, channel, basic_deliver, properties, body):
        data = json.loads(body)

        workers = []

        with self.database.session() as session:
            worker_objects = session.query(Worker).filter(Worker.framework == data['framework']).\
                filter(Worker.datacenter == data['datacenter']).filter(Worker.deleted == False)

            for worker in worker_objects:
                data = {'id': worker.id,
                        'target': worker.target,
                        'framework': worker.framework,
                        'tags': worker.tags}

                workers.append(data)

        publisher = RPCReplyPublisher(self.rabbitmq, properties.reply_to, properties.correlation_id)
        publisher.publish({'workers': workers})
        publisher.close()

        channel.basic_ack(basic_deliver.delivery_tag)
