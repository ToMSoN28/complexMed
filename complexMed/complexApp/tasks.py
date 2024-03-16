from datetime import timezone

from django.db.models import Q

from models import Visit

def update_status_cron():
    current_time = timezone.now().time()
    current_date = timezone.now().date()
    Visit.objects.filter(Q(start_time__lt=current_time) & Q(date=current_date) & Q(status='free')).update(status='passed')
    Visit.objects.filter(Q(start_time__lt=current_time) & Q(date=current_date) & Q(status='occupied')).update(status='in_process')
    Visit.objects.filter(Q(end_time__lt=current_time) & Q(date=current_date) & Q(status='in_process')).update(status='passed')
    pass
