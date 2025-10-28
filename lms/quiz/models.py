from django.db import models 
from courses.models import Module  # Updated to use Module instead of Lesson
from users.models import User

class Quiz(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='quizzes')  # Now linked to a module
    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'instructor'})  # Created by tutor

    def __str__(self):
        return f"Quiz: {self.title} for Module: {self.module.title}"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()  # The actual question text
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Question: {self.question_text} in Quiz: {self.quiz.title}" 
    
    class Meta:
        ordering = ['created_at']

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=255)  # Text for each possible answer
    is_correct = models.BooleanField(default=False)  # Whether this is the correct answer
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer: {self.answer_text} (Correct: {self.is_correct})"
    
    class Meta:
        ordering = ['created_at']

class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    date_taken = models.DateTimeField(auto_now_add=True)
    score = models.FloatField(null=True, blank=True)  # Percentage score of the student
    completed = models.BooleanField(default=False)  # Indicates whether the quiz was completed

    def __str__(self):
        return f"{self.student.email} attempted {self.quiz.title} on {self.date_taken}"
