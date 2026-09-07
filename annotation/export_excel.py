from openpyxl import Workbook
from django.http import HttpResponse
from django.db.models import Prefetch
from .models import FrameAnnotation
from .models import SequenceRating

def export_annotations_excel(request):

    wb = Workbook()

    ws = wb.active
    ws.title = "Annotations"
    headers = [
    "device_ID",
    "date",
    "farm_name",
    "cow_name",
    "original_image_path",
    "cropped_image_path",
    "hoof_label",
    "score_type",
    "Score",
    "Camera",
    "bb_x1",
    "bb_y1",
    "bb_x2",
    "bb_y2",
    "User",
    ]

    ws.append(headers)
    ratings = (
    SequenceRating.objects
    .exclude(user__role="tester") 
    .select_related(
        "user",
        "rating_target",
        "rating_target__sequence",
        "rating_target__sequence__cow",
        "rating_target__sequence__cow__farm",
    )
    .prefetch_related(
        Prefetch(
            "rating_target__annotations",
            queryset=FrameAnnotation.objects.select_related(
                "frame",
                "frame__view",
            )
        )
    )
)
    for rating in ratings:

        farm = rating.rating_target.sequence.cow.farm
        cow = rating.rating_target.sequence.cow

        for annotation in rating.rating_target.annotations.all():

            frame = annotation.frame
            view = frame.view
            record_date = farm.record_date

            if record_date is not None:
                record_date = record_date.replace(tzinfo=None)
            target_type = annotation.rating_target.target_type

            if target_type.startswith("SIDE"):
                score_type = "Foot angle"
            else:
                score_type = "Claw set"

            if rating.score == 0:
                rating.score = '?'
                
            ws.append([
                farm.device_id,
                record_date,
                farm.name,
                cow.name,
                frame.image.name,
                annotation.cropped_image.name,
                annotation.hoof_label,
                score_type,
                rating.score,   
                view.camera,
                annotation.x1,
                annotation.y1,
                annotation.x2,
                annotation.y2,
                f"{rating.user.first_name} {rating.user.last_name}".strip(),
            ])
    
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = (
        'attachment; filename="dataset.xlsx"'
    )

    wb.save(response)

    return response