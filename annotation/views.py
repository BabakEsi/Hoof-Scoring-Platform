from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from annotation.models import Farm, Cow, Sequence, SequenceRating, Frame, RatingTarget, FrameAnnotation

import zipfile
import tempfile
import random
from django.db.models import Exists, OuterRef, Count, Q
from pathlib import Path
from annotation.services.dataset_importer import DatasetImporter
from django.http import JsonResponse
from django.contrib import messages
from annotation.services.loaders.zip_loader import ZipLoader
from .services.directory_loader import DirectoryLoader
from accounts.models import User

def home(request):

    return render(request, 'home.html')

def farm_list_view(request):

    farms = Farm.objects.prefetch_related("cows").all()

    return render(
        request,
        "annotation/farms.html",
        {
            "farms": farms
        }
    )

def cow_detail_view(request, cow_id):

    cow = get_object_or_404(
        Cow.objects.prefetch_related("sequences"),
        id=cow_id
    )

    return render(
        request,
        "annotation/cow_detail.html",
        {
            "cow": cow
        }
    )



@login_required
def annotate_view(request):
    

    mode = request.GET.get("mode")

    history = request.session.get("annotation_history", [])
    current_index = request.session.get("annotation_index", -1)



    if request.method == "POST":

        target = get_object_or_404(
            RatingTarget,
            id=request.POST.get("target_id")
        )

        score = request.POST.get("score")

        if not score:
            messages.error(request, "Please select a rating.")
            return redirect(f"{request.path}?mode={mode}")

        SequenceRating.objects.update_or_create(
            user=request.user,
            rating_target=target,
            defaults={
                "score": int(score)
            }
        )
        sequence = target.sequence

        valid_targets = sequence.rating_targets.annotate(
            num_annotations=Count("annotations")
        ).filter(
            num_annotations__gt=0
        )

        total_targets = valid_targets.count()

        rated_targets = SequenceRating.objects.filter(
            user=request.user,
            rating_target__in=valid_targets
        ).values(
            "rating_target"
        ).distinct().count()

       

        if total_targets == rated_targets:
            sequence.status = "completed"
            sequence.save(update_fields=["status"])

        return redirect(f"{request.path}?mode={mode}")

    # ------------------------
    # TARGETS NOT RATED
    # ------------------------
    rated = SequenceRating.objects.filter(
        user=request.user,
        rating_target=OuterRef("pk")
    )

    targets = (
        RatingTarget.objects
        .annotate(
            already_rated=Exists(rated),
            num_annotations=Count("annotations")
        )
        .filter(
            already_rated=False,
            num_annotations__gt=0
        )
    )

    if mode == "Foot angle":
        targets = targets.filter(
            target_type__startswith="SIDE"
        )

    elif mode == "Claw set":
        targets = targets.filter(
            target_type__startswith="FRONT"
        )

    # ------------------------
    # FARM
    # ------------------------
    farm = (
        Farm.objects
        .filter(
            cows__sequences__rating_targets__in=targets
        )
        .distinct()
        .order_by("id")
        .first()
    )

    if not farm:
        request.session.pop("annotation_history", None)
        request.session.pop("annotation_index", None)
        return render(request, "annotation/finished.html")

    targets = targets.filter(
        sequence__cow__farm=farm
    )

    if not targets.exists():
        request.session.pop("annotation_history", None)
        request.session.pop("annotation_index", None)
        return render(request, "annotation/finished.html")

    # ------------------------
    # PREVIOUS
    # ------------------------
    back = request.GET.get("back")

    if back and current_index > 0:

        current_index -= 1
        request.session["annotation_index"] = current_index

        target = get_object_or_404(
            RatingTarget,
            id=history[current_index]
        )

    else:

        target = random.choice(list(targets))

        history = history[:current_index + 1]

        history.append(target.id)

        current_index += 1

        request.session["annotation_history"] = history
        request.session["annotation_index"] = current_index

    # ------------------------
    # IMAGES
    # ------------------------
    annotations = (
        FrameAnnotation.objects
        .filter(rating_target=target)
        .select_related("frame")
        .order_by("frame__frame_number")
    )

    images = [
        {
            "cropped": a.cropped_image.url,
            "original": a.frame.image.url,
        }
        for a in annotations
    ]

    image_urls = [
        a.cropped_image.url
        for a in annotations
    ]

    current_rating = SequenceRating.objects.filter(
        user=request.user,
        rating_target=target
    ).first()

    return render(
        request,
        "annotation/annotate.html",
        {
            "farm": farm,
            "cow": target.sequence.cow,
            "target": target,
            "annotations": annotations,
            "image_urls": image_urls,
            "images": images,
            "mode": mode,
            "score_range": range(1, 10),
            "current_rating": current_rating,
            "can_go_back": current_index > 0,
        },
    )

#############ADMIN####################

@login_required
def create_farm(request):

    if request.user.role != "admin":
        return redirect("accounts:dashboard")

    if request.method == "POST":

        name = request.POST.get("name")
        description = request.POST.get("description")

        Farm.objects.create(
            name=name,
            description=description
        )

        return redirect("accounts:dashboard")

    return render(request, "annotation/create_farm.html")




@login_required
def edit_farm(request, farm_id):

    if request.user.role != "admin":
        return redirect("accounts:dashboard")

    farm = get_object_or_404(Farm, id=farm_id)

    if request.method == "POST":

        farm.name = request.POST.get("name")
        farm.description = request.POST.get("description")
        farm.save()

        return redirect("accounts:dashboard")

    return render(request, "annotation/edit_farm.html", {
        "farm": farm
    })

@login_required
def delete_farm(request, farm_id):

    if request.user.role != "admin":
        return redirect("accounts:dashboard")

    farm = get_object_or_404(Farm, id=farm_id)

    if request.method == "POST":
        farm.delete()
        return redirect("accounts:dashboard")

    return redirect("accounts:dashboard")


@login_required
def create_cow(request):

    if request.user.role != "admin":
        return redirect("accounts:dashboard")

    farms = Farm.objects.all()

    # 👇 گرفتن farm از URL
    preselected_farm_id = request.GET.get("farm")
    preselected_farm = None

    if preselected_farm_id:
        preselected_farm = Farm.objects.filter(id=preselected_farm_id).first()

    if request.method == "POST":

        name = request.POST.get("name")
        farm_id = request.POST.get("farm")

        farm = Farm.objects.get(id=farm_id)

        Cow.objects.create(
            name=name,
            farm=farm,
            uploaded_by=request.user
        )

        return redirect("accounts:dashboard")

    return render(request, "annotation/create_cow.html", {
        "farms": farms,
        "preselected_farm": preselected_farm
    })


@login_required
def farm_detail_admin(request, farm_id):

    # 🚨 فقط ادمین
    if request.user.role != "admin":
        return redirect("accounts:dashboard")  # یا 403

    farm = get_object_or_404(Farm, id=farm_id)
    cows = farm.cows.prefetch_related("sequences").all()

    return render(request, "annotation/farm_detail_admin.html", {
        "farm": farm,
        "cows": cows
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Cow


@login_required
def cow_parts_admin(request, cow_id):

    cow = get_object_or_404(
        Cow.objects.select_related("farm"),
        id=cow_id
    )

    sequence = cow.sequences.first()

    if not sequence:
        parts = []

    elif sequence.camera_setup == "3":

        parts = [
            ("FRONT1", "Front 1"),
            ("FRONT2", "Front 2"),
            ("SIDE", "Side"),
            ("MIXED_FRONT", "Mixed Front"),
        ]

    else:

        parts = [
            ("FRONT", "Front"),
            ("SIDE", "Side"),
        ]

    return render(
        request,
        "annotation/cow_parts_admin.html",
        {
            "cow": cow,
            "parts": parts,
        }
    )


@login_required
def part_targets_admin(request, cow_id, code):

    cow = get_object_or_404(Cow, id=cow_id)

    if code == "SIDE":

        targets = (
            RatingTarget.objects
            .filter(
                sequence__cow=cow,
                target_type__startswith="SIDE",
                annotations__frame__view__camera="SIDE",
            )
            .annotate(
                num_annotations=Count("annotations", distinct=True)
            )
        )

    elif code in ["FRONT1", "FRONT2"]:

        targets = (
            RatingTarget.objects
            .filter(
                sequence__cow=cow,
                target_type__startswith="FRONT_PAIR",
                annotations__frame__view__camera=code,
            )
            .annotate(
                num_annotations=Count("annotations", distinct=True)
            )
        )

    elif code == "MIXED_FRONT":

        targets = (
            RatingTarget.objects
            .filter(
                sequence__cow=cow,
                target_type__startswith="FRONT_PAIR",
            )
            .annotate(
                num_annotations=Count(
                    "annotations",
                    filter=Q(
                        annotations__frame__view__camera__in=[
                            "FRONT1",
                            "FRONT2",
                        ]
                    ),
                    distinct=True,
                )
            )
        )

    else:
        targets = RatingTarget.objects.none()

        targets = (
        targets
        .filter(num_annotations__gt=0)
        .distinct()
    )

    for target in targets:

        suffix = target.target_type.split("_")[-1]

        if code == "MIXED_FRONT":
            mapping = {
                "F1": "FR",
                "F2": "FL",
                "B1": "BR",
                "B2": "BL",
            }
        else:
            mapping = {
                "F1": "F1",
                "F2": "F2",
                "B1": "B1",
                "B2": "B2",
            }

        target.short_name = mapping.get(suffix, suffix)

    return render(
        request,
        "annotation/part_targets_admin.html",
        {
            "cow": cow,
            "camera": code,
            "code": code,
            "targets": targets,
        },
    )
@login_required
def target_detail_admin(request, cow_id, target_id):

    cow = get_object_or_404(Cow, id=cow_id)
    target = get_object_or_404(RatingTarget, id=target_id)

    camera = request.GET.get("camera")

    annotations = list(
        FrameAnnotation.objects
        .filter(
            rating_target=target,
            frame__view__camera=camera,
        )
        .select_related("frame")
        .order_by("frame__frame_number")
    )

    index = max(0, int(request.GET.get("i", 0)))

    if index >= len(annotations):
        index = len(annotations) - 1 if annotations else 0

    current_annotation = (
        annotations[index]
        if annotations else None
    )

    ratings = (
        SequenceRating.objects
        .filter(rating_target=target)
        .select_related("user")
        .order_by("-created_at")
    )


    # فقط برای Mixed Front تغییر نام بده
    if camera == "MIXED_FRONT":

        mapping = {
            "F1": "FR",
            "F2": "FL",
            "B1": "BR",
            "B2": "BL",
        }

    else:

        mapping = {
            "F1": "F1",
            "F2": "F2",
            "B1": "B1",
            "B2": "B2",
        }


    # Rating names
    for rating in ratings:

        name = rating.rating_target.get_target_type_display()

        for old, new in mapping.items():
            name = name.replace(old, new)

        rating.display_target = name


    # Header target name
    suffix = target.target_type.split("_")[-1]

    target.short_name = mapping.get(
        suffix,
        suffix
    )


    return render(
        request,
        "annotation/target_detail_admin.html",
        {
            "cow": cow,
            "target": target,
            "current_annotation": current_annotation,
            "index": index,
            "total": len(annotations),
            "ratings": ratings,
            "camera": camera,
        },
    )

@login_required
def mixed_front_admin(request, cow_id):

    cow = get_object_or_404(Cow, id=cow_id)

    targets = (
        RatingTarget.objects
        .filter(
            sequence__cow=cow,
            target_type__startswith="FRONT_PAIR",
        )
        .annotate(
            num_annotations=Count("annotations")
        )
        .filter(num_annotations__gt=0)
        .distinct()
    )

    return render(
        request,
        "annotation/mixed_front_target_detail_admin.html",
        {
            "cow": cow,
            "targets": targets,
        },
    )

@login_required
def mixed_front_target_detail_admin(request, cow_id, target_id):

    cow = get_object_or_404(
        Cow,
        id=cow_id,
    )

    target = get_object_or_404(
        RatingTarget,
        id=target_id,
        sequence__cow=cow,
    )

    # -------------------------
    # Images
    # -------------------------
    front1 = list(
        FrameAnnotation.objects
        .filter(
            rating_target=target,
            frame__view__camera="FRONT1",
        )
        .select_related("frame")
        .order_by("frame__frame_number")
    )

    front2 = list(
        FrameAnnotation.objects
        .filter(
            rating_target=target,
            frame__view__camera="FRONT2",
        )
        .select_related("frame")
        .order_by("frame__frame_number")
    )

    total = max(len(front1), len(front2))

    index = max(
        0,
        int(request.GET.get("i", 0))
    )

    if total:
        index = min(index, total - 1)

    left = front1[index] if index < len(front1) else None
    right = front2[index] if index < len(front2) else None

    # -------------------------
    # Ratings
    # -------------------------
    ratings = (
        SequenceRating.objects
        .filter(rating_target=target)
        .select_related("user")
        .order_by("-created_at")
    )
    mapping = {
    "F1": "FR",
    "F2": "FL",
    "B1": "BR",
    "B2": "BL",
}

    suffix = target.target_type.split("_")[-1]
    target.short_name = mapping.get(suffix, suffix)

    for rating in ratings:
        rating.display_target = (
            rating.rating_target.get_target_type_display()
            .replace("F1", "FR")
            .replace("F2", "FL")
            .replace("B1", "BR")
            .replace("B2", "BL")
        )
    return render(
        request,
        "annotation/mixed_front_target_detail_admin.html",
        {
            "cow": cow,
            "target": target,
            "left": left,
            "right": right,
            "index": index,
            "total": total,
            "ratings": ratings,
        },
    )

@login_required
def upload_dataset(request):

    if request.user.role != "admin":
        return redirect("accounts:dashboard")

    if request.method != "POST":
        return redirect("accounts:dashboard")

    zip_file = request.FILES.get("zip_file")
    dataset_path = request.POST.get("dataset_path", "").strip()

    if not zip_file and not dataset_path:
        messages.error(
            request,
            "Please upload a ZIP file or provide a dataset directory."
        )
        return redirect("accounts:dashboard")

    if zip_file and dataset_path:
        messages.error(
            request,
            "Please choose either a ZIP file or a dataset directory."
        )
        return redirect("accounts:dashboard")

    if zip_file:
        loader = ZipLoader(zip_file)
    else:
        loader = DirectoryLoader(dataset_path)

    importer = DatasetImporter(
        loader=loader,
        user=request.user,
    )

    importer.run()

    messages.success(
        request,
        "✅ Dataset imported successfully."
    )

    return redirect("accounts:dashboard")

@login_required
def ratings_admin(request):
    if request.user.role != "admin":
        return redirect("accounts:dashboard")

    ratings = (
        SequenceRating.objects
        .select_related(
            "user",
            "rating_target",
            "rating_target__sequence",
            "rating_target__sequence__cow",
            "rating_target__sequence__cow__farm",
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "annotation/ratings_admin.html",
        {
            "ratings": ratings,
        }
    )

@login_required
def delete_rating(request, rating_id):

    if request.user.role != "admin":
        return redirect("accounts:dashboard")

    rating = get_object_or_404(
        SequenceRating,
        id=rating_id
    )

    if request.method == "POST":
        rating.delete()
        messages.success(request, "Rating deleted successfully.")

    return redirect("annotation:ratings_admin")