from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (TemplateView, 
                                  ListView,  
                                  CreateView, 
                                  UpdateView, 
                                  DeleteView, 
                                  DetailView)
from courses.models import Course, Module, Lesson



class InstructorView(TemplateView):
    template_name = "instructor/dashboard.html"

# Course Management Views
class InstructorCourseListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Course 
    template_name = "instructor/instructor_course_list.html"
    context_object_name = 'courses'

    def get_queryset(self):
        return Course.objects.filter(created_by=self.request.user)
    
    def test_func(self):
        courses = self.get_queryset()
        return all(course.created_by == self.request.user for course in courses)
    
class  InstructorCourseCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Course
    fields = ['title', 'description', 'objectives', 'image', 'category']
    template_name = "instructor/course_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
    def test_func(self):
        return self.request.user.role == 'instructor'

    def get_success_url(self):
        return reverse('instructor_course_detail', kwargs={'pk': self.object.pk})

class InstructorCourseDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Course
    template_name = "instructor/instructor_course_detail.html"

    def test_func(self):
        course = self.get_object()
        if self.request.user == course.created_by:
            return True
        return False

class InstructorCourseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Course
    fields = ['title', 'description', 'objectives', 'image', 'category']
    template_name = "instructor/course_update_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
    def test_func(self):
        course = self.get_object()
        if self.request.user == course.created_by:
            return True
        return False

    def get_success_url(self):
        return reverse('instructor_course_detail', kwargs={'pk': self.object.pk})
    
class InstructorCourseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Course
    template_name = "instructor/course_confirm_delete.html"
    success_url = reverse_lazy('instructor_course_list')

    def test_func(self):
        course = self.get_object()
        if self.request.user == course.created_by:
            return True
        return False
    

# Module Management Views 
class InstructorModuleListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "instructor/instructor_module_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instructor = self.request.user
        context['courses'] = Course.objects.filter(created_by=instructor).prefetch_related('modules')
        return context

    def test_func(self):
        instructor = self.request.user
        return Module.objects.filter(course__created_by=instructor).exists()

class InstructorModuleDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Module
    template_name = "instructor/instructor_module_detail.html"
    context_object_name = "module"
    pk_url_kwarg = 'pk' # Use 'pk' as the URL keyword argument for module ID

    def test_func(self):
        module = self.get_object() # Get the module object using get_object()
        return module.course.created_by == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        module = self.get_object() # Get the module object again to access related lessons
        context['lessons'] = module.lessons.all() # Add lessons to the context
        return context

class InstructorModuleCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Module
    fields = ['title', 'description', 'course', 'image_content', 'objectives', 'content']
    template_name = "instructor/module_form.html"

    def form_valid(self, form):
        selected_course = form.cleaned_data['course'] 
        if selected_course.created_by != self.request.user:
            form.add_error('course', "You can only create modules for courses you own.")
            return self.form_invalid(form)
        return super().form_valid(form)
    
    def test_func(self):
        course_id = self.kwargs.get('pk') 
        if not course_id:
            return False
        course = get_object_or_404(Course, id=course_id)
        return course.created_by == self.request.user

    def get_success_url(self):
        return reverse('instructor_module_detail', kwargs={'pk': self.object.pk})
    
class InstructorModuleUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Module
    fields = ['title', 'description', 'course', 'image_content', 'objectives', 'content']
    template_name = "instructor/module_update_form.html"

    def form_valid(self, form):
        selected_course = form.cleaned_data['course']
        if selected_course.created_by != self.request.user:
            form.add_error('course', "You can only update modules for courses you own.")
            return self.form_invalid(form)
        return super().form_valid(form)
    
    def test_func(self):
        module = self.get_object() 
        return module.course.created_by == self.request.user
    
    def get_success_url(self):
        return reverse('instructor_module_detail', kwargs={'pk': self.object.pk})
    
class InstructorModuleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Module
    template_name = "instructor/module_confirm_delete.html"
    context_object_name = "module"

    def test_func(self):
        module = self.get_object()
        return module.course.created_by == self.request.user
    
    def get_success_url(self):
        return reverse('instructor_module_list')
    

# Lesson Management Views
class InstructorLessonListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Lesson
    template_name = "instructor/instructor_lesson_list.html"
    context_object_name = "lessons"

    def get_queryset(self):
        module_id = self.kwargs.get('pk')
        self.module = get_object_or_404(Module, id=module_id)
        return Lesson.objects.filter(module=self.module)

    def test_func(self):
        module_id = self.kwargs.get('pk')
        module = get_object_or_404(Module, id=module_id)
        return module.course.created_by == self.request.user

    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['module'] = self.module
            context['courses'] = Course.objects.filter(created_by=self.request.user).prefetch_related('modules__lessons') #Added courses to context.
            return context


class InstructorLessonCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Lesson
    fields = [ 'module', 'title', 'description', 'objectives', 'image_content', 'content']
    template_name = "instructor/lesson_form.html"

    def form_valid(self, form):
        selected_module = form.cleaned_data['module']
        if selected_module.course.created_by != self.request.user:
            form.add_error('module', "You can only create lessons for modules in courses you own.")
            return self.form_invalid(form)
        return super().form_valid(form)
    
    def test_func(self):
        module_id = self.kwargs.get('pk')
        module = get_object_or_404(Module, id=module_id)
        return module.course.created_by == self.request.user

    def get_success_url(self):
        return reverse('instructor_lesson_list', kwargs={'pk': self.object.module.pk})
    
class InstructorLessonDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Lesson
    template_name = "instructor/instructor_lesson_detail.html"
    context_object_name = "lesson"
    pk_url_kwarg = 'pk'

    def test_func(self):
        lesson = self.get_object()
        return lesson.module.course.created_by == self.request.user
    
class InstructorLessonUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Lesson
    fields = [ 'module', 'title', 'description', 'objectives', 'image_content', 'content']
    template_name = "instructor/lesson_update_form.html"

    def form_valid(self, form):
        selected_module = form.cleaned_data['module']
        if selected_module.course.created_by != self.request.user:
            form.add_error('module', "You can only update lessons for modules in courses you own.")
            return self.form_invalid(form)
        return super().form_valid(form)
    
    def test_func(self):
        lesson = self.get_object()
        return lesson.module.course.created_by == self.request.user
    
    def get_success_url(self):
        return reverse('instructor_lesson_detail', kwargs={'pk': self.object.pk})
    
class InstructorLessonDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Lesson
    template_name = "instructor/lesson_confirm_delete.html"
    context_object_name = "lesson"

    def test_func(self):
        lesson = self.get_object()
        return lesson.module.course.created_by == self.request.user
    
    def get_success_url(self):
        return reverse('instructor_lesson_list', kwargs={'pk': self.object.module.pk})