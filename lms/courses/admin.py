from django.contrib import admin
from django.db.models import Count
from .models import Course, Module, Lesson, Enrollment, Video, AdditionalMaterial, Note, Ebook, EbookCategory, Certificate
from .forms import CourseForm, ModuleForm, LessonForm

# Inlines (one level only; Django does not support nested inlines)
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ['title', 'image_content', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0
    fields = ['title', 'image_content', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True

class VideoInline(admin.TabularInline):
    model = Video
    extra = 0
    fields = ['title', 'video_url', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True

class AdditionalMaterialInline(admin.TabularInline):
    model = AdditionalMaterial
    extra = 0
    fields = ['title', 'material_url', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True

# Course admin
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseForm
    list_display = ('title', 'category', 'created_by', 'modules_count', 'lessons_count', 'enrolled_count', 'created_at')
    list_filter = ('category', 'created_by', 'created_at')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'
    inlines = [ModuleInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _modules_count=Count('modules', distinct=True),
            _lessons_count=Count('modules__lessons', distinct=True),
            _enrolled_count=Count('enrolled_students', distinct=True),
        )

    def modules_count(self, obj):
        return getattr(obj, '_modules_count', 0)
    modules_count.short_description = 'Modules'

    def lessons_count(self, obj):
        return getattr(obj, '_lessons_count', 0)
    lessons_count.short_description = 'Lessons'

    def enrolled_count(self, obj):
        return getattr(obj, '_enrolled_count', 0)
    enrolled_count.short_description = 'Enrolled'

# Module admin
@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    form = ModuleForm
    list_display = ('title', 'course', 'lessons_count', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('title', 'course__title')
    date_hierarchy = 'created_at'
    inlines = [LessonInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_lessons_count=Count('lessons', distinct=True))

    def lessons_count(self, obj):
        return getattr(obj, '_lessons_count', 0)
    lessons_count.short_description = 'Lessons'

# Lesson admin
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    form = LessonForm
    list_display = ('title', 'module', 'videos_count', 'materials_count', 'created_at')
    list_filter = ('module__course', 'module', 'created_at')
    search_fields = ('title', 'module__title', 'module__course__title')
    date_hierarchy = 'created_at'
    inlines = [VideoInline, AdditionalMaterialInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _videos_count=Count('videos', distinct=True),
            _materials_count=Count('additional_materials', distinct=True),
        )

    def videos_count(self, obj):
        return getattr(obj, '_videos_count', 0)
    videos_count.short_description = 'Videos'

    def materials_count(self, obj):
        return getattr(obj, '_materials_count', 0)
    materials_count.short_description = 'Materials'

# Simple admin for related models
@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'created_at')
    list_filter = ('lesson__module__course', 'lesson')
    search_fields = ('title', 'lesson__title')
    date_hierarchy = 'created_at'

@admin.register(AdditionalMaterial)
class AdditionalMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'created_at')
    list_filter = ('lesson__module__course', 'lesson')
    search_fields = ('title', 'lesson__title')
    date_hierarchy = 'created_at'

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'date_enrolled']
    search_fields = ['user__email', 'course__title']
    list_filter = ['date_enrolled', 'course', 'user']
    date_hierarchy = 'date_enrolled'
    autocomplete_fields = ('user', 'course')
    list_select_related = ('user', 'course')

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'short_content', 'updated_at')
    search_fields = ('user__email', 'lesson__title', 'content')
    list_filter = ('updated_at', 'lesson__module__course')
    date_hierarchy = 'updated_at'

    def short_content(self, obj):
        text = (obj.content or '').strip()
        return (text[:60] + '...') if len(text) > 60 else text
    short_content.short_description = 'Content'

@admin.register(EbookCategory)
class EbookCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

@admin.register(Ebook)
class EbookAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'uploaded_by', 'published', 'allow_preview', 'created_at')
    list_filter = ('published', 'allow_preview', 'category', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'cover_image', 'file', 'category', 'uploaded_by')
        }),
        ('Publication', {
            'fields': ('published', 'allow_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'issued_at', 'has_file', 'unique_id')
    list_filter = ('issued_at', 'course')
    search_fields = ('user__email', 'course__title', 'unique_id')
    date_hierarchy = 'issued_at'
    readonly_fields = ('unique_id',)

    def has_file(self, obj):
        return bool(obj.certificate_file)
    has_file.boolean = True
    has_file.short_description = 'File'