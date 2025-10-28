from django.contrib import admin
from .models import Quiz, Question, Answer

# Quiz admin registration
class QuizAdmin(admin.ModelAdmin):
    # Updated list_display to reflect 'module' instead of 'lesson'
    list_display = ['title', 'module', 'created_by']
    search_fields = ['title', 'module__title']  # Search by module title
    list_filter = ['module__course', 'created_by']  # Filter by course via module

# Question admin registration
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'quiz']
    search_fields = ['question_text', 'quiz__title']
    list_filter = ['quiz']

# Answer admin registration
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['answer_text', 'question', 'is_correct']
    search_fields = ['answer_text', 'question__question_text']
    list_filter = ['is_correct']

# Register Quiz, Question, and Answer models
admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)
