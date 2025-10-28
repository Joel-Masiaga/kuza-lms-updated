from django import forms
from tinymce.widgets import TinyMCE
from courses.models import Course, Module, Lesson, Note

class CourseForm(forms.ModelForm):
    description = forms.CharField(widget=TinyMCE())
    objectives = forms.CharField(widget=TinyMCE())

    class Meta:
        model = Course
        fields = ['title', 'description', 'objectives', 'image', 'category'] 

class ModuleForm(forms.ModelForm):
    description = forms.CharField(widget=TinyMCE())
    objectives = forms.CharField(widget=TinyMCE())
    content = forms.CharField(widget=TinyMCE())

    class Meta:
        model = Module
        fields = ['title', 'description', 'course', 'image_content', 'objectives', 'content']

class LessonForm(forms.ModelForm):
    description = forms.CharField(widget=TinyMCE())
    objectives = forms.CharField(widget=TinyMCE()) 
    content = forms.CharField(widget=TinyMCE())

    class Meta:
        model = Lesson
        fields = ['module', 'title', 'description', 'objectives', 'image_content', 'content']

class NoteForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full flex-1 p-3 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-primary focus:border-primary resize-none',
            'placeholder': 'Add notes for this lesson...',
            'id': 'notes-textarea' # Ensure ID matches JS
        }),
        required=False
    )

    class Meta:
        model = Note
        fields = ['content']
