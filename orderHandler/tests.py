from django.test import TestCase
from orderHandler.models import Orders


# Create your tests here.
class OrderTestCase(TestCase):
    def setUp(self):
        Orders.create(order_type="buy", order_price=100, order_quantity=2, order_status="enqueued")

    def test_order_left_quantity(self):
        status = Orders.objects.get(order_left_quantity=2).order_status
        self.assertEqual(status, "enqueued")
