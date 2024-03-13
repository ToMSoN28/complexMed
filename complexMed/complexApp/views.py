from datetime import datetime, date, timedelta

from django.db.models import Q, Count
from django.db.utils import IntegrityError
from django.shortcuts import render, redirect, reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.generic.detail import DetailView

from .models import Worker, Patient, Visit


class PatientDetailView(DetailView):
    model = Patient
    template_name = 'patient_detail.html'
    context_object_name = 'patient'


def login_view(request):
    if request.method == 'POST':
        username = request.POST['typeLoginX']
        password = request.POST['typePasswordX']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('all_visits')
        else:
            messages.error(request, "Incorrect Login or Password")

    return render(request, 'login.html')


@login_required
def dashboard(request):
    worker = Worker.objects.get(user=request.user)
    # Visit.assign_patient(8, 1)
    return render(request, 'dashboard.html', {'worker': worker})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def all_visits(request):
    worker = Worker.objects.get(user=request.user)
    visits = Visit.objects.all()
    update_passed_visits()
    now = datetime.now()
    return render(request, 'all_visits.html',
                  {'visits': visits, 'worker': worker, 'today': now.strftime('%B %d, %Y'), 'now': timezone.now()})


@login_required
def patient_detail(request, patient_id):
    worker = Worker.objects.get(user=request.user)
    try:
        patient = Patient.objects.get(pk=patient_id)
        past_visits = patient.get_past_visits()
        upcoming_visits = patient.get_upcoming_visits()
        visits = combination_visits_lists(upcoming_visits, past_visits)
        doctors = Worker.get_doctors()
        visits_names = Visit.get_visits_names()
        available_visits = []
        available_visits_info = []
        if request.method == 'POST':
            visit_name = request.POST['selectName']
            doctor = request.POST['selectDoctor']
            week = request.POST['selectWeek']
            available_visits = Visit.get_available_visits(visit_name, doctor, week)
            available_visits_info = get_visits_dates(available_visits)
            print(available_visits)
            print(available_visits_info)


        return render(request, 'patient_detail.html',
                      {'worker': worker, 'visits': visits, 'patient': patient, 'doctors': doctors,
                       'visits_names': visits_names, 'available': available_visits,
                       'available_info': available_visits_info})
    except Patient.DoesNotExist:
        # Handle the case where the visit does not exist
        return render(request, 'visit_not_found.html')


@login_required
def patient_search(request):
    worker = Worker.objects.get(user=request.user)
    if request.method == 'POST':
        first = request.POST['inputFirstName']
        last = request.POST['inputLastName']
        phone = request.POST['inputPhone']

        q_objects = Q()
        if first:
            q_objects &= Q(first_name__icontains=first)
        if last:
            q_objects &= Q(last_name__icontains=last)
        if phone:
            q_objects &= Q(phone_number__icontains=phone)

        filtered_patients = Patient.objects.filter(q_objects)
        return render(request, 'patient_search.html', {'worker': worker, 'patients': filtered_patients})
    return render(request, 'patient_search.html', {'worker': worker, })


@login_required
def visit_detail(request, visit_id):
    worker = Worker.objects.get(user=request.user)
    try:
        visit = Visit.objects.get(pk=visit_id)
        return render(request, 'visit_detail.html', {'visit': visit, 'worker': worker})
    except Visit.DoesNotExist:
        # Handle the case where the visit does not exist
        return render(request, 'visit_not_found.html')


@login_required
def cancel_visit(request, visit_id):
    worker = Worker.objects.get(user=request.user)
    if request.method == 'POST':
        name = request.POST['inputFirstName']
        try:
            visit = Visit.objects.get(pk=visit_id)
            if visit.patient.first_name == name:
                status = Visit.cancel_visit(visit_id)
            else:
                status = True
            if status:
                return redirect('visit_detail', visit_id=visit_id)
            else:
                return render(request, 'serverError.html')
        except Visit.DoesNotExist:
            # Handle the case where the visit does not exist
            return render(request, 'visit_not_found.html')
    return redirect('logout')


@login_required
def assign_patient_to_visit_fun(request, visit_id, patient_id):
    worker = Worker.objects.get(user=request.user)
    if request.method == 'POST' and worker.is_receptionist:
        status = Visit.assign_patient(visit_id, patient_id)
        if status:
            return redirect('visit_detail', visit_id=visit_id)
        else:
            return render(request, 'serverError.html')
    return redirect('logout')


@login_required
def patient_registration(request):
    worker = Worker.objects.get(user=request.user)
    if request.method == 'POST':
        first = request.POST['inputFirstName']
        last = request.POST['inputLastName']
        pesel = request.POST['inputPesel']
        phone = request.POST['inputPhoneNumber']

        try:
            new_patient = Patient.create_patient(first, last, pesel, phone)
            print("Pacjent utworzony pomyślnie:", new_patient)
            return redirect(reverse('patient_detail', args=[new_patient.id]))
        except IntegrityError as e:
            print(f"Błąd podczas tworzenia pacjenta: {e}")
        except ValueError as e:

            print(f"Błąd podczas tworzenia pacjenta: {e}")
    return render(request, 'register_patient.html', {'worker': worker})


@login_required
def assign_patient_to_visit(request, visit_id):
    worker = Worker.objects.get(user=request.user)

    try:
        visit = Visit.objects.get(pk=visit_id)
        if request.method == 'POST':
            first = request.POST['inputFirstName']
            last = request.POST['inputLastName']
            pesel = request.POST['inputPesel']

            q_objects = Q()
            if first:
                q_objects &= Q(first_name__icontains=first)
            if last:
                q_objects &= Q(last_name__icontains=last)
            if pesel:
                q_objects &= Q(pesel=pesel)

            filtered_patients = Patient.objects.filter(q_objects)

            return render(request, 'visit_assign.html',
                          {'worker': worker, 'visit': visit, 'patients': filtered_patients})
        return render(request, 'visit_assign.html', {'worker': worker, 'visit': visit})
    except Visit.DoesNotExist:
        return render(request, 'visit_not_found.html')


def update_passed_visits():
    visits_to_update = Visit.objects.filter(Q(status='free') | Q(status='occupied'))
    for visit in visits_to_update:
        visit.update_status()
    pass


def combination_visits_lists(upcoming_visits, past_visits):
    min_length = min(len(upcoming_visits), len(past_visits))
    combined_visits = [(upcoming_visits[i], past_visits[i]) for i in range(min_length)]
    combined_visits += [(upcoming_visits[i], None) for i in range(min_length, len(upcoming_visits))]
    combined_visits += [(None, past_visits[i]) for i in range(min_length, len(past_visits))]
    return combined_visits


def get_visits_dates(visit_list):
    unique_dates = (
        visit_list
        .values('date')
        .distinct()
        .order_by('date')
    )
    result_data = [entry['date'].strftime('%B %d, %Y') for entry in unique_dates]
    return result_data