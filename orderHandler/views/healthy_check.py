from django.http import JsonResponse

# Create your views here.
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def index(request):
  response = {"message": "Welcome to TradeEngine!"}
  return JsonResponse(response)
