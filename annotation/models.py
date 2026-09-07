from django.db import models
from django.conf import settings
# from .services.image_utils import OverwriteStorage

class Farm(models.Model):

    name = models.CharField(max_length=255)
    device_id = models.CharField(max_length=255)
    description = models.TextField(
        blank=True,
        null=True
    )

    record_date = models.DateTimeField(
        blank=True,
        null=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


class Cow(models.Model):

    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name="cows"
    )

    name = models.CharField(max_length=100)

    main_image = models.ImageField(
        upload_to="cow_images/",
        blank=True,
        null=True
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ("farm", "name")

    def __str__(self):
        return self.name

class ImportedJson(models.Model):

    STATUS = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name="json_files"
    )

    file_path = models.TextField()

    file_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending",
    )

    processed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    error_message = models.TextField(
    blank=True,
    default=""
    )

class Sequence(models.Model):

    CAMERA_SETUP_CHOICES = [
        ("2", "Two Cameras"),
        ("3", "Three Cameras"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("reviewed", "Reviewed"),
    ]

    cow = models.ForeignKey(
        Cow,
        on_delete=models.CASCADE,
        related_name="sequences"
    )

    camera_setup = models.CharField(
        max_length=1,
        choices=CAMERA_SETUP_CHOICES
    )

    total_frames = models.PositiveIntegerField(
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.cow.name} - {self.get_camera_setup_display()}"


class CameraView(models.Model):

    CAMERA_CHOICES = [
        ("FRONT1", "Front 1"),
        ("FRONT2", "Front 2"),
        ("SIDE", "Side"),
    ]

    sequence = models.ForeignKey(
        Sequence,
        on_delete=models.CASCADE,
        related_name="views"
    )

    camera = models.CharField(
        max_length=10,
        choices=CAMERA_CHOICES
    )

    class Meta:
        unique_together = ("sequence", "camera")

    def __str__(self):
        return f"{self.sequence} - {self.get_camera_display()}"


class Frame(models.Model):

    view = models.ForeignKey(
        CameraView,
        on_delete=models.CASCADE,
        related_name="frames"
    )

    frame_number = models.PositiveIntegerField()

    def original_path(instance, filename):
        return (
            f"originals/"
            f"{instance.view.sequence.cow.farm.name}/"
            f"{instance.view.sequence.cow.name}/"
            f"{instance.view.camera}/"
            f"{filename}"
        )

    image = models.ImageField(
        upload_to=original_path,
        # storage=OverwriteStorage(),
        max_length=255
    )
    

    class Meta:
        ordering = ["frame_number"]
        unique_together = ("view", "frame_number")

    def __str__(self):
        return f"{self.view} - Frame {self.frame_number}"


class RatingTarget(models.Model):

    TARGET_CHOICES = [

        # Three camera setup
        ("FRONT_PAIR_F1", "Front Pair F1"),
        ("FRONT_PAIR_F2", "Front Pair F2"),
        ("FRONT_PAIR_B1", "Front Pair B1"),
        ("FRONT_PAIR_B2", "Front Pair B2"),

        ("SIDE_F1", "Side F1"),
        ("SIDE_F2", "Side F2"),
        ("SIDE_B1", "Side B1"),
        ("SIDE_B2", "Side B2"),

        # Two camera setup
        ("FRONT_F1", "Front F1"),
        ("FRONT_F2", "Front F2"),
        ("FRONT_B1", "Front B1"),
        ("FRONT_B2", "Front B2"),
    ]

    sequence = models.ForeignKey(
        Sequence,
        on_delete=models.CASCADE,
        related_name="rating_targets"
    )

    source_zip = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    target_type = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES
    )

    class Meta:
        unique_together = ("sequence", "target_type")

    def __str__(self):
        return self.get_target_type_display()


class FrameAnnotation(models.Model):

    frame = models.ForeignKey(
        Frame,
        on_delete=models.CASCADE,
        related_name="annotations"
    )
    hoof_label = models.CharField(max_length=2)
    
    x1 = models.PositiveIntegerField()
    y1 = models.PositiveIntegerField()
    x2 = models.PositiveIntegerField()
    y2 = models.PositiveIntegerField()

    rating_target = models.ForeignKey(
        RatingTarget,
        on_delete=models.CASCADE,
        related_name="annotations"
    )

    def cropped_path(instance, filename):
        target = instance.rating_target.target_type

        # FRONT_PAIR_F1 -> F1
        # SIDE_B2 -> B2
        # FRONT_F1 -> F1
        hoof = target.split("_")[-1]

        return (
            f"cropped/"
            f"{instance.frame.view.sequence.cow.farm.name}/"
            f"{instance.frame.view.sequence.cow.name}/"
            f"{instance.frame.view.camera}/"
            f"{hoof}/"
            f"{filename}"
        )

    cropped_image = models.ImageField(
        upload_to=cropped_path,
        # storage=OverwriteStorage(),
        max_length=255
    )
    


class SequenceRating(models.Model):

    SCORE_CHOICES = [
        (0, "No Opinion"),
        (1, "1"),
        (2, "2"),
        (3, "3"),
        (4, "4"),
        (5, "5"),
        (6, "6"),
        (7, "7"),
        (8, "8"),
        (9, "9"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    rating_target = models.ForeignKey(
        RatingTarget,
        on_delete=models.CASCADE,
        related_name="ratings"
    )
   

    score = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ("user", "rating_target")

    def __str__(self):
        return f"{self.rating_target} - {self.score}"