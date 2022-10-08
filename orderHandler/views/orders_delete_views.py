from django.db import transaction
from django.http import JsonResponse
from rest_framework.generics import RetrieveDestroyAPIView
from loguru import logger
from orderHandler.models import Orders


class OrdersRetrieveDestroyViews(RetrieveDestroyAPIView):

  def destroy(self, request, *args, **kwargs):
    return self.delete_order(kwargs.get("order_id"))

  @staticmethod
  def delete_order(order_id):
    order_object = None
    try:
      with transaction.atomic():
        # add distribute lock --- lock the code block
        order_object = Orders.objects.select_for_update().filter(order_id=order_id)
        order_object = order_object[0] if len(order_object) > 0 else None
        if order_object is None or order_object.order_status == "killed":
          logger.info("Order {} is not exist or already killed".format(order_id))
          return JsonResponse(
            {"message": "Warning, the resource is not exist or already killed."})
        if order_object.order_status == "enqueued":
          order_object.order_status = "killed"
          order_object.save()
          return JsonResponse({"message": "Successfully request to delete order."})
    except Orders.DoesNotExist:
      response = {"error": True, "message": "The requested order doesn't exist"}
      return JsonResponse(response, status=400)
    except Exception as e:
      logger.exception("Fail to delete resource: {}, exception: {}".format(order_object, e))
      return JsonResponse({
        "error": True,
        "message": "Fail to delete resource: {}, exception: {}".format(order_object, e)}, status=400)

  def retrieve(self, request, *args, **kwargs):
    return self.retrieve_order(kwargs.get("order_id"))

  @staticmethod
  def retrieve_order(order_id):
    order_object = None
    try:
      order_object = Orders.objects.filter(order_id=order_id)
      if len(order_object) != 0:
        order = order_object[0]
        response = order.as_json()
        return JsonResponse(response, status=200)
      else:
        response = {"error": True, "message": "The requested order doesn't exist"}
        return JsonResponse(response, status=400)
    except Exception as e:
      logger.exception("Fail to get resource: {}, exception: {}".format(order_object, e))
      return JsonResponse({
        "error": True,
        "message": "Fail to get resource: {}, exception: {}".format(order_object, e)}, status=400)
