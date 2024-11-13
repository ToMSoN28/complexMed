from datetime import datetime, date, timedelta

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone


class Worker(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # username, password, email, first_name, last_name
    is_doctor = models.BooleanField(default=False)
    is_receptionist = models.BooleanField(default=False)
    is_manager = models.BooleanField(default=False)
    visits = models.ManyToManyField('Visit', related_name='doctor_visits', blank=True)

    @classmethod
    def username_valid(cls, username):
        return not User.objects.filter(username=username).exists()

    @classmethod
    def get_name(cls, doc_id):
        worker = Worker.objects.get(user_id=doc_id)
        return worker.user.first_name + " " + worker.user.last_name

    @classmethod
    def create_worker(cls, username, password, email, first_name, last_name,
                      is_doctor=False, is_receptionist=False, is_manager=False):
        user = User.objects.create_user(username=username, password=password,
                                        email=email, first_name=first_name, last_name=last_name)
        worker = cls(user=user, is_doctor=is_doctor, is_receptionist=is_receptionist, is_manager=is_manager)
        user.save()
        worker.save()
        return worker

    @classmethod
    def get_doctors(cls):
        return Worker.objects.filter(is_doctor=True)

    def get_past_visits(self):
        today = timezone.now().date()
        print(today)
        return self.visits.filter(date=today, status='passed').order_by('-date', '-start_time')

    def get_upcoming_visits(self):
        today = timezone.now().date()
        return self.visits.filter(Q(date=today, status='occupied') | Q(date=today, status='free')).order_by('date',
                                                                                                            'start_time')

    def get_actual_visits(self):
        return self.visits.filter(status='in_process').order_by('date', 'start_time').first()


class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birthday = models.DateTimeField()
    pesel = models.CharField(max_length=11, unique=True)
    phone_number = models.CharField(max_length=15)
    visits = models.ManyToManyField('Visit', related_name='patient_visits', blank=True)

    def get_past_visits(self):
        return self.visits.filter(status='passed').order_by('-date', '-start_time')

    def get_upcoming_visits(self):
        return self.visits.filter(status='occupied').order_by('date', 'start_time')

    @classmethod
    def create_patient(cls, first, last, pesel, phone):
        if cls.objects.filter(pesel=pesel).exists():
            raise ValueError("Pacjent o tym numerze PESEL już istnieje.")
        year = int(pesel[0:2])
        month = int(pesel[2:4])
        day = int(pesel[4:6])
        if month > 20:
            year += 2000
            month -= 20
        elif month > 40:
            year += 2100
            month -= 40
        elif month > 60:
            year += 2200
            month -= 60
        else:
            year += 1900
        birthdate = datetime(year, month, day)

        patient = cls(first_name=first, last_name=last, birthday=birthdate, pesel=pesel, phone_number=phone)
        patient.save()
        return patient


class VisitName(models.Model):
    name = models.CharField(max_length=255, unique=True)

    @classmethod
    def create_visit_name(cls, name):
        if not cls.objects.filter(name=name).exists() and len(name) != 0:
            v_name = cls(name=name)
            v_name.save()
        else:
            print('This name already exist of len 0')

    @staticmethod
    def get_visits_names():
        return VisitName.objects.distinct()


class Visit(models.Model):
    STATUS_CHOICES = [
        ('free', 'Free'),
        ('occupied', 'Occupied'),
        ('passed', 'Passed'),
        ('in_process', 'In_Process'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    doctor = models.ForeignKey(Worker, on_delete=models.CASCADE, limit_choices_to={'is_doctor': True})
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='free')

    name = models.ForeignKey(VisitName, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(null=True, blank=True)
    recommendation = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    room = models.CharField(max_length=50)

    @classmethod
    def create_visit(cls, doc_id, name_id, date, start, end, price, room):
        doc = Worker.objects.get(pk=doc_id)
        name = VisitName.objects.get(pk=name_id)
        if True:  # dodac czy wtedy ten lekarz jest wolny
            # błędy o przeminiętej dodanej
            visit = cls(doctor=doc, name=name, date=date, start_time=start, end_time=end, price=price, room=room)
            visit.save()
            doc.visits.add(visit)
        else:
            print('termin zajęty, zwrócić wizytę która blokuje?')

    def delete_visit(self):
        self.delete()

    def cancel_visit(self):
        if self.status == 'occupied':
            self.status = 'free'
            self.patient.visits.remove(self)
            self.patient = None
            self.save()
            return True
        return False

    @classmethod
    def assign_patient(cls, visit_id, patient_id):
        try:
            visit = cls.objects.get(pk=visit_id)
            patient = Patient.objects.get(pk=patient_id)

            if visit.status == 'free':
                visit.patient = patient
                patient.visits.add(visit)
                visit.status = 'occupied'
                visit.save()
                return True
            else:
                return False
        except (cls.DoesNotExist, Patient.DoesNotExist):
            return False

    @classmethod
    def edit_by_doctor(cls, visit_id, doctor_id, progress, results):
        try:
            visit = cls.objects.get(pk=visit_id)
            doctor = Worker.objects.get(pk=doctor_id)

            if visit.doctor == doctor:
                visit.progress = progress
                visit.results = results
                visit.save()
                return True
            else:
                return False
        except (cls.DoesNotExist, Worker.DoesNotExist):
            return False

    def update_status(self):
        current_datetime = timezone.now()
        visit_datetime = datetime.combine(self.date, self.start_time)
        visit_datetime_start = timezone.make_aware(visit_datetime)

        visit_datetime = datetime.combine(self.date, self.end_time)
        visit_datetime_end = timezone.make_aware(visit_datetime)
        # print(current_datetime)
        # print(visit_datetime_start)
        # print(visit_datetime_end)
        # print(visit_datetime_start < current_datetime and self.status != 'passed')
        if visit_datetime_start < current_datetime and self.status != 'passed':
            if self.status == 'free':
                self.status = 'passed'
            if self.status == 'occupied':
                self.status = 'in_process'
            # print(self.status)
            self.save()
        # print(visit_datetime_end <= current_datetime and self.status != 'passed')
        if visit_datetime_end <= current_datetime and self.status != 'passed':
            self.status = 'passed'
            # print(self.status)
            self.save()
        # print(self.status)

    @classmethod
    def get_available_visits(cls, v_name, d_id, week):
        # print(v_name, d_id, week)
        # print(type(v_name), type(d_id), type(week))
        q_objects = Q(status='free')
        if int(v_name) != 0:
            q_objects &= Q(name__id=v_name)
        if int(d_id) != 0:
            q_objects &= Q(doctor__user__id=d_id)

        today = date.today()
        day_num = today.weekday()
        today = today - timedelta(days=day_num)
        date_filter = None
        if week == 'this':
            date_filter = Q(date__range=(today, today + timedelta(days=6)))
        elif week == 'next':
            date_filter = Q(date__range=(today + timedelta(days=7), today + timedelta(days=13)))
        else:
            date_filter = Q(date__range=(today + timedelta(days=14), today + timedelta(days=20)))
        q_objects &= date_filter

        return Visit.objects.filter(q_objects).order_by('date', 'start_time')

    @classmethod
    def gat_all_visits_for_doctor_for_date(cls, doctor_id, date_visit):
        q_objects = Q(doctor__user__id=doctor_id, date=date_visit)
        return Visit.objects.filter(q_objects).order_by('start_time')

