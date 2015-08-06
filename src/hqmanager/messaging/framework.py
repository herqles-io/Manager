from hqlib.rabbitmq.routing import Subscriber as RoutingSubscriber
from hqlib.rabbitmq.rpc import RPCReplyPublisher
import json
from uuid import uuid4


class RegisterFrameworkSubscriber(RoutingSubscriber):

    def __init__(self, rabbitmq):
        super(RegisterFrameworkSubscriber, self).__init__(rabbitmq, "framework", "register",
                                                          queue_name="framework_register", qos=1)

    def message_deliver(self, channel, basic_deliver, properties, body):
        data = json.loads(body)

        uuid = uuid4()

        publisher = RPCReplyPublisher(self.rabbitmq, properties.reply_to, properties.correlation_id)
        publisher.publish({"id": str(uuid)})
        publisher.close()

        channel.basic_ack(basic_deliver.delivery_tag)
