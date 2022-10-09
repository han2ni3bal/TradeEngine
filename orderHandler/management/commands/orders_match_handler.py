#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import time
from multiprocessing import Process
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from loguru import logger


from orderHandler.models import Orders


class Command(BaseCommand):
  help = "Orders handler"

  def __init__(self):
    super(Command, self).__init__()
    self.should_stop = False
    self.sleep_interval = 9

  def handle(self, *args, **options):
    connections.close_all()
    process_dict = {}
    func_list = ['select_and_handle_buy_orders']

    # Periodically check the queue
    while not self.should_stop:
      for func in func_list:
        process_func = process_dict.get(func, None)
        if process_func is None or (not process_func.is_alive()):
          func_obj = getattr(sys.modules[__name__], func)
          process_dict[func] = Process(target=func_obj)
          process_dict[func].daemon = True
          process_dict[func].start()

      logger.debug("Sleep for {} seconds".format(self.sleep_interval))
      time.sleep(self.sleep_interval)


def select_and_handle_buy_orders():
  connections.close_all()
  while True:
    with transaction.atomic():
      logger.info("Process starts to select and match orders")
      buy_orders = Orders.objects.select_for_update().\
        filter(order_type="buy", order_status="enqueued").order_by("order_time")
      for buy_order in buy_orders:
        logger.info("Start to match the order: Id:{}, Price:{} and Quantity:{}".
                    format(buy_order.order_id, buy_order.order_price, buy_order.order_quantity))
        try:
          left = match_buy_order_to_sell(buy_order)
          logger.info("The left number is {}".format(left))
        except ValueError as e:
          logger.warning("error occur:{}".format(e))
          continue
        if left > 0:
          buy_order.order_left_quantity = left
        else:
          buy_order.order_status = "filled"
          buy_order.order_left_quantity = 0
        buy_order.save()
      time.sleep(5)


def match_buy_order_to_sell(order):
  price = order.order_price
  quantity = order.order_left_quantity
  with transaction.atomic():
    sell_orders = Orders.objects.select_for_update().\
      filter(order_type="sell", order_status="enqueued", order_price=price)
    if len(sell_orders) == 0:
      raise ValueError("There is no matched sell orders for order {}!".format(order.order_id))
    sell_orders = sell_orders.order_by("order_time")
    logger.info(sell_orders)
    for sell_order in sell_orders:
      if sell_order.order_left_quantity > quantity:
        logger.info("The sell order is more than the buy order")
        sell_order.order_left_quantity = sell_order.order_left_quantity - quantity
        sell_order.save()
        return 0
      elif sell_order.order_left_quantity <= quantity:
        logger.info("The sell order can fill the buy order")
        sell_order.order_status = "filled"
        left = int(quantity - sell_order.order_left_quantity)
        sell_order.order_left_quantity = 0
        sell_order.save()
        return left
