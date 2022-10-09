import yaml
import requests
import time
from func_timeout import func_set_timeout
import func_timeout
from functools import wraps
from django.views.decorators.csrf import csrf_exempt
from loguru import logger
from django.http import JsonResponse
from django.db import transaction
from rest_framework.generics import ListCreateAPIView
from orderHandler.models import Orders


def check_method(method):
    def check_method_inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = args[0]
            if request.method == method:
                return func(*args, **kwargs)
            else:
                response = {
                    "error": True,
                    "message": "{} method not allowed".format(request.method)
                }
                return JsonResponse(response, status=400)

        return wrapper

    return check_method_inner


def list_orders():
    try:
        query = Orders.objects.all()
        tasks = [task.as_json() for task in query.order_by('-order_time')]
        total_number = len(tasks)
        return JsonResponse({"data": tasks, "total": total_number})
    except Orders.DoesNotExist:
        response = {"error": True, "message": "Required task doesn't exist"}
        return JsonResponse(response, status=400)


def check_request_body(body):
    order_type = body.get("type", None)
    order_price = body.get("price", None)
    order_quantity = body.get("quantity", None)
    if order_type is None or order_type not in ['buy', 'sell']:
        raise Exception("Parameters TYPE is illegal")
    if order_price is None or not isinstance(order_price, int):
        raise Exception("Parameters PRICE is illegal")
    if order_quantity is None or not isinstance(order_quantity, int):
        raise Exception("Parameters QUANTITY is illegal")
    return {k: v for k, v in body.items() if v is not None}


class OrdersCreateListViews(ListCreateAPIView):

    def create(self, request, *args, **kwargs):

        # Check the reqeust body
        try:
            logger.info(yaml.safe_load(request.body))
            body = check_request_body(yaml.safe_load(request.body.decode("utf-8")))
        except Exception as e:
            logger.exception("check request body failed: {}".format(e.args[0]))
            return JsonResponse({"error": True, "message": e.args[0]}, status=400)

        # Parse request data
        order_type = body.get("type")
        order_price = body.get("price")
        order_quantity = body.get("quantity")

        try:
            with transaction.atomic():
                order = Orders.create(order_type=order_type,
                                      order_price=order_price, order_quantity=order_quantity, order_status="enqueued")
                response = order.as_json()
        except Exception as e:
            logger.exception("Fail request create order, backend Error: {}".format(e))
            response = {
                "error": True,
                "message": "Failed to create order"
            }
            return JsonResponse(response, status=500)
        return JsonResponse(response, status=200)

    def get(self, request, *args, **kwargs):
        return list_orders()


@csrf_exempt
@check_method(method="POST")
def make_trade(request):
    # Create a trade inside database
    create_response = requests.post(url='http://127.0.0.1:8000/trade/orders', data=request.body)
    if create_response.status_code != 200:
        return JsonResponse(create_response, status=500)
    order_id = create_response.json().get("order_id")
    left_quantity = create_response.json().get("order_left_quantity")
    # Start to check the status of trade inside the database
    url = "http://127.0.0.1:8000/trade/orders/{}".format(order_id)
    status = None
    try:
        status, quantity = check_trade_status(url, order_id)
        if quantity is not None:
            left_quantity = quantity
    except func_timeout.exceptions.FunctionTimedOut:
        logger.info("Time out for order{}, if you order is filled, you will receive a message!".format(order_id))
        try:
            check_response = requests.get(url=url)
            if check_response.status_code != 200:
                raise Exception("Fail to check trade")
            left_quantity = check_response.json().get("order_left_quantity")
            status = check_response.json().get("order_status")
        except Exception as e:
            logger.exception(e)
    # Return response by different status
    if status == "filled":
        response = {"error": False, "message": "The trade id: {}, has been filled".format(order_id)}
    elif status == "enqueued":
        response = {"error": False, "message": "The trade id: {}, has not been filled, "
                                               "left quantity is {}".format(order_id, left_quantity)}
    elif status == "killed":
        response = {"error": False, "message": "The trade id: {}, has been killed by users, "
                                               "left quantity is {}".format(order_id, left_quantity)}
    else:
        response = {"error": True, "message": "Something went wrong, id:{} , status:{}".format(order_id, status)}
    return JsonResponse(response, status=200)


@func_set_timeout(30)
def check_trade_status(url: str, order_id: int) -> (str, int):
    status = "enqueued"
    left_quantity = None
    while status == "enqueued":
        logger.info("The trade,id:{} is still enqueued...".format(order_id))
        try:
            check_response = requests.get(url=url)
        except Exception as e:
            logger.exception(e)
            continue
        order_status = check_response.json().get("order_status")
        left_quantity = check_response.json().get("order_left_quantity")
        status = order_status
        time.sleep(5)
    return status, left_quantity
