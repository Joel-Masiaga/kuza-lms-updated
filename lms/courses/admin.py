from django.contrib import admin
from django.db.models import Count
from .models import (
    Course, Module, Lesson, Enrollment, Video, AdditionalMaterial, 
    Note, Ebook, EbookCategory, Certificate
)
# The forms are assumed to be correctly set up for TinyMCE
from .forms import CourseForm, ModuleForm, LessonForm 

# Inlines (one level only; Django does not support nested inlines)
# No changes needed to inlines
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ['title', 'image_content', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True
    autocomplete_fields = ['module'] # Added for consistency

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0
    fields = ['title', 'image_content', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True
    autocomplete_fields = ['course'] # Added for consistency

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
    search_fields = ('title', 'description', 'created_by__email')
    date_hierarchy = 'created_at'
    inlines = [ModuleInline]
    
    # NEW: Organize the detail page
    readonly_fields = ['created_at']
    autocomplete_fields = ['created_by']
    fieldsets = (
        (None, {
            'fields': ('title', 'category', 'image')
        }),
        ('Content', {
            'fields': ('description', 'objectives')
        }),
        ('Administration', {
            'fields': ('created_by', 'created_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        When creating a new course, set the created_by
        field to the current user.
        """
        if not obj.pk: # This means the object is new (not being changed)
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

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
    
    # NEW: Organize the detail page
    readonly_fields = ['created_at']
    autocomplete_fields = ['course']
    fieldsets = (
        (None, {
            'fields': ('course', 'title', 'image_content')
        }),
        ('Content', {
            'fields': ('description', 'objectives', 'content')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

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
    list_display = ('title', 'module', 'lesson_type', 'videos_count', 'materials_count', 'created_at')
    list_filter = ('module__course', 'module', 'created_at')
    search_fields = ('title', 'module__title', 'module__course__title')
    date_hierarchy = 'created_at'
    inlines = [VideoInline, AdditionalMaterialInline]
    
    # NEW: Organize the detail page
    readonly_fields = ['created_at']
    autocomplete_fields = ['module']
    filter_horizontal = ['read_by_users'] # Better UI for ManyToMany
    fieldsets = (
        (None, {
            'fields': ('module', 'title', 'image_content')
        }),
        ('Content', {
            'fields': ('description', 'objectives', 'content', 'pdf_file')
        }),
        ('Tracking', {
            'fields': ('read_by_users',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('module__course').prefetch_related('videos').annotate(
            _videos_count=Count('videos', distinct=True),
            _materials_count=Count('additional_materials', distinct=True),
        )

    # NEW: Add lesson_type to list_display (from model @property)
    def lesson_type(self, obj):
        return obj.lesson_type
    lesson_type.short_description = 'Type'

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
    
    # NEW: Add fields for detail view
    fields = ('lesson', 'title', 'video_url', 'created_at')
    readonly_fields = ['created_at']
    autocomplete_fields = ['lesson']

@admin.register(AdditionalMaterial)
class AdditionalMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'created_at')
    list_filter = ('lesson__module__course', 'lesson')
    search_fields = ('title', 'lesson__title')
    date_hierarchy = 'created_at'
    
    # NEW: Add fields for detail view
    fields = ('lesson', 'title', 'material_url', 'created_at')
    readonly_fields = ['created_at']
    autocomplete_fields = ['lesson']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'date_enrolled']
    search_fields = ['user__email', 'course__title']
    list_filter = ['date_enrolled', 'course']
    date_hierarchy = 'date_enrolled'
    autocomplete_fields = ('user', 'course')
    list_select_related = ('user', 'course')
    
    # NEW: Make auto-generated dates readonly
    readonly_fields = ['date_enrolled', 'created_at']
    fields = ('user', 'course', 'date_enrolled', 'created_at')


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'short_content', 'updated_at')
    search_fields = ('user__email', 'lesson__title', 'content')
    list_filter = ('updated_at', 'lesson__module__course')
    date_hierarchy = 'updated_at'
    
    # NEW: Organize detail page
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['user', 'lesson']
    fieldsets = (
        (None, {
            'fields': ('user', 'lesson', 'content')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

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
    # This admin is simple and complete, no changes needed.

@admin.register(Ebook)
class EbookAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'uploaded_by', 'published', 'allow_preview', 'created_at')
    list_filter = ('published', 'allow_preview', 'category', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}
    
    # NEW: Add autocomplete fields
    autocomplete_fields = ['category', 'uploaded_by']
    
    # This fieldset is already excellent and covers all fields
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
    
    # `unique_id` is readonly from model, but explicit is good
    readonly_fields = ('unique_id',) 
    
    # NEW: Add autocomplete and fieldsets
    autocomplete_fields = ['user', 'course']
    fieldsets = (
        (None, {
            'fields': ('user', 'course', 'issued_at', 'certificate_file', 'unique_id')
        }),
    )

    def has_file(self, obj):
        return bool(obj.certificate_file)
    has_file.boolean = True
    has_file.short_description = 'File'