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
    def create_worker(cls, username, password, email, first_name, last_name,
                      is_doctor=False, is_receptionist=False, is_manager=False):
        user = User.objects.create_user(username=username, password=password,
                                        email=email, first_name=first_name, last_name=last_name)
        worker = cls(user=user, is_doctor=is_doctor, is_receptionist=is_receptionist, is_manager=is_manager)
        worker.save()
        return worker

    @classmethod
    def get_doctors(cls):
        return Worker.objects.filter(is_doctor=True)


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
        elif month > 10:
            year += 2100
            month -= 10
        else:
            year += 1900
        birthdate = datetime(year, month, day)

        patient = cls(first_name=first, last_name=last, birthday=birthdate, pesel=pesel, phone_number=phone)
        patient.save()
        return patient


class VisitName(models.Model):
    name = models.CharField(max_length=255, unique=True)

    @staticmethod
    def get_visits_names():
        return VisitName.objects.distinct()


class Visit(models.Model):
    STATUS_CHOICES = [
        ('free', 'Free'),
        ('occupied', 'Occupied'),
        ('passed', 'Passed'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    doctor = models.ForeignKey(Worker, on_delete=models.CASCADE, limit_choices_to={'is_doctor': True})
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='free')

    name = models.ForeignKey(VisitName, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField()
    recommendation = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    room = models.CharField(max_length=50)

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
        visit_datetime_aware = timezone.make_aware(visit_datetime)

        if visit_datetime_aware < current_datetime:
            self.status = 'passed'
            self.save()


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
        date_filter = None
        if week == 'this':
            date_filter = Q(date__range=(today, today + timedelta(days=7)))
        elif week == 'next':
            date_filter = Q(date__range=(today + timedelta(days=7), today + timedelta(days=14)))
        else:
            date_filter = Q(date__range=(today + timedelta(days=14), today + timedelta(days=21)))
        q_objects &= date_filter

        return Visit.objects.filter(q_objects).order_by('date', 'start_time')
