from django.contrib import admin
from .models import Worker, Patient, Visit, VisitName

admin.site.register(Worker)
admin.site.register(Patient)
admin.site.register(Visit)
admin.site.register(VisitName)
