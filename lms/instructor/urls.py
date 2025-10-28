from django.urls import path
from .views import (InstructorView, 
                    InstructorCourseListView, 
                    InstructorCourseCreateView, 
                    InstructorCourseDetailView, 
                    InstructorCourseUpdateView, 
                    InstructorCourseDeleteView,
                    
                    InstructorModuleListView,
                    InstructorModuleDetailView,
                    InstructorModuleCreateView,
                    InstructorModuleUpdateView,
                    InstructorModuleDeleteView,
                    
                    InstructorLessonListView,
                    InstructorLessonCreateView,
                    InstructorLessonDetailView,
                    InstructorLessonUpdateView,
                    InstructorLessonDeleteView)


urlpatterns = [
    path('dashboard/', InstructorView.as_view(), name='instructor_dashboard'),
    path('instructor-courses/', InstructorCourseListView.as_view(), name='instructor_course_list'),
    path('create-course/', InstructorCourseCreateView.as_view(), name='create_course'),
    path('course/<int:pk>/', InstructorCourseDetailView.as_view(), name='instructor_course_detail'),
    path('course/<int:pk>/update/', InstructorCourseUpdateView.as_view(), name='update_course'),
    path('course/<int:pk>/delete/', InstructorCourseDeleteView.as_view(), name='delete_course'),

    # Module url paths
    path('course/modules/', InstructorModuleListView.as_view(), name='instructor_module_list'),
    path('module/<int:pk>/', InstructorModuleDetailView.as_view(), name='instructor_module_detail'),
    path('course/<int:pk>/create-module/', InstructorModuleCreateView.as_view(), name='create_module'),
    path('module/<int:pk>/update/', InstructorModuleUpdateView.as_view(), name='update_module'),
    path('module/<int:pk>/delete/', InstructorModuleDeleteView.as_view(), name='delete_module'),

    # Lesson url paths
    path('module/<int:pk>/lessons/', InstructorLessonListView.as_view(), name='instructor_lesson_list'), 
    path('module/<int:pk>/create-lesson/', InstructorLessonCreateView.as_view(), name='create_lesson'),
    path('lesson/<int:pk>/', InstructorLessonDetailView.as_view(), name='instructor_lesson_detail'),
    path('lesson/<int:pk>/update-lesson/', InstructorLessonUpdateView.as_view(), name='update_lesson'),
    path('lesson/<int:pk>/delete-lesson/', InstructorLessonDeleteView.as_view(), name='delete_lesson'),
]   