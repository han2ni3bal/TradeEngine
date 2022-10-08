#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.urls import path

from orderHandler.views import orders_create_views, orders_delete_views, healthy_check

app_name = "orderHandler"

_healthy_url = [
  path("healthy_check", healthy_check.index, name="index"),
]


_order_url = [
  path("orders", orders_create_views.OrdersCreateListViews.as_view(), name="create_list_orders"),
  path("orders/<int:order_id>", orders_delete_views.OrdersRetrieveDestroyViews.as_view(),
       name="delete_orders"),
  path("orders/make", orders_create_views.make_trade, name="make_trade"),
]


urlpatterns = _healthy_url + _order_url
