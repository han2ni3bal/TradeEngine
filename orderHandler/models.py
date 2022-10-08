from django.db import models


# Create your models here.
class Orders(models.Model):
    order_id = models.AutoField(primary_key=True)
    order_time = models.DateTimeField(auto_now_add=True)
    order_type = models.CharField(max_length=128, blank=False)
    order_price = models.IntegerField(blank=False)
    order_quantity = models.IntegerField(blank=False)
    order_left_quantity = models.IntegerField(blank=True, null=True)
    order_status = models.CharField(max_length=16, blank=False, default="enqueued")

    class Meta:
        db_table = 'orderHandler_orders'

    def __str__(self):
        return "{}-{}".format(self.order_id, self.order_time)

    @classmethod
    def create(cls, order_type, order_price, order_quantity, order_status):
        order = cls()
        order.order_type = order_type
        order.order_price = order_price
        order.order_quantity = order_quantity
        order.order_left_quantity = order_quantity
        order.order_status = order_status
        order.save()
        return order

    def as_json(self):
        return {
            "order_id": self.order_id,
            "order_time": str(self.order_time),
            "order_type": self.order_type,
            "order_price": self.order_price,
            "order_quantity": self.order_quantity,
            "order_left_quantity": self.order_left_quantity,
            "order_status": self.order_status,
        }
