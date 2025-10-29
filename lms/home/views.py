from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect, FileResponse, Http404, HttpResponseForbidden
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View, ListView
from django.contrib import messages
from django.db import models, transaction
from django.db.models import F, Count, Q, Sum, Case, When, Value, IntegerField
import os
from courses.models import Course, Lesson, Module, Enrollment, Note, Ebook, EbookCategory, Certificate
from quiz.models import Quiz, Question, Answer, QuizAttempt
from users.models import User, Profile

# Gamification constants
POINTS_PER_LESSON = 10
POINTS_PER_COURSE = 100
POINTS_PER_QUIZ = 50  # Award when user achieves pass mark in a quiz


@transaction.atomic
def check_completion_and_generate_certificate(user, course, request, allow_award=True):
    """
    Course completion check. Only awards course points/certificate when allow_award is True.
    Revokes if course becomes incomplete.
    """
    ProfileModel = Profile
    profile, _ = ProfileModel.objects.get_or_create(user=user)
    already_completed = profile.earned_badges.filter(pk=course.pk).exists()

    total_lessons = Lesson.objects.filter(module__course=course).count()
    if total_lessons == 0:
        return False

    read_lessons_count = Lesson.objects.filter(module__course=course, read_by_users=user).count()
    all_lessons_read = read_lessons_count >= total_lessons

    # Require passing the last module's quiz if it exists
    quiz_requirement_met = True
    last_module = course.modules.order_by('created_at').last()
    if last_module:
        final_quiz = Quiz.objects.filter(module=last_module).first()
        if final_quiz:
            quiz_requirement_met = QuizAttempt.objects.filter(
                student=user, quiz=final_quiz, score__gte=75
            ).exists()

    is_now_complete = all_lessons_read and quiz_requirement_met

    if allow_award and is_now_complete and not already_completed:
        ProfileModel.objects.filter(user=user).update(points=F('points') + POINTS_PER_COURSE)
        profile.earned_badges.add(course)
        profile.refresh_from_db()
        certificate = Certificate(user=user, course=course)
        if certificate.generate_and_save_certificate():
            messages.success(request, f"Congratulations! You've completed {course.title}, earned {POINTS_PER_COURSE} points, and a badge!")
        else:
            messages.success(request, f"Congratulations! You've completed {course.title}, earned {POINTS_PER_COURSE} points, and a badge! (Certificate generation failed)")
        return True
    elif not is_now_complete and already_completed:
        ProfileModel.objects.filter(user=user).update(
            points=Case(
                When(points__gte=Value(POINTS_PER_COURSE), then=F('points') - Value(POINTS_PER_COURSE)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        profile.earned_badges.remove(course)
        Certificate.objects.filter(user=user, course=course).delete()
        messages.info(request, f"Course '{course.title}' is no longer complete. Badge and {POINTS_PER_COURSE} points removed.")
        return False
    elif allow_award and is_now_complete and not Certificate.objects.filter(user=user, course=course).exists():
        certificate = Certificate(user=user, course=course)
        certificate.generate_and_save_certificate()

    return False


class HomeView(TemplateView):
    template_name = "home/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_courses"] = Course.objects.all().order_by('-created_at')
        context["enrolled_courses"] = Course.objects.none()
        context["completed_courses"] = []
        context["in_progress_courses"] = []
        context["user_points"] = 0
        context["user_badges"] = 0

        if self.request.user.is_authenticated:
            user = self.request.user
            profile, _ = Profile.objects.get_or_create(user=user)

            enrolled_courses = Course.objects.filter(enrollment__user=user).prefetch_related(
                'modules__lessons',
                'modules__quizzes'
            )

            completed_course_pks = set(profile.earned_badges.values_list('pk', flat=True))
            completed_list = []
            in_progress_list = []

            for course in enrolled_courses:
                if course.pk in completed_course_pks:
                    completed_list.append(course)
                else:
                    in_progress_list.append(course)

            context.update({
                "enrolled_courses": enrolled_courses,
                "completed_courses": completed_list,
                "in_progress_courses": in_progress_list,
                "user_points": profile.points,
                "user_badges": len(completed_course_pks),
            })
        return context


@method_decorator(login_required, name='dispatch')
class CoursesView(TemplateView):
    template_name = "home/courses.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile, _ = Profile.objects.get_or_create(user=user)

        current_filter = self.request.GET.get('filter', 'all')
        context['current_filter'] = current_filter

        enrolled_courses = Course.objects.filter(enrollment__user=user).select_related(
            'created_by__profile'
        ).only(
            'pk', 'title', 'image', 'category', 'description',
            'created_by__profile__first_name', 'created_by__profile__last_name'
        )

        completed_course_ids = set(profile.earned_badges.values_list('id', flat=True))
        completed_courses = [c for c in enrolled_courses if c.id in completed_course_ids]
        enrolled_not_completed_courses = [c for c in enrolled_courses if c.id not in completed_course_ids]

        other_courses = Course.objects.exclude(enrollment__user=user).select_related(
            'created_by__profile'
        ).only(
            'pk', 'title', 'image', 'category', 'description',
            'created_by__profile__first_name', 'created_by__profile__last_name'
        ) if current_filter in ('all', '') else Course.objects.none()

        context.update({
            'enrolled_courses': enrolled_courses,
            'completed_courses': completed_courses,
            'enrolled_not_completed_courses': enrolled_not_completed_courses,
            'other_courses': other_courses
        })
        return context


class CourseDetailView(View):
    def get(self, request, pk):
        course = get_object_or_404(
            Course.objects.select_related('created_by__profile').prefetch_related(
                models.Prefetch(
                    'modules',
                    queryset=Module.objects.order_by('created_at').prefetch_related(
                        models.Prefetch('lessons', queryset=Lesson.objects.order_by('created_at').only('pk', 'title'))
                    ).only('pk', 'title', 'course_id')
                )
            ),
            pk=pk
        )
        modules = course.modules.all()
        enrolled = request.user.is_authenticated and Enrollment.objects.filter(user=request.user, course=course).exists()
        return render(request, 'home/course_detail.html', {'course': course, 'modules': modules, 'enrolled': enrolled})

    @method_decorator(login_required)
    @transaction.atomic
    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        action = request.POST.get('action', 'enroll')
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)

        if action == 'enroll':
            enrollment, created = Enrollment.objects.get_or_create(user=user, course=course)
            if created:
                messages.success(request, f'You have successfully enrolled in {course.title}!')
            else:
                messages.info(request, f'You are already enrolled in {course.title}.')

            first_lesson = Lesson.objects.filter(module__course=course).order_by('module__created_at', 'created_at').first()
            if first_lesson:
                return redirect('lesson_detail', pk=first_lesson.pk)

            messages.warning(request, "This course doesn't have any lessons yet.")
            return HttpResponseRedirect(reverse('course_detail', args=[pk]))

        elif action == 'unenroll':
            enrollment = Enrollment.objects.filter(user=user, course=course).first()
            if enrollment:
                was_completed = profile.earned_badges.filter(pk=course.pk).exists()

                lessons_in_course = Lesson.objects.filter(module__course=course)
                points_to_remove = lessons_in_course.filter(read_by_users=user).count() * POINTS_PER_LESSON

                user.read_lessons.remove(*lessons_in_course)
                Note.objects.filter(user=user, lesson__in=lessons_in_course).delete()
                quizzes_in_course = Quiz.objects.filter(module__course=course)
                QuizAttempt.objects.filter(student=user, quiz__in=quizzes_in_course).delete()

                if was_completed:
                    points_to_remove += POINTS_PER_COURSE
                    profile.earned_badges.remove(course)
                    Certificate.objects.filter(user=user, course=course).delete()

                if points_to_remove > 0:
                    Profile.objects.filter(user=user).update(
                        points=Case(
                            When(points__gte=Value(points_to_remove), then=F('points') - Value(points_to_remove)),
                            default=Value(0),
                            output_field=IntegerField(),
                        )
                    )

                enrollment.delete()
                messages.success(request, f'You have successfully unenrolled from {course.title} and your progress has been cleared.')
            else:
                messages.warning(request, f'You are not enrolled in {course.title}.')

            return HttpResponseRedirect(reverse('course_detail', args=[pk]))

        messages.error(request, "Invalid action.")
        return HttpResponseRedirect(reverse('course_detail', args=[pk]))


class ModuleDetailView(View):
    def get(self, request, pk):
        module = get_object_or_404(
            Module.objects.select_related('course').prefetch_related(
                models.Prefetch('lessons', queryset=Lesson.objects.only('pk', 'title').order_by('created_at'))
            ),
            pk=pk
        )
        return render(request, 'home/module_detail.html', {'module': module})


@method_decorator(login_required, name='dispatch')
class LessonDetailView(View):
    def get(self, request, pk):
        lesson = get_object_or_404(Lesson.objects.select_related('module__course'), pk=pk)
        user = request.user
        course = lesson.module.course

        if not Enrollment.objects.filter(user=user, course=course).exists():
            messages.warning(request, f"You must be enrolled in '{course.title}' to view this lesson.")
            return redirect('course_detail', pk=course.pk)

        # Enforce module progression: all previous module quizzes (if any) must be passed
        ordered_modules = list(course.modules.order_by('created_at'))
        for m in ordered_modules:
            if m == lesson.module:
                break
            q = m.quizzes.first()
            if q and not QuizAttempt.objects.filter(student=user, quiz=q, score__gte=75).exists():
                messages.warning(request, f"Please pass the quiz for module '{m.title}' (score 75%+) to proceed.")
                return redirect('quiz_detail', quiz_id=q.pk)

        all_course_modules = course.modules.order_by('created_at').prefetch_related(
            models.Prefetch('lessons', queryset=Lesson.objects.order_by('created_at').only('pk', 'title')),
            models.Prefetch('quizzes', queryset=Quiz.objects.only('pk', 'module_id'))
        )

        lesson_pks_in_course = Lesson.objects.filter(module__course=course).values_list('pk', flat=True)
        total_lessons_count = lesson_pks_in_course.count()
        read_lesson_ids = set(user.read_lessons.filter(pk__in=lesson_pks_in_course).values_list('pk', flat=True))
        completed_lessons_count = len(read_lesson_ids)

        progress_percentage = (completed_lessons_count * 100.0 / total_lessons_count) if total_lessons_count else 0
        read = lesson.pk in read_lesson_ids

        # Prev/next lesson ids
        all_lessons_flat_pks = list(
            Lesson.objects.filter(module__course=course)
            .order_by('module__created_at', 'created_at')
            .values_list('pk', flat=True)
        )
        previous_lesson = None
        next_lesson = None
        try:
            idx = all_lessons_flat_pks.index(lesson.pk)
            prev_id = all_lessons_flat_pks[idx - 1] if idx > 0 else None
            next_id = all_lessons_flat_pks[idx + 1] if idx < len(all_lessons_flat_pks) - 1 else None
            if prev_id:
                previous_lesson = Lesson.objects.only('pk').get(pk=prev_id)
            if next_id:
                next_lesson = Lesson.objects.only('pk').get(pk=next_id)
        except ValueError:
            pass

        module_quiz = lesson.module.quizzes.first()
        quiz_attempt = None
        if module_quiz:
            quiz_attempt = QuizAttempt.objects.filter(student=user, quiz=module_quiz).first()

        note = Note.objects.filter(user=user, lesson=lesson).first()

        context = {
            'lesson': lesson,
            'all_course_modules': all_course_modules,
            'previous_lesson': previous_lesson,
            'next_lesson': next_lesson,
            'progress_percentage': progress_percentage,
            'read': read,
            'quiz_attempt': quiz_attempt,
            'read_lesson_ids': read_lesson_ids,
            'note': note,
        }
        return render(request, 'home/lesson.html', context)

    @transaction.atomic
    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        user = request.user
        course = lesson.module.course
        profile, _ = Profile.objects.get_or_create(user=user)

        if not Enrollment.objects.filter(user=user, course=course).exists():
            messages.error(request, "You are not enrolled in this course.")
            return HttpResponse("You are not enrolled in this course.", status=403)

        # Save Note
        if 'save_note' in request.POST:
            note_content = request.POST.get('note_content', '')
            Note.objects.update_or_create(user=user, lesson=lesson, defaults={'content': note_content})
            messages.success(request, "Your note has been saved!")
            return redirect('lesson_detail', pk=lesson.id)

        action_taken = None
        next_url = None
        lesson_was_already_read = lesson.read_by_users.filter(pk=user.pk).exists()

        if 'mark_read' in request.POST and not lesson_was_already_read:
            lesson.read_by_users.add(user)
            action_taken = 'mark_read'
            Profile.objects.filter(user=user).update(points=F('points') + POINTS_PER_LESSON)
            messages.success(request, f"Lesson complete! +{POINTS_PER_LESSON} points.")

        elif 'unmark_read' in request.POST and lesson_was_already_read:
            was_course_complete = profile.earned_badges.filter(pk=course.pk).exists()
            lesson.read_by_users.remove(user)
            action_taken = 'unmark_read'

            Profile.objects.filter(user=user).update(
                points=Case(
                    When(points__gte=Value(POINTS_PER_LESSON), then=F('points') - Value(POINTS_PER_LESSON)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            messages.info(request, f"Lesson marked incomplete. -{POINTS_PER_LESSON} points.")
            if was_course_complete:
                check_completion_and_generate_certificate(user, course, request, allow_award=False)

        # Next navigation + gating
        if action_taken:
            if action_taken in ('mark_read', 'unmark_read'):
                allow_award = (action_taken == 'mark_read')
                course_just_completed = check_completion_and_generate_certificate(user, course, request, allow_award=allow_award)
            else:
                course_just_completed = False

            # Determine next step
            all_lessons_flat = list(
                Lesson.objects.filter(module__course=course)
                .order_by('module__created_at', 'created_at')
                .values_list('pk', flat=True)
            )
            try:
                idx = all_lessons_flat.index(lesson.pk)
                next_id = all_lessons_flat[idx + 1] if idx < len(all_lessons_flat) - 1 else None

                # If this was the last lesson in its module, gate on module quiz
                last_in_module = (Lesson.objects.filter(module=lesson.module).order_by('created_at').last().pk == lesson.pk)
                if last_in_module:
                    module_quiz = lesson.module.quizzes.first()
                    if module_quiz:
                        quiz_passed = QuizAttempt.objects.filter(student=user, quiz=module_quiz, score__gte=75).exists()
                        if not quiz_passed:
                            if action_taken == 'mark_read' and not course_just_completed:
                                messages.info(request, "Module complete. Please take the module quiz (75%+ to proceed).")
                            next_url = reverse('quiz_detail', kwargs={'quiz_id': module_quiz.pk})

                # If not gated by a quiz, proceed as usual
                if not next_url:
                    if next_id:
                        next_url = reverse('lesson_detail', kwargs={'pk': next_id})
                    else:
                        # End of course: if last module has quiz and not passed, gate it; else go to course detail
                        last_module = course.modules.order_by('created_at').last()
                        final_quiz = Quiz.objects.filter(module=last_module).first() if last_module else None
                        if final_quiz:
                            quiz_passed = QuizAttempt.objects.filter(student=user, quiz=final_quiz, score__gte=75).exists()
                            if not quiz_passed:
                                if action_taken == 'mark_read' and not course_just_completed:
                                    messages.info(request, "Last lesson complete. Now, take the final quiz!")
                                next_url = reverse('quiz_detail', kwargs={'quiz_id': final_quiz.pk})
                        if not next_url:
                            if action_taken == 'mark_read' and not course_just_completed:
                                messages.success(request, f"All lessons complete in '{course.title}'.")
                            next_url = reverse('course_detail', kwargs={'pk': course.id})
            except ValueError:
                next_url = reverse('course_detail', kwargs={'pk': course.id})

        return redirect(next_url or reverse('lesson_detail', kwargs={'pk': lesson.id}))


class QuizDetailView(View):
    @method_decorator(login_required)
    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz.objects.select_related('module__course'), id=quiz_id)
        module = quiz.module
        course = module.course
        user = request.user

        if not Enrollment.objects.filter(user=user, course=course).exists():
            messages.warning(request, f"You must be enrolled in '{course.title}' to take this quiz.")
            return redirect('course_detail', pk=course.pk)

        # Require all lessons in the module to be complete before taking the quiz
        if Lesson.objects.filter(module=module).exclude(read_by_users=user).exists():
            messages.warning(request, f"Complete all lessons in '{module.title}' before taking the quiz.")
            last_unread_lesson = Lesson.objects.filter(module=module).exclude(read_by_users=user).order_by('created_at').first()
            if last_unread_lesson:
                return redirect('lesson_detail', pk=last_unread_lesson.pk)
            return redirect('course_detail', pk=course.pk)

        questions = quiz.questions.prefetch_related('answers')
        return render(request, 'quiz/quiz.html', {'quiz': quiz, 'questions': questions})


class SubmitQuizView(View):
    @method_decorator(login_required)
    @transaction.atomic
    def post(self, request, quiz_id):
        quiz = get_object_or_404(Quiz.objects.select_related('module__course'), id=quiz_id)
        module = quiz.module
        course = module.course
        user = request.user

        if not Enrollment.objects.filter(user=user, course=course).exists():
            messages.error(request, "Enrollment required to submit quiz.")
            return redirect('course_detail', pk=course.pk)

        # Lessons must be complete before submitting
        if Lesson.objects.filter(module=module).exclude(read_by_users=user).exists():
            messages.warning(request, "Complete all module lessons before submitting the quiz.")
            return redirect('quiz_detail', quiz_id=quiz.id)

        # Prepare grading
        questions = list(quiz.questions.all())
        all_answers = list(Answer.objects.filter(question__quiz=quiz))
        correct_answer_ids = {a.id for a in all_answers if a.is_correct}
        answer_text_by_id = {a.id: a.answer_text for a in all_answers}
        answers_by_question = {}
        for a in all_answers:
            answers_by_question.setdefault(a.question_id, []).append(a)

        score = 0
        total_questions = len(questions)
        question_results = []  # per-question outcome with options
        responses = {}  # NEW: store user's selections for this attempt (session only)

        # Check if user had already passed (to avoid double awarding points)
        already_passed_before = QuizAttempt.objects.filter(student=user, quiz=quiz, score__gte=75).exists()

        for q in questions:
            selected_id_str = request.POST.get(f'question_{q.id}')
            selected_id = int(selected_id_str) if selected_id_str and selected_id_str.isdigit() else None
            is_correct = (selected_id in correct_answer_ids) if selected_id else False
            if is_correct:
                score += 1

            if selected_id is not None:
                responses[str(q.id)] = selected_id  # save as strings for session-JSON compatibility

            # Build options for view-only rendering
            options = [
                {
                    'id': opt.id,
                    'text': opt.answer_text,
                    'is_correct': opt.is_correct,
                }
                for opt in answers_by_question.get(q.id, [])
            ]

            question_results.append({
                'question': q,
                'selected_answer_text': answer_text_by_id.get(selected_id) if selected_id else None,
                'selected_id': selected_id,
                'is_correct': is_correct,
                'options': options,
            })

        score_percentage = (score * 100.0 / total_questions) if total_questions > 0 else 0.0

        # Save attempt (latest attempt overwrites)
        QuizAttempt.objects.update_or_create(
            student=user, quiz=quiz,
            defaults={'score': score_percentage, 'completed': True}
        )

        # Save selections in session (no model changes)
        quiz_responses = request.session.get('quiz_responses', {})
        quiz_responses[str(quiz.id)] = responses
        request.session['quiz_responses'] = quiz_responses
        request.session.modified = True

        passed = score_percentage >= 75.0

        # Award quiz points only on first time passing this quiz
        if passed and not already_passed_before:
            Profile.objects.filter(user=user).update(points=F('points') + POINTS_PER_QUIZ)
            messages.success(request, f"Great job! +{POINTS_PER_QUIZ} points for passing the quiz.")

        # If this is the last module and now all lessons are read and quiz passed, allow course completion
        course_just_completed = False
        if passed:
            all_lessons_read = not Lesson.objects.filter(module__course=course).exclude(read_by_users=user).exists()
            last_module_in_course = course.modules.order_by('created_at').last()
            if module == last_module_in_course and all_lessons_read:
                course_just_completed = check_completion_and_generate_certificate(user, course, request, allow_award=True)

        # Determine Continue target (next module's first lesson if available, else course detail)
        continue_url = reverse('course_detail', kwargs={'pk': course.pk})
        if passed:
            ordered_module_ids = list(course.modules.order_by('created_at').values_list('pk', flat=True))
            try:
                idx = ordered_module_ids.index(module.pk)
                if idx < len(ordered_module_ids) - 1:
                    next_module_id = ordered_module_ids[idx + 1]
                    first_lesson_next = Lesson.objects.filter(module_id=next_module_id).order_by('created_at').first()
                    if first_lesson_next:
                        continue_url = reverse('lesson_detail', kwargs={'pk': first_lesson_next.pk})
                    # If next module has no lessons, fallback remains course detail
            except ValueError:
                pass

        # Final message on failure
        if not passed:
            messages.warning(request, "You did not reach the 75% pass mark. Review the module and try again.")

        return render(request, 'quiz/quiz_result.html', {
            'quiz': quiz,
            'score': score,
            'total_questions': total_questions,
            'score_percentage': score_percentage,
            'passed': passed,
            'question_results': question_results,  # includes options and selected choice
            'message': (
                "Congratulations! You passed the quiz." if passed
                else f"You scored {score_percentage:.2f}%. You need at least 75% to pass."
            ),
            'continue_url': continue_url,
            'show_marking_scheme': passed,  # Only reveal correct answers if passed
        })

    
 # --- Quizzes list (menu) ---
@method_decorator(login_required, name='dispatch')
class QuizAttemptListView(TemplateView):
    template_name = 'quiz/quiz_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempts = (QuizAttempt.objects
                    .filter(student=self.request.user)
                    .select_related('quiz__module__course')
                    .order_by('-id'))
        context['attempts'] = attempts
        return context



@method_decorator(login_required, name='dispatch')
class ReviewQuizView(View):
    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz.objects.select_related('module__course'), id=quiz_id)
        attempt = QuizAttempt.objects.filter(student=request.user, quiz=quiz).first()
        if not attempt:
            messages.info(request, "You haven't attempted this quiz yet.")
            return redirect('quiz_detail', quiz_id=quiz.id)

        module = quiz.module
        course = module.course

        total_questions = quiz.questions.count()
        score_percentage = float(attempt.score or 0.0)
        score_correct = int(round((score_percentage / 100.0) * total_questions)) if total_questions > 0 else 0
        passed = score_percentage >= 75.0

        # Pull saved selections from session (no model changes)
        resp_root = request.session.get('quiz_responses', {})
        saved = resp_root.get(str(quiz.id), {}) if isinstance(resp_root, dict) else {}
        if not saved:
            messages.info(request, "Detailed selections for this attempt are unavailable.")

        # Preload answers for building view-only blocks
        answers = Answer.objects.filter(question__quiz=quiz).select_related('question')
        answers_by_q = {}
        for a in answers:
            answers_by_q.setdefault(a.question_id, []).append(a)

        question_results = []
        for q in quiz.questions.all():
            raw = saved.get(str(q.id))
            try:
                selected_id = int(raw) if raw not in (None, '') else None
            except (TypeError, ValueError):
                selected_id = None

            opts = answers_by_q.get(q.id, [])
            options = [{'id': o.id, 'text': o.answer_text, 'is_correct': o.is_correct} for o in opts]

            sel_obj = next((o for o in opts if o.id == selected_id), None) if selected_id else None
            is_correct = (sel_obj.is_correct if sel_obj is not None else None)

            question_results.append({
                'question': q,
                'selected_answer_text': (sel_obj.answer_text if sel_obj else None),
                'selected_id': selected_id,
                'is_correct': is_correct,
                'options': options,
            })

        # Determine Continue target (next module's first lesson if available, else course detail)
        continue_url = reverse('course_detail', kwargs={'pk': course.pk})
        if passed:
            ordered_module_ids = list(course.modules.order_by('created_at').values_list('pk', flat=True))
            try:
                idx = ordered_module_ids.index(module.pk)
                if idx < len(ordered_module_ids) - 1:
                    next_module_id = ordered_module_ids[idx + 1]
                    first_lesson_next = Lesson.objects.filter(module_id=next_module_id).order_by('created_at').first()
                    if first_lesson_next:
                        continue_url = reverse('lesson_detail', kwargs={'pk': first_lesson_next.pk})
            except ValueError:
                pass

        return render(request, 'quiz/quiz_result.html', {
            'quiz': quiz,
            'score': score_correct,
            'total_questions': total_questions,
            'score_percentage': score_percentage,
            'passed': passed,
            'question_results': question_results,
            'message': (
                "Congratulations! You passed the quiz." if passed
                else f"You scored {score_percentage:.2f}%. You need at least 75% to pass."
            ),
            'continue_url': continue_url,
            'show_marking_scheme': passed,  # Only reveal correct answers if passed
        })


        # Ebooks
class EbookListView(TemplateView):
    template_name = "home/ebook_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = EbookCategory.objects.all().order_by('name').annotate(ebook_count=Count('ebooks'))
        qs = Ebook.objects.filter(published=True).select_related('category').order_by('-created_at')
        category_slug = self.request.GET.get('category')
        selected_category = None
        if category_slug:
            selected_category = EbookCategory.objects.filter(slug=category_slug).first()
            if selected_category:
                qs = qs.filter(category=selected_category)
        context.update({
            "categories": categories,
            "ebooks": qs,
            "selected_category": selected_category,
        })
        return context


@method_decorator(login_required, name='dispatch')
class EbookDetailView(View):
    def get(self, request, slug):
        ebook = get_object_or_404(Ebook.objects.select_related('category'), slug=slug, published=True)
        if not ebook.allow_preview:
            messages.warning(request, "This ebook is not available for in-site preview.")
            return redirect('ebook_list')
        stream_url = reverse('ebook_stream', args=[ebook.slug])
        return render(request, 'home/ebook_detail.html', {'ebook': ebook, 'stream_url': stream_url})


@method_decorator(login_required, name='dispatch')
class EbookStreamView(View):
    def get(self, request, slug):
        ebook = get_object_or_404(Ebook, slug=slug, published=True)
        if not ebook.allow_preview:
            return HttpResponseForbidden("Preview not allowed for this ebook.")
        if not ebook.file:
            raise Http404("Ebook file not found.")
        if not ebook.is_pdf:
            raise Http404("Ebook is not a PDF.")

        # --- UPDATED CODE ---
        # Use Django's storage-aware methods instead of os.path
        
        # 1. Check if the file exists using the storage backend
        if not ebook.file.storage.exists(ebook.file.name):
            raise Http404("File missing on server storage.")

        try:
            # 2. Open the file using the storage backend
            # This works for both local files and Cloudinary files
            resp = FileResponse(ebook.file.open('rb'), content_type='application/pdf')
            
            # --- End of updated code ---

            resp['Content-Disposition'] = 'inline'
            resp['X-Content-Type-Options'] = 'nosniff'
            resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            resp['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'self';"
            return resp
        except FileNotFoundError: # This can still happen with local storage
            raise Http404("File missing on server storage.")
        except Exception as e:
            print(f"Error serving ebook {slug}: {e}")
            return HttpResponse("Error serving file.", status=500)

@method_decorator(login_required, name='dispatch')
class CertificateListView(ListView):
    model = Certificate
    template_name = 'home/certificates.html'
    context_object_name = 'certificates'

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user).select_related('course').order_by('-issued_at')


@method_decorator(login_required, name='dispatch')
class DownloadCertificateView(View):
    def get(self, request, certificate_id):
        certificate = get_object_or_404(Certificate.objects.select_related('user', 'course'), pk=certificate_id)
        if certificate.user != request.user:
            return HttpResponseForbidden("You do not have permission to download this certificate.")

        if not certificate.certificate_file or not certificate.certificate_file.storage.exists(certificate.certificate_file.name):
            messages.error(request, "Certificate file not found or is missing. It might be generating or may have failed.")
            return redirect('certificate_list')
        try:
            response = FileResponse(certificate.certificate_file.open('rb'), content_type='application/pdf')
            course_title_safe = "".join([c if c.isalnum() else "_" for c in certificate.course.title])
            filename = f"Certificate_{course_title_safe}_{certificate.unique_id}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except FileNotFoundError:
            messages.error(request, "Certificate file could not be found on the server.")
            return redirect('certificate_list')
        except Exception:
            messages.error(request, "An error occurred while trying to download the certificate.")
            return redirect('certificate_list')