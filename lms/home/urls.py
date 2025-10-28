from django.urls import path
from . import views
from .views import (
    LessonDetailView, 
    ModuleDetailView, 
    CoursesView,  
    CourseDetailView, 
    QuizDetailView, 
    SubmitQuizView, 
    CertificateListView, 
    DownloadCertificateView, 
    QuizAttemptListView, 
    ReviewQuizView
)

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('courses/', CoursesView.as_view(), name='courses'),
    path('course/<int:pk>/', CourseDetailView.as_view(), name='course_detail'),
    path('module/<int:pk>/', ModuleDetailView.as_view(), name='module_detail'),
    path('lesson/<int:pk>/', LessonDetailView.as_view(), name='lesson_detail'),


 # Quiz detail view (to display the quiz and questions)
    path('quiz/<int:quiz_id>/', QuizDetailView.as_view(), name='quiz_detail'),

    # Submit quiz view (when the student submits their answers)
    path('quiz/<int:quiz_id>/submit/', SubmitQuizView.as_view(), name='submit_quiz'),

# Quizzes menu and review
    path('quizzes/', QuizAttemptListView.as_view(), name='quiz_list'),
    path('quizzes/<int:quiz_id>/review/', ReviewQuizView.as_view(), name='quiz_review'),

 # Ebook
    path('ebooks/', views.EbookListView.as_view(), name='ebook_list'),
    path('ebooks/<slug:slug>/', views.EbookDetailView.as_view(), name='ebook_detail'),
    path('ebooks/<slug:slug>/stream/', views.EbookStreamView.as_view(), name='ebook_stream'),

    # Certificates
    path('certificates/', CertificateListView.as_view(), name='certificate_list'),
    path('certificates/download/<int:certificate_id>/', DownloadCertificateView.as_view(), name='download_certificate'),

]
