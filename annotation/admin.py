from django.contrib import admin

from .models import (
    Farm,
    Cow,
    Sequence,
    CameraView,
    Frame,
    FrameAnnotation,
    RatingTarget,
    SequenceRating,
    ImportedJson
)


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'name',
        'record_date',
        'created_at',
    )

    search_fields = (
        'name',
    )

    list_filter = (
        'created_at',
    )


@admin.register(Cow)
class CowAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'name',
        'farm',
        'uploaded_by',
        'created_at',
    )

    search_fields = (
        'name',
    )

    list_filter = (
        'farm',
        'created_at',
    )


class CameraViewInline(admin.TabularInline):
    model = CameraView
    extra = 0


class RatingTargetInline(admin.TabularInline):
    model = RatingTarget
    extra = 0


@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'cow',
        'camera_setup',
        'status',
        'total_frames',
        'created_at',
    )

    search_fields = (
        'cow__name',
    )

    list_filter = (
        'camera_setup',
        'status',
        'created_at',
    )

    inlines = [
        CameraViewInline,
        RatingTargetInline,
    ]


class FrameInline(admin.TabularInline):
    model = Frame
    extra = 0


@admin.register(CameraView)
class CameraViewAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'sequence',
        'camera',
    )

    list_filter = (
        'camera',
    )

    search_fields = (
        'sequence__cow__name',
    )

    inlines = [
        FrameInline,
    ]


class FrameAnnotationInline(admin.TabularInline):
    model = FrameAnnotation
    extra = 0


@admin.register(Frame)
class FrameAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'view',
        'frame_number',
    )

    search_fields = (
        'view__sequence__cow__name',
    )

    list_filter = (
        'view__camera',
    )

    inlines = [
        FrameAnnotationInline,
    ]


@admin.register(RatingTarget)
class RatingTargetAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'sequence',
        'target_type',
    )

    search_fields = (
        'sequence__cow__name',
    )

    list_filter = (
        'target_type',
    )


@admin.register(FrameAnnotation)
class FrameAnnotationAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'frame',
        'rating_target',
    )

    search_fields = (
        'frame__view__sequence__cow__name',
    )

    list_filter = (
        'rating_target',
    )


@admin.register(SequenceRating)
class SequenceRatingAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'rating_target',
        'score',
        'created_at',
    )

    search_fields = (
        'user__email',
        'rating_target__sequence__cow__name',
    )

    list_filter = (
        'score',
        'created_at',
    )

@admin.register(ImportedJson)
class ImportedJsonAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "farm",
        "file_path",
        "status",
        "processed_at",
        "created_at",
    )

    search_fields = (
        "file_path",
        "file_hash",
        "farm__name",
    )

    list_filter = (
        "status",
        "farm",
        "created_at",
    )

    readonly_fields = (
        "file_hash",
        "processed_at",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

   