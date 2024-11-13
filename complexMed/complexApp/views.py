from datetime import datetime, date, timedelta, time
from random import randint

from django.contrib.admin.views.decorators import staff_member_required
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
            worker = Worker.objects.get(user=user)
            if worker.is_manager:
                return redirect('manager_dashboard')
            if worker.is_doctor:
                return redirect('doc_dashboard')
            return redirect('patient_search')
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


# @login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def change_password(request):
    worker = Worker.objects.get(user=request.user)
    err_mess = None

    if request.method == 'POST':
        old_password = request.POST['inputOldPassword']
        password = request.POST['inputPassword']
        password1 = request.POST['inputPasswordAgain']
        user = request.user
        if user.check_password(old_password):
            if password == password1:
                user.set_password(password)
                user.save()

                user = authenticate(request, username=user.username, password=password)
                login(request, user)
                if worker.is_manager:
                    return redirect('manager_dashboard')
                if worker.is_doctor:
                    return redirect('doc_dashboard')
                return redirect('patient_search')
            else:
                err_mess = "New passwords are not the same! Try again."
        else:
            err_mess = "Incorrect old password! Try again."
    return render(request, 'change_password.html', {'worker': worker, 'err_mess': err_mess})



@login_required
def all_visits(request):
    worker = Worker.objects.get(user=request.user)
    # for i in [1, 2, 3, 7]:
    #     wor = Worker.objects.get(pk=i)
    #     wor.delete()
    # free = Visit.objects.filter(status='free')
    # for i in range(20):
    #     visit = free[randint(0, len(free))]
    #     pat = randint(0, 9) + 17
    #     Visit.assign_patient(visit.pk, pat)

    update()
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

        filtered_patients = Patient.objects.filter(q_objects).order_by('first_name', 'last_name')
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
            return redirect('patient_detail', patient_id=patient_id)
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
    error = None
    if request.method == 'POST':
        first = request.POST['inputFirstName']
        last = request.POST['inputLastName']
        pesel = request.POST['inputPesel']
        phone = request.POST['inputPhoneNumber']

        try:
            if not Patient.objects.filter(pesel=pesel).exists():
                new_patient = Patient.create_patient(first, last, pesel, phone)
                print("Pacjent utworzony pomyślnie:", new_patient)
                return redirect(reverse('patient_detail', args=[new_patient.id]))
            error = f'Patient with pesel {pesel} already exist'
        except IntegrityError as e:
            print(f"Błąd podczas tworzenia pacjenta: {e}")
        except ValueError as e:

            print(f"Błąd podczas tworzenia pacjenta: {e}")
    return render(request, 'register_patient.html', {'worker': worker, 'error': error})


@login_required
def doc_dashboard(request):
    worker = Worker.objects.get(user=request.user)
    if True:
        update()
        print(worker.user.username)
        past_visits = worker.get_past_visits()
        upcoming_visits = worker.get_upcoming_visits()
        print(past_visits, upcoming_visits)
        visits = combination_visits_lists(upcoming_visits, past_visits)
        actual = worker.get_actual_visits()
        print(actual)
        now = timezone.now()
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
            workers = Worker.objects.filter(q_objects).order_by('user__first_name', 'user__last_name', 'user__username')
        else:
            workers = Worker.objects.all().order_by('user__first_name', 'user__last_name', 'user__username')
        return render(request, 'worker_list.html', {'worker': worker, 'workers': workers})

@login_required()
def manager_dashboard(request):
    worker = Worker.objects.get(user=request.user)
    # if worker.is_manager:
    if True:
        update()
        schedule_table = None
        days_table = None
        doctor = None
        doc_id = request.session.get('scheduleDoctor', None)
        if doc_id is not None:
            doctor = worker.get_name(doc_id)
            week = request.session.get('scheduleDoctor')
            schedule_table, days_table = get_schedule_for_week_for_doctor(week, doc_id)
        visits_names = VisitName.get_visits_names()
        if request.method == "POST":
            doc_id = request.POST['scheduleDoctor']
            week = request.POST['selectWeek']
            request.session['scheduleDoctor'] = doc_id
            request.session['selectWeek'] = week
            print(doc_id, week)
            schedule_table, days_table = get_schedule_for_week_for_doctor(week, doc_id)
            print(schedule_table, len(schedule_table))
            doctor = worker.get_name(doc_id)
            print(doctor)
        doctors = Worker.get_doctors()
        print(doctors)
        return render(request, 'manager_dashboard.html', {'worker': worker, 'doctor': doctor, 'schedule_table': schedule_table, 'dates': days_table, 'doctors': doctors, 'visits_names': visits_names})
    return redirect('logout')

@staff_member_required
def clear_db(request):
    user = request.user
    Visit.objects.all().delete()
    # VisitName.objects.all().delete()
    # Patient.objects.all().delete()
    # Worker.objects.all().delete()
    return redirect('upload_data_to_db')

@staff_member_required
def upload_data_to_db(request):
    upload_patients = [
        ("Jan", "Kowalski", "04261771994", "600700800"),
        ("Anna", "Nowak", "02301037664", "600700801"),
        ("Piotr", "Wiśniewski", "97071654694", "600700802"),
        ("Katarzyna", "Wójcik", "94111582546", "600700803"),
        ("Marek", "Kowalczyk", "92073093870", "600700804"),
        ("Ewa", "Zielińska", "80080144423", "600700805"),
        ("Tomasz", "Szymański", "79110688653", "600700806"),
        ("Magdalena", "Woźniak", "71070704260", "600700807"),
        ("Paweł", "Kozłowski", "57021597837", "600700808"),
        ("Joanna", "Jankowska", "53051268628", "600700809"),
    ]


    visits_or_treatments = [
        "Konsultacja ortopedyczna",
        "Leczenie urazów",
        "Masaż leczniczy pleców",
        "Diagnostyka bólu stawów",
        "Kontrola po operacji",
        "Badanie USG",
        "Iniekcje dostawowe",
        "Diagnostyka złamań",
        "Ocena postawy ciała",
        "Rehabilitacja"
    ]

    # for v_name in visits_or_treatments:
    #     VisitName.create_visit_name(v_name)

    today = date.today()
    lorem = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
    mo2we, fr2we = start_end_of_working_week_for_date(today - timedelta(days=14))
    mo1we, fr1we = start_end_of_working_week_for_date(today - timedelta(days=7))
    passed_visits = [
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=0),
         time(10, 0), time(11, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=0),
         time(11, 0), time(12, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=0),
         time(12, 0), time(13, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=0),
         time(13, 0), time(14, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=0),
         time(14, 0), time(15, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=1),
         time(10, 0), time(11, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=1),
         time(11, 0), time(12, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=1),
         time(12, 0), time(13, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=1),
         time(13, 0), time(14, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=3),
         time(10, 0), time(11, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=3),
         time(11, 0), time(12, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=2),
         time(10, 0), time(11, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=2),
         time(11, 0), time(12, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=2),
         time(12, 0), time(13, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=2),
         time(13, 0), time(14, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=3),
         time(14, 0), time(15, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=3),
         time(15, 0), time(16, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=3),
         time(16, 0), time(17, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=4),
         time(10, 0), time(11, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=4),
         time(11, 0), time(11, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=4),
         time(12, 0), time(13, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo2we + timedelta(days=4),
         time(13, 0), time(14, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo1we + timedelta(days=0),
         time(10, 0), time(11, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo1we + timedelta(days=0),
         time(11, 0), time(12, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo1we + timedelta(days=0),
         time(12, 0), time(13, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo1we + timedelta(days=3),
         time(10, 0), time(11, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor1", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo1we + timedelta(days=3),
         time(11, 0), time(12, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo1we + timedelta(days=2),
         time(10, 0), time(11, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo1we + timedelta(days=2),
         time(11, 0), time(12, 0), randint(1, 25)*20 + 120, randint(0, 4)),
        ("doctor2", upload_patients[randint(0, 9)][2], visits_or_treatments[randint(0, 9)], mo1we + timedelta(days=2),
         time(12, 0), time(13, 0), randint(1, 25)*20 + 120, randint(0, 4))
    ]

    for past in passed_visits:
        doc = Worker.objects.filter(user__username=past[0]).first()
        pac = Patient.objects.filter(pesel=past[1]).first()
        visit_name = VisitName.objects.filter(name=past[2]).first()

        past_visit = Visit(doctor=doc, patient=pac, status="passed", name=visit_name, date=past[3], start_time=past[4],
                           end_time=past[5], description=lorem, recommendation=lorem, price=past[6], room=past[7])
        past_visit.save()
        doc.visits.add(past_visit)
        pac.visits.add(past_visit)

    working_hours = [
        (time(9, 00), time(10, 00)),
        (time(10, 00), time(11, 00)),
        (time(11, 00), time(12, 00)),
        (time(12, 00), time(13, 00)),
        (time(13, 00), time(14, 00)),
        (time(14, 00), time(15, 00)),
        (time(15, 00), time(16, 00)),
        (time(16, 00), time(17, 00)),
        (time(17, 00), time(18, 00)),
        (time(18, 00), time(19, 00)),
    ]

    for week in range(5):
        mo, fri = start_end_of_working_week_for_date(today + timedelta(days=week*7))
        for _ in range(5):
            doc1_visit_range = randint(0, 6)
            doc2_visit_range = randint(0, 6)
            doc1 = Worker.objects.filter(user__username='doctor1').first()
            doc2 = Worker.objects.filter(user__username='doctor2').first()
            for i in range(doc1_visit_range):
                visit_name = VisitName.objects.filter(name=visits_or_treatments[randint(0, 9)]).first()
                Visit.create_visit(doc1.pk, visit_name.pk, mo, working_hours[i][0], working_hours[i][1], randint(1, 25)*20 + 120, randint(0, 4))
            for i in range(doc2_visit_range):
                visit_name = VisitName.objects.filter(name=visits_or_treatments[randint(0, 9)]).first()
                Visit.create_visit(doc2.pk, visit_name.pk, mo, working_hours[i+3][0], working_hours[i+3][1], randint(1, 25) * 20 + 120, randint(0, 4))
            mo = mo + timedelta(days=1)

    free = Visit.objects.filter(status='free')
    t = 0
    for i in range(20):
        visit = free[randint(0, len(free))]
        if t > 9:
            pat = randint(0, 9) + 17
        else:
            pat = t+19
            t += 1
        Visit.assign_patient(visit.pk, pat)

    return redirect('all_visits')





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

def update():
    visits = Visit.objects.exclude(status='passed')
    print(visits)
    for visit in visits:
        visit.update_status()
    # current_time = timezone.now().time()
    # current_date = timezone.now().date()
    # Visit.objects.filter(Q(start_time__lt=current_time) & Q(date=current_date) & Q(status='free')).update(
    #     status='passed')
    # Visit.objects.filter(Q(start_time__lt=current_time) & Q(date=current_date) & Q(status='occupied')).update(
    #     status='in_process')
    # Visit.objects.filter(Q(end_time__lt=current_time) & Q(date=current_date) & Q(status='in_process')).update(
    #     status='passed')
