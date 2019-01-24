from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .decorators import lecturer_required, student_required
from .forms import *
from .models import User, Student, Course, CourseAllocation, TakenCourse, Session, Semester, CarryOverStudent, RepeatingStudent
from django.views.generic import CreateView, UpdateView, DeleteView
from django.utils.decorators import method_decorator
from django.contrib.auth import update_session_auth_hash, authenticate
from django.contrib.auth.forms import PasswordChangeForm
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib import messages
#pdf
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, black, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY,TA_LEFT,TA_CENTER,TA_RIGHT
from reportlab.platypus.tables import Table
from reportlab.lib.units import inch
from reportlab.lib import colors
cm = 2.54

from ARMS.settings import MEDIA_ROOT, BASE_DIR, STATIC_URL
import os



@login_required
def home(request):
    """ 
    Shows our dashboard containing number of students, courses, lecturers, repating students, 
    carry over students and 1st class students in an interactive graph

    """
    students = Student.objects.all().count()
    staff = User.objects.filter(is_lecturer=True).count()
    courses = Course.objects.all().count()
    current_semester = Semester.objects.get(is_current_semester=True)
    no_of_1st_class_students = Result.objects.filter(cgpa__gte=4.5).count()
    no_of_carry_over_students = CarryOverStudent.objects.all().count()
    no_of_students_to_repeat = RepeatingStudent.objects.all().count()

    context = {
        "no_of_students": students,
        "no_of_staff":staff,
        "no_of_courses": courses,
        "no_of_1st_class_students": no_of_1st_class_students,
        "no_of_students_to_repeat": no_of_students_to_repeat,
        "no_of_carry_over_students": no_of_carry_over_students,
    }

    return render(request, 'result/home.html', context)

def get_chart(request, *args, **kwargs):
    all_query_score = ()
    levels = (100, 200, 300, 400, 500) # all the levels in the department

    # iterate through the levels above
    for i in levels:
    	# gather all the courses registered by the students of the current level in the loop
        all_query_score += (TakenCourse.objects.filter(student__level=i),)

    # for level #100 
    first_level_total = 0

    # get the total score for all the courses registered by the students of this level
    for i in all_query_score[0]:
        first_level_total += i.total
    
    first_level_avg = 0
    if not all_query_score[0].count() == 0:
    	# calculate the average of all the students of this level
        first_level_avg = first_level_total / all_query_score[0].count()

    # do same  as above for # 200 Level students
    second_level_total = 0
    for i in all_query_score[1]:
        second_level_total += i.total
    second_level_avg = 0
    if not all_query_score[1].count() == 0:
        second_level_avg = second_level_total / all_query_score[1].count()

    # do same  as above for # 300 Level students
    third_level_total = 0
    for i in all_query_score[2]:
        third_level_total += i.total
    third_level_avg = 0
    if not all_query_score[2].count() == 0:
        third_level_avg = third_level_total / all_query_score[2].count()

    # do same  as above for # 400 Level students
    fourth_level_total = 0
    for i in all_query_score[3]:
        fourth_level_total += i.total
    fourth_level_avg = 0
    if not all_query_score[3].count() == 0:
        fourth_level_avg = fourth_level_total / all_query_score[3].count()

    # do same  as above for # 500 Level students
    fifth_level_total = 0
    for i in all_query_score[4]:
        fifth_level_total += i.total
    fifth_level_avg = 0
    if not all_query_score[4].count() == 0:
        fifth_level_avg = fifth_level_total / all_query_score[4].count()

    labels = ["100 Level", "200 Level", "300 Level", "400 Level", "500 Level"]
    default_level_average = [first_level_avg, second_level_avg, third_level_avg, fourth_level_avg, fifth_level_avg]
    average_data = {
        "labels": labels,
        "default_level_average": default_level_average,
    }
    return JsonResponse(average_data)


@login_required
def profile(request):
    """ Show profile of any user that fire out the request """
    current_semester = Semester.objects.get(is_current_semester=True)
    if request.user.is_lecturer:
        courses = Course.objects.filter(allocated_course__lecturer__pk=request.user.id).filter(semester=current_semester)
        return render(request, 'account/profile.html', {"courses": courses,})
    elif request.user.is_student:
        level = Student.objects.get(user__pk=request.user.id)
        courses = TakenCourse.objects.filter(student__user__id=request.user.id, course__level=level.level)
        context = {
        'courses': courses,
        'level': level,
        }
        return render(request, 'account/profile.html', context)
    else:
        staff = User.objects.filter(is_lecturer=True)
        return render(request, 'account/profile.html', { "staff": staff })

@login_required
def user_profile(request, id):
    """ Show profile of any selected user """
    if request.user.id == id:
        return redirect("/profile/")

    current_semester = Semester.objects.get(is_current_semester=True)
    user = User.objects.get(pk=id)
    if user.is_lecturer:
        courses = Course.objects.filter(allocated_course__lecturer__pk=id).filter(semester=current_semester)
        context = {
            "user": user,
            "courses": courses,
            }
        return render(request, 'account/user_profile.html', context)
    elif user.is_student:
        level = Student.objects.get(user__pk=id)
        courses = TakenCourse.objects.filter(student__user__id=id, course__level=level.level)
        context = {
            "user_type": "student",
            'courses': courses,
            'level': level,
            'user':user,
        }
        return render(request, 'account/user_profile.html', context)
    else:
        context = {
            "user": user,
            "user_type": "superuser"
            }
        return render(request, 'account/user_profile.html', context)

@login_required
def profile_update(request):
    """ Check if the fired request is a POST then grap changes and update the records otherwise we show an empty form """
    user = request.user.id
    user = User.objects.get(pk=user)
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.email = form.cleaned_data.get('email')
            user.phone = form.cleaned_data.get('phone')
            user.address = form.cleaned_data.get('address')
            if request.FILES:
                user.picture = request.FILES['picture']
            user.save()
            messages.success(request, 'Your profile was successfully edited.')
            return redirect("/profile/")
    else:
        form = ProfileForm(instance=user, initial={
            'firstname': user.first_name,
            'lastname': user.last_name,
            'email': user.email,
            'phone': user.phone,
            'picture': user.picture,
            })

    return render(request, 'account/profile_update.html', {'form': form})


@login_required
@lecturer_required
def course_list(request):
    """ Show list of all registered courses in the system """
    courses = Course.objects.all()
    context = {
        "courses":courses,
        }
    return render(request, 'course/course_list.html', context)

@login_required
@lecturer_required
def student_list(request):
    """ Show list of all registered students in the system """
    students = Student.objects.all()
    user_type = "Student"
    context = {
        "students": students, 
        "user_type": user_type,
        }
    return render(request, 'students/student_list.html', context)

@login_required
@lecturer_required
def staff_list(request):
    """ Show list of all registered staff """
    staff = User.objects.filter(is_student=False)
    user_type = "Staff"
    context = {
        "staff": staff, 
        "user_type": user_type,
        }
    return render(request, 'staff/staff_list.html', context)


@login_required
@lecturer_required
def session_list_view(request):
    """ Show list of all sessions """
    sessions = Session.objects.all().order_by('-session')
    return render(request, 'result/manage_session.html', {"sessions": sessions,})

@login_required
@lecturer_required
def session_add_view(request):
    """ check request method, if POST we add session otherwise show empty form """
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Session added successfully ! ')

    else:
        form = SessionForm()
    return render(request, 'result/session_update.html', {'form': form})

@login_required
@lecturer_required
def session_update_view(request, pk):
    session = Session.objects.get(pk=pk)
    if request.method == 'POST':
        a = request.POST.get('is_current_session')
        if a == '2':
            unset = Session.objects.get(is_current_session=True)
            unset.is_current_session = False
            unset.save()
            form = SessionForm(request.POST, instance=session)
            if form.is_valid():
                form.save()
                messages.success(request, 'Session updated successfully ! ')
        else:
            form = SessionForm(request.POST, instance=session)
            if form.is_valid():
                form.save()
                messages.success(request, 'Session updated successfully ! ')

    else:
        form = SessionForm(instance=session)
    return render(request, 'result/session_update.html', {'form': form})

@login_required
@lecturer_required
def session_delete_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if session.is_current_session == True:
    	messages.info(request, "You cannot delete current session")
    	return redirect('manage_session')
    else:
    	session.delete()
    	messages.success(request, "Session successfully deleted")
    return redirect('manage_semester')

@login_required
@lecturer_required
def semester_list_view(request):
    semesters = Semester.objects.all().order_by('-semester')
    return render(request, 'result/manage_semester.html', {"semesters": semesters,})

@login_required
@lecturer_required
def semester_add_view(request):
    if request.method == 'POST':
        form = SemesterForm(request.POST)
        if form.is_valid():
            data = form.data.get('is_current_semester') # returns string of 'True' if the user selected Yes
            if data == 'True':
            	semester = form.data.get('semester')
            	ss = form.data.get('session')
            	session = Session.objects.get(pk=ss)
            	try:
            		if Semester.objects.get(semester=semester, session=ss):
	            		messages.info(request, semester + " semester in " + session.session +" session already exist")
	            		return redirect('create_new_semester')
            	except:
	            	semester = Semester.objects.get(is_current_semester=True)
	            	semester.is_current_semester = False
	            	semester.save()
	            	form.save()
            form.save()
            messages.success(request, 'Semester added successfully ! ')
            return redirect('manage_semester')
    else:
        form = SemesterForm()
    return render(request, 'result/semester_update.html', {'form': form})

@login_required
@lecturer_required
def semester_update_view(request, pk):
    semester = Semester.objects.get(pk=pk)
    if request.method == 'POST':
        if request.POST.get('is_current_semester') == 'True': # returns string of 'True' if the user selected yes for 'is current semester'
            unset_semester = Semester.objects.get(is_current_semester=True)
            unset_semester.is_current_semester = False
            unset_semester.save()
            unset_session = Session.objects.get(is_current_session=True)
            unset_session.is_current_session = False
            unset_session.save()
            new_session = request.POST.get('session')
            form = SemesterForm(request.POST, instance=semester)
            if form.is_valid():
            	set_session = Session.objects.get(pk=new_session)
            	set_session.is_current_session = True
            	set_session.save()
            	form.save()
            	messages.success(request, 'Semester updated successfully !')
            	return redirect('manage_semester')
        else:
            form = SemesterForm(request.POST, instance=semester)
            if form.is_valid():
                form.save()
                return redirect('manage_semester')

    else:
        form = SemesterForm(instance=semester)
    return render(request, 'result/semester_update.html', {'form': form})

@login_required
@lecturer_required
def semester_delete_view(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    if semester.is_current_semester == True:
    	messages.info(request, "You cannot delete current semester")
    	return redirect('manage_semester')
    else:
    	semester.delete()
    	messages.success(request, "Semester successfully deleted")
    return redirect('manage_semester')


@method_decorator([login_required, lecturer_required], name='dispatch')
class StaffAddView(CreateView):
    model = User
    form_class = StaffAddForm
    template_name = 'registration/add_staff.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'staff'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        return redirect('staff_list')

@login_required
@lecturer_required
def edit_staff(request, pk):
    staff = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = StaffAddForm(request.POST, instance=staff)
        if form.is_valid():
            staff.save()
            return redirect('staff_list')
    else:
        form = StaffAddForm(instance=staff)
    return render(request, 'registration/edit_staff.html', {'form': form})

@login_required
@lecturer_required
def delete_staff(request, pk):
    staff = get_object_or_404(User, pk=pk)
    staff.delete()
    return redirect('staff_list')

@method_decorator([login_required, lecturer_required], name='dispatch')
class StudentAddView(CreateView):
    model = User
    form_class = StudentAddForm
    template_name = 'registration/add_student.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'student'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        return redirect('student_list')

@login_required
@lecturer_required
def edit_student(request, pk):
	student = get_object_or_404(Student, pk=pk)
	if request.method == "POST":
		form = StudentAddForm(request.POST, instance=student)
		if form.is_valid():
			form.save()
			return redirect('student_list')
	else:
		form = StudentAddForm(instance=student)
	return render(request, 'registration/edit_student.html', {'form': form})

@login_required
@lecturer_required
def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    student.delete()
    return redirect('student_list')


@method_decorator([login_required, lecturer_required], name='dispatch')
class CourseAddView(CreateView):
    model = Course
    form_class = CourseAddForm
    template_name = 'course/course_form.html'


    def form_valid(self, form):
        form.save()
        return redirect('course_allocation')

@login_required
@lecturer_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseAddForm(request.POST, instance=course)
        if form.is_valid():
            course.save()
            messages.success(request, "Successfully Updated")
            return redirect('course_list')
    else:
        form = CourseAddForm(instance=course)
    return render(request, 'course/course_form.html', {'form': form})

@method_decorator([login_required, lecturer_required], name='dispatch')
class CourseAllocationView(CreateView):
    form_class = CourseAllocationForm
    template_name = 'course/course_allocation.html'

    def get_form_kwargs(self):
        kwargs = super(CourseAllocationView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # if a staff has been allocated a course before update it else create new
        lecturer = form.cleaned_data['lecturer']
        selected_courses = form.cleaned_data['courses']
        courses = ()
        for course in selected_courses:
            courses += (course.pk,)
        print(courses)

        try:
            a = CourseAllocation.objects.get(lecturer=lecturer)
        except:
            a = CourseAllocation.objects.create(lecturer=lecturer)
        for i in range(0, selected_courses.count()):
            a.courses.add(courses[i])
            a.save()
        return redirect('course_allocation_view')


@login_required
@student_required
def course_registration(request):
    if request.method == 'POST':
        ids = ()
        data = request.POST.copy()
        data.pop('csrfmiddlewaretoken', None) # remove csrf_token
        for key in data.keys():
            ids = ids + (str(key),)
        for s in range(0,len(ids)):
            student = Student.objects.get(user__pk=request.user.id)
            course = Course.objects.get(pk=ids[s])
            obj = TakenCourse.objects.create(student=student, course=course)
            obj.save()
            messages.success(request, 'Courses Registered Successfully!')
        return redirect('course_registration')
    else:
        student = Student.objects.get(user__pk=request.user.id)
        taken_courses = TakenCourse.objects.filter(student__user__id=request.user.id)
        t = ()
        for i in taken_courses:
            t += (i.course.pk,)
        current_semester = Semester.objects.get(is_current_semester=True)
        courses = Course.objects.filter(level=student.level).exclude(id__in=t)
        all_courses = Course.objects.filter(level=student.level)

        no_course_is_registered = False # Check if no course is registered
        all_courses_are_registered = False

        registered_courses = Course.objects.filter(level=student.level).filter(id__in=t)
        if registered_courses.count() == 0: # Check if number of registered courses is 0
        	no_course_is_registered = True

        if registered_courses.count() == all_courses.count():
        	all_courses_are_registered = True

        total_first_semester_unit = 0
        total_sec_semester_unit = 0
        total_registered_unit = 0
        for i in courses:
            if i.semester == "First":
                total_first_semester_unit += int(i.courseUnit)
            if i.semester == "Second":
                total_sec_semester_unit += int(i.courseUnit)
        for i in registered_courses:
            total_registered_unit += int(i.courseUnit)
        context = {
        		"all_courses_are_registered": all_courses_are_registered,
        		"no_course_is_registered": no_course_is_registered,
                "current_semester":current_semester, 
                "courses":courses, 
                "total_first_semester_unit": total_first_semester_unit,
                "total_sec_semester_unit": total_sec_semester_unit,
                "registered_courses": registered_courses,
                "total_registered_unit": total_registered_unit,
                "student": student,
                }
        return render(request, 'course/course_registration.html', context)

@login_required
@student_required
def course_drop(request):
    if request.method == 'POST':
        ids = ()
        data = request.POST.copy()
        data.pop('csrfmiddlewaretoken', None) # remove csrf_token
        for key in data.keys():
            ids = ids + (str(key),)
        for s in range(0,len(ids)):
            student = Student.objects.get(user__pk=request.user.id)
            course = Course.objects.get(pk=ids[s])
            obj = TakenCourse.objects.get(student=student, course=course)
            obj.delete()
            messages.success(request, 'Successfully Dropped!')
        return redirect('course_registration')

@login_required
@lecturer_required
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    course.delete()
    messages.success(request, 'Deleted successfully!')
    return redirect('course_list')

@login_required
@lecturer_required 
def add_score(request):
    """ 
    Shows a page where a lecturer will select a course allocated to him for score entry.
    in a specific semester and session 

    """
    current_session = Session.objects.get(is_current_session=True)
    current_semester = get_object_or_404(Semester, is_current_semester=True, session=current_session)
    semester = Course.objects.filter(allocated_course__lecturer__pk=request.user.id, semester=current_semester)
    courses = Course.objects.filter(allocated_course__lecturer__pk=request.user.id).filter(semester=current_semester)
    context = {
    "courses": courses,
    }
    return render(request, 'result/add_score.html', context)

@login_required
@lecturer_required 
def add_score_for(request, id):
    """ 
    Shows a page where a lecturer will add score for studens that are taking courses allocated to him
    in a specific semester and session 
    """
    current_semester = Semester.objects.get(is_current_semester=True)
    if request.method == 'GET':
        courses = Course.objects.filter(allocated_course__lecturer__pk=request.user.id).filter(semester=current_semester)
        course = Course.objects.get(pk=id)
        students = TakenCourse.objects.filter(course__allocated_course__lecturer__pk=request.user.id).filter(course__id=id).filter(course__semester=current_semester)
        context = {
        "courses":courses, 
        "course": course, 
        "students":students,
        }
        return render(request, 'result/add_score_for.html', context)

    if request.method == 'POST':
        ids = ()
        data = request.POST.copy()
        data.pop('csrfmiddlewaretoken', None) # remove csrf_token
        for key in data.keys():
            ids = ids + (str(key),)      # gather all the all students id (i.e the keys) in a tuple
        for s in range(0,len(ids)):      # iterate over the list of student ids gathered above
            student = TakenCourse.objects.get(id=ids[s])
            courses = Course.objects.filter(level=student.student.level).filter(semester=current_semester) # all courses of a specific level in current semester
            total_unit_in_semester = 0
            for i in courses:
                if i == courses.count():
                    break
                else:
                   total_unit_in_semester += int(i.courseUnit)
            score = data.getlist(ids[s]) # get list of score for current student in the loop
            ca = score[0]                # subscript the list to get the fisrt value > ca score
            exam = score[1]              # do thesame for exam score
            obj = TakenCourse.objects.get(pk=ids[s]) # get the current student data
            obj.ca = ca # set current student ca score
            obj.exam = exam # set current student exam score
            obj.total = obj.get_total(ca=ca,exam=exam)
            obj.grade = obj.get_grade(ca=ca,exam=exam)
            obj.comment = obj.get_comment(obj.grade)
            obj.carry_over(obj.grade)
            obj.is_repeating()
            obj.save()
            gpa = obj.calculate_gpa(total_unit_in_semester)
            cgpa = obj.calculate_cgpa()
            try:
                a = Result.objects.get(student=student.student, semester=current_semester, level=student.student.level)
                a.gpa = gpa
                a.cgpa = cgpa
                a.save()
            except:
                Result.objects.get_or_create(student=student.student, gpa=gpa, semester=current_semester, level=student.student.level)
        messages.success(request, 'Successfully Recorded! ')
        return HttpResponseRedirect(reverse_lazy('add_score_for', kwargs={'id': id}))
    return HttpResponseRedirect(reverse_lazy('add_score_for', kwargs={'id': id}))

@login_required
@student_required
def view_result(request):
    student = Student.objects.get(user__pk=request.user.id)
    current_semester = Semester.objects.get(is_current_semester=True)
    courses = TakenCourse.objects.filter(student__user__pk=request.user.id, course__level=student.level)
    result = Result.objects.filter(student__user__pk=request.user.id)
    current_semester_grades = {}

    previousCGPA = 0
    previousLEVEL = 0

    for i in result:
        if not int(i.level) - 100 == 0: # TODO think n check the logic
            previousLEVEL = i.level
            try:
                a = Result.objects.get(student__user__pk=request.user.id, level=previousLEVEL, semester="Second")
                previousCGPA = a.cgpa
                break
            except:
                previousCGPA = 0
        else:
            break
    context = {
            "courses": courses, 
            "result":result, 
            "student": student, 
            "previousCGPA": previousCGPA,
            }

    return render(request, 'students/view_results.html', context)

@login_required
def change_password(request):
	if request.method == 'POST':
		form = PasswordChangeForm(request.user, request.POST)
		if form.is_valid():
			user = form.save()
			update_session_auth_hash(request, user)
			messages.success(request, 'Your password was successfully updated!')
		else:
			messages.error(request, 'Please correct the errors below. ')
	else:
		form = PasswordChangeForm(request.user)
	return render(request, 'account/change_password.html', {
		'form': form,
        })


@login_required
@lecturer_required
def course_allocation_view(request):
    allocated_courses = CourseAllocation.objects.all()
    return render(request, 'course/course_allocation_view.html', {"allocated_courses": allocated_courses})

@login_required
@lecturer_required
def withheld_course(request, pk):
    course = CourseAllocation.objects.get(pk=pk)
    course.delete()
    messages.success(request, 'successfully deallocated!')
    return redirect("course_allocation_view")


@login_required
def carry_over(request):
    if request.method == "POST":
        value = ()
        data = request.POST.copy()
        data.pop('csrfmiddlewaretoken', None) # remove csrf_token
        for val in data.values():
            value += (val,)
        course = value[0]
        session = value[1]
        courses = CarryOverStudent.objects.filter(course__courseCode=course, session=session)
        all_courses = Course.objects.all()
        sessions = Session.objects.all()
        signal_template = True
        context = {
                    "all_courses": all_courses,
                    "courses": courses,
                    "signal_template": signal_template, 
                    "sessions":sessions 
        }
        return render(request, 'course/carry_over.html', context)
    else:
        all_courses = Course.objects.all()
        sessions = Session.objects.all()
        return render(request, 'course/carry_over.html',  { "all_courses": all_courses, "sessions":sessions })


@login_required
def repeat_list(request):
    students = RepeatingStudent.objects.all()
    return render(request, 'students/repeaters.html', {"students": students})

@login_required
def first_class_list(request):
    students = Result.objects.filter(cgpa__gte=4.5)
    return render(request, 'students/first_class_students.html', {"students": students})

@login_required
@lecturer_required
def result_sheet_pdf_view(request, id):
    current_semester = Semester.objects.get(is_current_semester=True)
    current_session = Session.objects.get(is_current_session=True)
    result = TakenCourse.objects.filter(course__pk=id)
    no_of_pass = TakenCourse.objects.filter(course__pk=id, comment="PASS").count()
    no_of_fail = TakenCourse.objects.filter(course__pk=id, comment="FAIL").count()
    fname = str(current_semester) + '_semester_' + str(current_session) + '_session_' + 'resultSheet.pdf'
    fname = fname.replace("/", "-")
    flocation = '/tmp/'+fname

    doc = SimpleDocTemplate(flocation, rightMargin=0, leftMargin=6.5 * cm, topMargin=0.3 * cm, bottomMargin=0)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle( name="ParagraphTitle", fontSize=11, fontName="FreeSansBold"))
    Story = [Spacer(1,.2)]
    style = styles["Normal"]

    logo = MEDIA_ROOT + "/logo/android-chrome-144x144.png"
    print(logo)
    im = Image(logo, 1*inch, 1*inch)
    im.__setattr__("_offs_x", -280)
    im.__setattr__("_offs_y", -45)
    Story.append(im)
    
    style = getSampleStyleSheet()
    normal = style["Normal"]
    normal.alignment = TA_CENTER
    normal.fontName = "Helvetica"
    normal.fontSize = 12
    normal.leading = 15
    title = "<b> "+str(current_semester) + " Semester " + str(current_session) + " Result Sheet</b>" 
    title = Paragraph(title.upper(), normal)
    Story.append(title)
    Story.append(Spacer(1,0.1*inch))

    style = getSampleStyleSheet()
    normal = style["Normal"]
    normal.alignment = TA_CENTER
    normal.fontName = "Helvetica"
    normal.fontSize = 10
    normal.leading = 15
    title = "<b>Course lecturer: " + request.user.get_full_name() + "</b>"
    title = Paragraph(title.upper(), normal)
    Story.append(title)
    Story.append(Spacer(1,0.1*inch))

    normal = style["Normal"]
    normal.alignment = TA_CENTER
    normal.fontName = "Helvetica"
    normal.fontSize = 10
    normal.leading = 15
    level = result.filter(course_id=id).first()
    title = "<b>Level: </b>" + str(level.course.level+"L")
    title = Paragraph(title.upper(), normal)
    Story.append(title)
    Story.append(Spacer(1,.6*inch))
    
    elements = []
    count = 0
    header = [('S/N', 'ID NUMBER', 'CA', 'EXAM', 'GRADE', 'COMMENT')]
    table_header=Table(header,1*[1.2*inch], 1*[0.5*inch])
    table_header.setStyle(
    	TableStyle([
    		('ALIGN',(-2,-2), (-2,-2),'CENTER'),
    		('TEXTCOLOR',(1,0),(1,0),colors.blue),
    		('TEXTCOLOR',(-1,0),(-1,0),colors.blue),
    		('ALIGN',(0,-1),(-1,-1),'CENTER'),
    		('VALIGN',(0,-1),(-1,-1),'MIDDLE'),
    		('TEXTCOLOR',(0,-1),(-1,-1),colors.blue),
    		('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
    		('BOX', (0,0), (-1,-1), 0.25, colors.black),
    		]))
    Story.append(table_header)
    for student in result:
    	data = [(count+1, student.student.id_number.upper(), student.ca, student.exam, student.grade, student.comment)]
    	color = colors.black
    	if student.grade == 'F':
    		color = colors.red
    	count += 1
    	t=Table(data,1*[1.2*inch], 1*[0.5*inch])
    	t.setStyle(
    		TableStyle([
	    		('ALIGN',(-2,-2), (-2,-2),'CENTER'),
	    		('ALIGN',(1,0), (1,0),'CENTER'),
	    		('ALIGN',(-1,0), (-1,0),'CENTER'),
	    		('ALIGN',(-3,0), (-3,0),'CENTER'),
	    		('ALIGN',(-4,0), (-4,0),'CENTER'),
	    		('ALIGN',(-6,0), (-6,0),'CENTER'),
	    		('TEXTCOLOR',(0,-1),(-1,-1),color),
	    		('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
	    		('BOX', (0,0), (-1,-1), 0.25, colors.black),
	    		]))
    	Story.append(t)

    Story.append(Spacer(1,1*inch))
    style_right = ParagraphStyle(name='right', parent=styles['Normal'], alignment=TA_RIGHT)
    tbl_data = [
    [Paragraph("<b>Date:</b>_______________________________________", styles["Normal"]), Paragraph("<b>No. of PASS:</b> " + str(no_of_pass), style_right)],
    [Paragraph("<b>Siganture / Stamp:</b> _____________________________", styles["Normal"]), Paragraph("<b>No. of FAIL: </b>" + str(no_of_fail), style_right)]]
    tbl = Table(tbl_data)
    Story.append(tbl)

    doc.build(Story)

    fs = FileSystemStorage("/tmp")
    with fs.open(fname) as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename='+fname+''
        return response
    return response


@login_required
@student_required
def course_registration_form(request):
    current_semester = Semester.objects.get(is_current_semester=True)
    current_session = Session.objects.get(is_current_session=True)
    courses = TakenCourse.objects.filter(student__user__id=request.user.id)
    fname = request.user.username + '.pdf'
    fname = fname.replace("/", "-")
    flocation = '/tmp/'+fname
    doc = SimpleDocTemplate(flocation, rightMargin=15, leftMargin=15, topMargin=0, bottomMargin=0)
    styles = getSampleStyleSheet()

    Story = [Spacer(1,0.5)]
    Story.append(Spacer(1,0.4*inch))
    style = styles["Normal"]

    style = getSampleStyleSheet()
    normal = style["Normal"]
    normal.alignment = TA_CENTER
    normal.fontName = "Helvetica"
    normal.fontSize = 12
    normal.leading = 18
    title = "<b>MODIBBO ADAMA UNIVERSITY OF TECHNOLOGY, YOLA</b>" 
    title = Paragraph(title.upper(), normal)
    Story.append(title)
    style = getSampleStyleSheet()
    
    school = style["Normal"]
    school.alignment = TA_CENTER
    school.fontName = "Helvetica"
    school.fontSize = 10
    school.leading = 18
    school_title = "<b>SCHOOL OF MANAGEMENT AND INFORMATION TECHNOLOGY</b>"
    school_title = Paragraph(school_title.upper(), school)
    Story.append(school_title)

    style = getSampleStyleSheet()
    Story.append(Spacer(1,0.1*inch))
    department = style["Normal"]
    department.alignment = TA_CENTER
    department.fontName = "Helvetica"
    department.fontSize = 9
    department.leading = 18
    department_title = "<b>DEPARTMENT OF INFORMATION MANAGEMENT TECHNOLOGY</b>"
    department_title = Paragraph(department_title, department)
    Story.append(department_title)
    Story.append(Spacer(1,.3*inch))
    
    title = "<b><u>STUDENT REGISTRATION FORM</u></b>"
    title = Paragraph(title.upper(), normal)
    Story.append(title)
    student = Student.objects.get(user__pk=request.user.id)

    style_right = ParagraphStyle(name='right', parent=styles['Normal'])
    tbl_data = [
        [Paragraph("<b>Registration Number : " + request.user.username.upper() + "</b>", styles["Normal"])],
        [Paragraph("<b>Name : " + request.user.get_full_name().upper() + "</b>", styles["Normal"])],
        [Paragraph("<b>Session : " + current_session.session.upper() + "</b>", styles["Normal"]), Paragraph("<b>Level: " + student.level + "</b>", styles["Normal"])
        ]]
    tbl = Table(tbl_data)
    Story.append(tbl)
    Story.append(Spacer(1, 0.6*inch))

    style = getSampleStyleSheet()
    semester = style["Normal"]
    semester.alignment = TA_LEFT
    semester.fontName = "Helvetica"
    semester.fontSize = 9
    semester.leading = 18
    semester_title = "<b>FIRST SEMESTER</b>"
    semester_title = Paragraph(semester_title, semester)
    Story.append(semester_title)

    elements = []

    # FIRST SEMESTER
    count = 0
    header = [('S/No', 'Course Code', 'Course Title', 'Unit', Paragraph('Name, Siganture of course lecturer & Date', style['Normal']))]
    table_header = Table(header,1*[1.4*inch], 1*[0.5*inch])
    table_header.setStyle(
        TableStyle([
                ('ALIGN',(-2,-2), (-2,-2),'CENTER'),
                ('VALIGN',(-2,-2), (-2,-2),'MIDDLE'),
                ('ALIGN',(1,0), (1,0),'CENTER'),
                ('VALIGN',(1,0), (1,0),'MIDDLE'),
                ('ALIGN',(0,0), (0,0),'CENTER'),
                ('VALIGN',(0,0), (0,0),'MIDDLE'),
                ('ALIGN',(-4,0), (-4,0),'LEFT'),
                ('VALIGN',(-4,0), (-4,0),'MIDDLE'),
                ('ALIGN',(-3,0), (-3,0),'LEFT'),
                ('VALIGN',(-3,0), (-3,0),'MIDDLE'),
                ('TEXTCOLOR',(0,-1),(-1,-1),colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                ('BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
    Story.append(table_header)

    first_semester_unit = 0
    for course in courses:
        if course.course.semester == FIRST:
            first_semester_unit += int(course.course.courseUnit)
            data = [(count+1, course.course.courseCode.upper(), course.course.courseTitle, course.course.courseUnit, '')]
            color = colors.black
            count += 1
            table_body=Table(data,1*[1.4*inch], 1*[0.3*inch])
            table_body.setStyle(
                TableStyle([
                    ('ALIGN',(-2,-2), (-2,-2),'CENTER'),
                    ('ALIGN',(1,0), (1,0),'CENTER'),
                    ('ALIGN',(0,0), (0,0),'CENTER'),
                    ('ALIGN',(-4,0), (-4,0),'LEFT'),
                    ('TEXTCOLOR',(0,-1),(-1,-1),colors.black),
                    ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                    ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                    ]))
            Story.append(table_body)

    style = getSampleStyleSheet()
    semester = style["Normal"]
    semester.alignment = TA_LEFT
    semester.fontName = "Helvetica"
    semester.fontSize = 8
    semester.leading = 18
    semester_title = "<b>Total Units : " + str(first_semester_unit) + "</b>"
    semester_title = Paragraph(semester_title, semester)
    Story.append(semester_title)

    # FIRST SEMESTER ENDS HERE
    Story.append(Spacer(1, 0.6*inch))

    style = getSampleStyleSheet()
    semester = style["Normal"]
    semester.alignment = TA_LEFT
    semester.fontName = "Helvetica"
    semester.fontSize = 9
    semester.leading = 18
    semester_title = "<b>SECOND SEMESTER</b>"
    semester_title = Paragraph(semester_title, semester)
    Story.append(semester_title)
    # SECOND SEMESTER
    count = 0
    header = [('S/No', 'Course Code', 'Course Title', 'Unit', Paragraph('<b>Name, Siganture of course lecturer & Date</b>', style['Normal']))]
    table_header = Table(header,1*[1.4*inch], 1*[0.5*inch])
    table_header.setStyle(
        TableStyle([
                ('ALIGN',(-2,-2), (-2,-2),'CENTER'),
                ('VALIGN',(-2,-2), (-2,-2),'MIDDLE'),
                ('ALIGN',(1,0), (1,0),'CENTER'),
                ('VALIGN',(1,0), (1,0),'MIDDLE'),
                ('ALIGN',(0,0), (0,0),'CENTER'),
                ('VALIGN',(0,0), (0,0),'MIDDLE'),
                ('ALIGN',(-4,0), (-4,0),'LEFT'),
                ('VALIGN',(-4,0), (-4,0),'MIDDLE'),
                ('ALIGN',(-3,0), (-3,0),'LEFT'),
                ('VALIGN',(-3,0), (-3,0),'MIDDLE'),
                ('TEXTCOLOR',(0,-1),(-1,-1),colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                ('BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
    Story.append(table_header)

    second_semester_unit = 0
    for course in courses:
        if course.course.semester == SECOND:
            second_semester_unit += int(course.course.courseUnit)
            data = [(count+1, course.course.courseCode.upper(), course.course.courseTitle, course.course.courseUnit, '')]
            color = colors.black
            count += 1
            table_body=Table(data,1*[1.4*inch], 1*[0.3*inch])
            table_body.setStyle(
                TableStyle([
                    ('ALIGN',(-2,-2), (-2,-2),'CENTER'),
                    ('ALIGN',(1,0), (1,0),'CENTER'),
                    ('ALIGN',(0,0), (0,0),'CENTER'),
                    ('ALIGN',(-4,0), (-4,0),'LEFT'),
                    ('TEXTCOLOR',(0,-1),(-1,-1),colors.black),
                    ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                    ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                    ]))
            Story.append(table_body)

    style = getSampleStyleSheet()
    semester = style["Normal"]
    semester.alignment = TA_LEFT
    semester.fontName = "Helvetica"
    semester.fontSize = 8
    semester.leading = 18
    semester_title = "<b>Total Units : " + str(second_semester_unit) + "</b>"
    semester_title = Paragraph(semester_title, semester)
    Story.append(semester_title)

    Story.append(Spacer(1, 2))
    style = getSampleStyleSheet()
    certification = style["Normal"]
    certification.alignment = TA_JUSTIFY
    certification.fontName = "Helvetica"
    certification.fontSize = 8
    certification.leading = 18
    student = Student.objects.get(user__pk=request.user.id)
    certification_text = "CERTIFICATION OF REGISTRATION: I certify that <b>" + str(request.user.get_full_name().upper()) + "</b>\
    has been duly registered for the <b>" + student.level + " level </b> of study in the department\
    of INFORMATION MANAGEMENT TECHNOLOGY and that the courses and units registered are as approved by the senate of the University"
    certification_text = Paragraph(certification_text, certification)
    Story.append(certification_text)

    # FIRST SEMESTER ENDS HERE

    logo = MEDIA_ROOT + "/logo/android-chrome-144x144.png"
    im = Image(logo, 1.5*inch, 1.5*inch)
    im.__setattr__("_offs_x", -228)
    im.__setattr__("_offs_y", 625)
    Story.append(im)

    picture =  BASE_DIR + request.user.get_picture()
    im = Image(picture, 1.0*inch, 1.0*inch)
    im.__setattr__("_offs_x", 218)
    im.__setattr__("_offs_y", 625)
    Story.append(im)
    doc.build(Story)
    fs = FileSystemStorage("/tmp")
    with fs.open(fname) as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename='+fname+''
        return response
    return response