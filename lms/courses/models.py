from django.utils import timezone
from django.db import models
from users.models import User
from tinymce.models import HTMLField  # Import TinyMCE HTMLField
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.conf import settings
import os, mimetypes
from cloudinary_storage.storage import RawMediaCloudinaryStorage


class Course(models.Model):

    CATEGORY_CHOICES = [
        ('community_health', 'Community Health'),
        ('obstetrics', 'Obstetrics & Gynecology'),
        ('pediatrics', 'Pediatrics'),
        ('cloud_computing', 'Cloud Computing'),
        ('python_programming', 'Python Programming'),
        ('data_science', 'Data Science'),
        ('django_framework', 'Django Framework'),
    ]

    title = models.CharField(max_length=200)
    description = HTMLField(blank=True, null=True)  # Replaced CKEditor with TinyMCE
    objectives = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'instructor'})
    enrolled_students = models.ManyToManyField(User, related_name='enrolled_courses', through='Enrollment', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='course_images/', null=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='community_health')

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['created_at']

    def default_image(self):
        return self.image.url if self.image else '/static/images/default.jpg'

    def progress(self, user):
        total_lessons = self.modules.all().prefetch_related('lessons').count()
        completed_lessons = self.modules.all().prefetch_related('lessons').filter(
            lessons__read=True, lessons__enrollment__user=user).count()
        lesson_progress = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0

        total_quizzes = self.quizzes.count()
        completed_quizzes = self.quizzes.filter(attempts__student=user, attempts__completed=True).distinct().count()
        quiz_progress = (completed_quizzes / total_quizzes) * 100 if total_quizzes > 0 else 0

        return (lesson_progress + quiz_progress) / 2 

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = HTMLField(blank=True, null=True)
    image_content = models.ImageField(upload_to='module_images/', blank=True, null=True)
    objectives = models.TextField(blank=True, null=True)
    content = HTMLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    class Meta:
        ordering = ['created_at']

class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = HTMLField(blank=True, null=True)
    objectives = models.TextField(blank=True, null=True)
    image_content = models.ImageField(upload_to='lesson_images/', blank=True, null=True)
    content = HTMLField(blank=True, null=True)
    read_by_users = models.ManyToManyField(User, related_name='read_lessons', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='lesson_pdfs/', storage=RawMediaCloudinaryStorage(), blank=True, null=True)

    def __str__(self):
        return f"{self.module.course.title} - {self.module.title} - {self.title}"
    
    class Meta:
        ordering = ['created_at']

    # NEW: convenience property to determine lesson type for UI/icon decision
    @property
    def lesson_type(self):
        """
        Returns one of 'video', 'pdf', 'text' depending on available content.
        Priority: video > pdf > text
        """
        if hasattr(self, 'videos') and self.videos.exists():
            return 'video'
        if self.pdf_file:
            return 'pdf'
        if self.content:
            return 'text'
        return 'text'


class Video(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=200)
    video_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

    class Meta:
        ordering = ['created_at']

class AdditionalMaterial(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='additional_materials')
    title = models.CharField(max_length=200)
    material_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

    class Meta:
        ordering = ['created_at']

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_enrolled = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.email} enrolled in {self.course.title}"

class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='notes')
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Ensure a user can only have one note per lesson
        unique_together = ('user', 'lesson')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Note for {self.user.email} on {self.lesson.title}"

# Ebooks
class EbookCategory(models.Model):
    """
    Optional categorisation for ebooks (separate from Course categories).
    """
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)

    class Meta:
        verbose_name = "Ebook Category"
        verbose_name_plural = "Ebook Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Ebook(models.Model):
    """
    Stores ebooks (PDFs) that can be read inside the site via a viewer.
    Do not expose a direct download link in templates; serve via viewer endpoint.
    """
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=260, unique=True)
    description = HTMLField(blank=True, null=True)
    cover_image = models.ImageField(upload_to='ebook_covers/', null=True, blank=True)
    file = models.FileField(upload_to='ebooks/', storage=RawMediaCloudinaryStorage(), help_text="Upload PDF file")
    category = models.ForeignKey(EbookCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='ebooks')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_ebooks')
    published = models.BooleanField(default=True)
    allow_preview = models.BooleanField(default=True, help_text="If false, prevent in-site preview")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['published']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_pdf(self):
        name = (self.file.name or '').lower()
        return name.endswith('.pdf')

    def cover_url(self):
        return self.cover_image.url if self.cover_image else '/static/images/ebook-default-cover.png'
    

#Certificates
from django.utils import timezone
from django.core.files.base import ContentFile
import io
import uuid # Import uuid

class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    issued_at = models.DateTimeField(default=timezone.now)
    certificate_file = models.FileField(upload_to='certificates/', storage=RawMediaCloudinaryStorage(), null=True, blank=True)
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True) # Unique ID for verification

    class Meta:
        unique_together = ('user', 'course') # User gets one certificate per course
        ordering = ['-issued_at']

    def __str__(self):
        return f"Certificate for {self.user.email} - {self.course.title}"

    def generate_and_save_certificate(self):
        # Placeholder for the actual generation logic using the utility function
        # This method will call the utility, get the PDF bytes, and save it to certificate_file
        from .utility import generate_certificate_pdf # Avoid circular import

        try:
            pdf_bytes = generate_certificate_pdf(self.user, self.course)
            if pdf_bytes:
                # Use unique_id in filename to ensure uniqueness
                filename = f"certificate_{self.user.id}_{self.course.id}_{self.unique_id}.pdf"
                self.certificate_file.save(filename, ContentFile(pdf_bytes), save=True)
                return True
        except Exception as e:
            print(f"Error generating certificate for user {self.user.id}, course {self.course.id}: {e}")
            # Consider logging the error properly
        return False