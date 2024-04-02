from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from .views import (login_view, dashboard, logout_view, patient_registration, all_visits,
                    visit_detail, cancel_visit, assign_patient_to_visit_fun,patient_detail,
                    patient_search, visit_edit_by_doc, doc_dashboard, add_visit_name,
                    manager_dashboard)


urlpatterns = [
    path('login/', login_view, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/doctor/', doc_dashboard, name='doc_dashboard'),
    path('logout/', logout_view, name='logout'),
    path('patient-registration/', patient_registration, name='patient_registration'),
    path('patient/<int:patient_id>/', patient_detail, name='patient_detail'),
    path('patient/search', patient_search, name='patient_search'),
    path('visits/', all_visits, name='all_visits'),
    path('visit/<int:visit_id>/', visit_detail, name='visit_detail'),
    path('visit/<int:visit_id>/cancel/', cancel_visit, name='cancel_visit'),
    path('visit/<int:visit_id>/doctor/edit', visit_edit_by_doc, name='visit_edit_by_doc'),
    path('visit/<int:visit_id>/assign/patient/<int:patient_id>/', assign_patient_to_visit_fun, name='assign_patient_to_visit_fun'),
    path('visit-name/add/', add_visit_name, name='add_visit_name'),
    path('dashboard/manager/', manager_dashboard, name='manager_dashboard')
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
