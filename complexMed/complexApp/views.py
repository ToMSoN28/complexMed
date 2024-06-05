from datetime import datetime, date, timedelta

from django.db.models import Q, Count
from django.db.utils import IntegrityError
from django.shortcuts import render, redirect, reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.generic.detail import DetailView

from .models import Worker, Patient, Visit, VisitName



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
    # update_passed_visits()
    # Visit.cancel_visit(1)
    # Visit.assign_patient(2, 1)
    return render(request, 'dashboard.html', {'worker': worker})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def all_visits(request):
    worker = Worker.objects.get(user=request.user)
    visits = Visit.objects.all()
    # update_passed_visits()
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
        print(past_visits, upcoming_visits)
        visits = combination_visits_lists(upcoming_visits, past_visits)
        doctors = Worker.get_doctors()
        print(doctors)
        visits_names = VisitName.get_visits_names()
        available_visits = []
        available_visits_info = []
        if request.method == 'POST':
            visit_name = request.POST['selectName']
            doctor = request.POST['selectDoctor']
            week = request.POST['selectWeek']
            available_visits = Visit.get_available_visits(visit_name, doctor, week)
            available_visits_info = get_visits_dates(available_visits)
            # print(available_visits)
            # print(available_visits_info)


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
def visit_edit_by_doc(request, visit_id):
    worker = Worker.objects.get(user=request.user)
    try:
        visit = Visit.objects.get(pk=visit_id)
        if visit.doctor.id != worker.id or visit.status in ['free', 'occupied']:
            return redirect('visit_detail', visit_id=visit_id)

        if request.method == 'POST':
            visit.description = request.POST.get('description')
            visit.recommendation = request.POST.get('recommendation')
            visit.save()
            if 'save_exit' in request.POST or 'save_exit_confirm' in request.POST:
                return redirect('visit_detail', visit_id=visit_id)

        return render(request, 'visit_edit_by_doc.html', {'visit': visit, 'worker': worker})
    except Visit.DoesNotExist:
        # Handle the case where the visit does not exist
        return render(request, 'visit_not_found.html')


@login_required
def cancel_visit(request, visit_id):
    worker = Worker.objects.get(user=request.user)
    if request.method == 'POST' and worker.is_receptionist:
        try:
            visit = Visit.objects.get(pk=visit_id)
            patient_id = visit.patient.id
            status = visit.cancel_visit()
            if status:
                return redirect('patient_detail', patient_id=patient_id)
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
            return redirect('patient_detail', patient_id=patient_id)
        else:
            return render(request, 'serverError.html')
    return redirect('logout')

@login_required
def delete_visit(request, visit_id):
    worker = Worker.objects.get(user=request.user)
    if request.method == 'POST' and worker.is_manager:
        visit = Visit.objects.get(pk=visit_id)
        visit.delete_visit()
        return redirect('manager_dashboard')
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
def doc_dashboard(request):
    worker = Worker.objects.get(user=request.user)
    if True:
        past_visits = worker.get_past_visits()
        upcoming_visits = worker.get_upcoming_visits()
        # print(past_visits, upcoming_visits)
        visits = combination_visits_lists(upcoming_visits, past_visits)
        actual = worker.get_actual_visits()
        print(actual)
        now = datetime.now()
        # next = list(upcoming_visits)
        # print(next)
        return render(request, 'doc_dashboard.html', {'worker': worker, 'visits': visits, 'actual': actual, 'now': now })

@login_required
def add_visit_name(request):
    worker = Worker.objects.get(user=request.user)
    if request.method == 'POST' and worker.is_manager:
        name = request.POST['visit_name']
        # doctor
        # week
        print(name)
        VisitName.create_visit_name(name)
        return redirect('manager_dashboard')
    return redirect('logout')

@login_required
def add_visit(request):
    worker = Worker.objects.get(user=request.user)
    if request.method == 'POST' and worker.is_manager:
        name = request.POST['selectName']
        doc = request.POST['selectDoctor']
        date_v = request.POST['selectDate']
        s_time = request.POST['selectStart']
        e_time = request.POST['selectEnd']
        room = request.POST['room']
        price = request.POST['price']
        Visit.create_visit(doc, name, datetime.strptime(date_v, "%Y-%m-%d").date(),
                           datetime.strptime(s_time, "%H:%M").time(),
                           datetime.strptime(e_time, "%H:%M").time(),
                           price, room)
        print(name, doc, date_v, s_time, e_time, room, price)
        return redirect('manager_dashboard')
    return redirect('logout')

@login_required()
def create_account(request):
    worker = Worker.objects.get(user=request.user)
    error_msg = None
    if request.method == 'POST':
        username = request.POST['inputUsername']
        first = request.POST['inputFirstName']
        last = request.POST['inputLastName']
        email = request.POST['inputEmail']
        function = request.POST['selectFunction']
        password = request.POST['inputPassword']
        password1 = request.POST['inputPasswordAgain']
        is_receptionist, is_doctor = False, False
        if function == '0':
            is_receptionist = True
            print("recept")
        if function == '1':
            is_doctor = True
        if password == password1:
            print("same passwords")
            if Worker.username_valid(username):
                Worker.create_worker(username=username, password=password,
                                     email=email, first_name=first, last_name=last,
                                     is_doctor=is_doctor, is_receptionist=is_receptionist, is_manager=False)
                print("created", first, last, function)
                return redirect('workers_list')
            else:
                error_msg = f"Username: {username} is already used. Create account again."
        else:
            error_msg = "Passwords are not the same. Create account again."
        print(error_msg)

    return render(request, 'create_account.html', {'worker': worker, 'error_msg': error_msg})

@login_required
def workers_list(request):
    worker = Worker.objects.get(user=request.user)
    if worker.is_manager:
        q_objects = Q()
        search_applied = False
        if request.method == 'POST':
            first = request.POST['inputFirstName']
            last = request.POST['inputLastName']
            username = request.POST['inputUsername']
            if first:
                q_objects &= Q(user__first_name__icontains=first)
                search_applied = True
            if last:
                q_objects &= Q(user__last_name__icontains=last)
                search_applied = True
            if username:
                q_objects &= Q(user__username__icontains=username)
                search_applied = True
        if search_applied:
            workers = Worker.objects.filter(q_objects)
        else:
            workers = Worker.objects.all()
        return render(request, 'worker_list.html', {'worker': worker, 'workers': workers})

@login_required()
def manager_dashboard(request):
    worker = Worker.objects.get(user=request.user)
    if worker.is_manager:
        schedule_table = None
        days_table = None
        doctor = None
        visits_names = VisitName.get_visits_names()
        if request.method == "POST":
            doc_id = request.POST['scheduleDoctor']
            week = request.POST['selectWeek']
            print(doc_id, week)
            schedule_table, days_table = get_schedule_for_week_for_doctor(week, doc_id)
            print(schedule_table, len(schedule_table))
            doctor = worker.get_name(doc_id)
            print(doctor)
        doctors = Worker.get_doctors()
        print(doctors)
        return render(request, 'manager_dashboard.html', {'worker': worker, 'doctor': doctor, 'schedule_table': schedule_table, 'dates': days_table, 'doctors': doctors, 'visits_names': visits_names})
    return redirect('logout')


def start_end_of_working_week_for_date(date_of_week):
    # today = datetime.date.today()
    day_of_week = date_of_week.weekday()
    start_of_week = date_of_week - timedelta(days=day_of_week)
    end_of_week = start_of_week + timedelta(days=4)
    return start_of_week, end_of_week

def get_schedule_for_week_for_doctor(week, doctor_id):
    today = date.today()
    if week == 'next':
        today += timedelta(days=7)
    elif week == 'inTwo':
        today += timedelta(days=14)
        print(today)
    elif week == 'inThree':
        today += timedelta(days=21)
    elif week == 'inFour':
        today += timedelta(days=28)
    elif week == 'inFive':
        today += timedelta(days=35)
    start_of_week, end_of_week = start_end_of_working_week_for_date(today)
    current_date = start_of_week
    schedule_table = []
    days_table = []
    while current_date <= end_of_week:
        day_visit = Visit.gat_all_visits_for_doctor_for_date(doctor_id, current_date)
        print(day_visit, current_date)
        if len(day_visit) == 0:
            schedule_table.append([])
        else:
            tmp = []
            for visit in day_visit:
                tmp.append(visit)
            schedule_table.append(tmp)
        days_table.append(current_date)
        current_date += timedelta(days=1)
    maximum = 0
    for day in schedule_table:
        if len(day) > maximum:
            maximum = len(day)

    sch_tab = []
    for i in range(maximum):
        tmp = []
        for j in range(5):
            if i < len(schedule_table[j]):
                tmp.append(schedule_table[j][i])
            else:
                tmp.append(None)
        sch_tab.append(tmp)
    return sch_tab, days_table



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
    return unique_dates
