from hqlib.rabbitmq.routing import Subscriber as RoutingSubscriber
from hqlib.rabbitmq.rpc import RPCReplyPublisher
import json


class Validate(RoutingSubscriber):

    def __init__(self, rabbitmq, assignment):
        super(Validate, self).__init__(rabbitmq, "security", "validate", queue_name="security_validate", qos=1)
        self.assignment = assignment

    def message_deliver(self, channel, basic_deliver, properties, body):
        data = json.loads(body)

        publisher = RPCReplyPublisher(self.rabbitmq, properties.reply_to, properties.correlation_id)

        token = data['token']

        if self.assignment.validate_token(token) is False:
            publisher.publish({"code": 403, "error": "Invalid API Token"})
            publisher.close()
            channel.basic_ack(basic_deliver.delivery_tag)
            return

        if 'permission' in data:
            if not self.assignment.has_permission_token(token, data['permission']):
                publisher.publish({"code": 403, "error": "Invalid user permissions"})
                publisher.close()
                channel.basic_ack(basic_deliver.delivery_tag)
                return

        username = self.assignment.get_username_from_token(token)
        user_id = self.assignment.get_assignment_id(username)

        publisher.publish({"code": 200, "user": {'id': user_id, 'name': username}})
        publisher.close()

        channel.basic_ack(basic_deliver.delivery_tag)
