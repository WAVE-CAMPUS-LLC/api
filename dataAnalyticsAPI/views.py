from django.http import JsonResponse
from django.db.models.functions import TruncDate
from django.db.models import Count
from authenticationApp.models import CustomUser

# Create your views here.
def userSignups(request):
    data = CustomUser.objects.annotate(date_joined_day=TruncDate('date_joined')).values('date_joined_day').annotate(count=Count('id')).values('date_joined_day')
    
    labels = [entry['date_joined_day'] for entry in data]
    counts = [entry['count'] for entry in data]
    
    return JsonResponse({"labels": labels, "counts": counts})