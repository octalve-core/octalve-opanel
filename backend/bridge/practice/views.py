import json
import uuid
from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from .engine import Store, Rejected

@never_cache
@csrf_protect
def workspace(request):
    if (not settings.DEBUG or not getattr(settings,'OPANEL_PRACTICE_ENABLED',False)
            or request.get_host().split(':')[0] not in ('localhost','127.0.0.1')):
        return JsonResponse({'detail':'Not found.'},status=404)
    path=getattr(settings,'OPANEL_PRACTICE_DATABASE','')
    if not path: return JsonResponse({'detail':'Practice storage is not configured.'},status=503)
    if request.method not in ('GET','POST'): return JsonResponse({'detail':'Method not allowed.'},status=405)
    key=request.get_signed_cookie('opanel_practice',default='',salt='opanel.practice.v1',max_age=86400)
    try: key=uuid.UUID(hex=key).hex
    except (ValueError,AttributeError): key=uuid.uuid4().hex
    store=Store(path)
    try:
        if request.method=='POST':
            if len(request.body)>20000: raise Rejected('Request too large.')
            data=json.loads(request.body)
            if not isinstance(data,dict) or set(data)-{'revision','request_id','operation','data','confirmed'}: raise Rejected('Invalid request.')
            state=store.apply(key,data.get('revision'),data.get('request_id'),data.get('operation'),data.get('data',{}),data.get('confirmed',False))
        else: state=store.read(key)
        response=JsonResponse({'state':state,'csrf_token':get_token(request)})
        response.set_signed_cookie('opanel_practice',key,salt='opanel.practice.v1',max_age=86400,httponly=True,samesite='Strict',path='/api/practice/')
        return response
    except (Rejected,ValueError,TypeError):
        return JsonResponse({'detail':'Action rejected. Check values, dependencies and confirmation, then refresh if the workspace changed.'},status=400)
