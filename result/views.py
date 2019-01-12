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

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, black
from reportlab.lib.units import inch



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
    levels = (100, 200, 300, 400, 500)

    for i in levels:
        all_query_score += (TakenCourse.objects.filter(student__level=i),)

    first_level_total = 0
    for i in all_query_score[0]:
        first_level_total += i.total
    first_level_avg = 0
    if not all_query_score[0].count() == 0:
        first_level_avg = first_level_total / all_query_score[0].count()

    second_level_total = 0
    for i in all_query_score[1]:
        second_level_total += i.total
    second_level_avg = 0
    if not all_query_score[1].count() == 0:
        second_level_avg = second_level_total / all_query_score[1].count()

    third_level_total = 0
    for i in all_query_score[2]:
        third_level_total += i.total
    third_level_avg = 0
    if not all_query_score[2].count() == 0:
        third_level_avg = third_level_total / all_query_score[2].count()

    fourth_level_total = 0
    for i in all_query_score[3]:
        fourth_level_total += i.total
    fourth_level_avg = 0
    if not all_query_score[3].count() == 0:
        fourth_level_avg = fourth_level_total / all_query_score[3].count()

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
        print(a)
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
    messages.success(request, 'Updated successfully!')
    return render(request, 'result/session_update.html', {'form': form})

@login_required
@lecturer_required
def session_delete_view(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    semester.delete()
    messages.success(request, 'Deleted successfully!')
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
            data = form.data.get('is_current_semester') # returns string of 2 if the user selected yes
            if data == '2':
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
        if request.POST.get('is_current_semester') == 'True': # returns string of 'True' if the user selected yes for is current semester
            unset = Semester.objects.get(is_current_semester=True)
            unset.is_current_semester = False
            print(unset)
            unset.save()
            form = SemesterForm(request.POST, instance=semester)
            if form.is_valid():
                form.save()
                messages.success(request, 'Semester updated successfully !')
                return redirect('manage_semester')
        else:
            form = SemesterForm(request.POST, instance=semester)
            if form.is_valid():
                form.save()
                messages.success(request, 'Semester updated successfully ! ')
                return redirect('manage_semester')

    else:
        form = SemesterForm(instance=semester)
    return render(request, 'result/semester_update.html', {'form': form})

@login_required
@lecturer_required
def semester_delete_view(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    semester.delete()
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
        registered_courses = Course.objects.filter(level=student.level).filter(id__in=t)
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
    current_semester = Semester.objects.get(is_current_semester=True)
    current_session = Session.objects.get(is_current_session=True)
    courses = Course.objects.filter(allocated_course__lecturer__pk=request.user.id).filter(semester=current_semester)
    context = {
    "courses":courses, 
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
        print(courses)
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
    # TOBE USED, fname = str(current_semester) + '_semester_' + str(current_session) + '_session_' + 'result sheet.pdf'
    doc = SimpleDocTemplate("/tmp/somefilename.pdf")
    styles = getSampleStyleSheet()
    Story = [Spacer(1,2)]
    style = styles["Normal"]
    title = "\t\t\t" + str(current_semester) + " Semester " + str(current_session) + " Result Sheet"
    p = Paragraph(title, style)
    Story.append(p)
    Story.append(Spacer(1,1*inch))

    header = "ID Number  CA  Exam  Grade Comment"
    p = Paragraph(header, style)
    Story.append(p)
    Story.append(Spacer(1,0.3*inch))
    for student in result:
       bogustext = "{0} {1} {2} {3} {4}".format(student.student.id_number, int(student.ca), int(student.exam), student.grade, student.comment)
       p = Paragraph(bogustext, style)
       Story.append(p)
       Story.append(Spacer(1,0.2*inch))
    doc.build(Story)

    fs = FileSystemStorage("/tmp")
    with fs.open("somefilename.pdf") as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="somefilename.pdf"'
        return response
    return response