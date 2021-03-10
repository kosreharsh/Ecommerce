from main import models

def order_middleware(get_response):
    def middleware(request):
        if 'order_id' in request.session:
            order_id = request.session['order_id']
            try:
                order = models.Order.objects.get(id=order_id)
                request.order = order
            except models.Order.DoesNotExist:
                request.order =None
        else:
            request.order = None
        
        response = get_response(request)
        return response
    return middleware