from .rating_mapper import get_rating_target
import numpy as np
import os
import cv2
from datetime import datetime
from django.core.files.storage import default_storage
from pathlib import Path
from django.utils import timezone
from annotation.models import ImportedJson
from .filename_parser import parse_filename
from .image_utils import (
    image_from_base64,
    clamp_bbox,
    save_pil_to_imagefield,
    # generate_unique_name
)

from annotation.models import (
    Farm,
    Cow,
    Sequence,
    CameraView,
    Frame,
    FrameAnnotation,
    RatingTarget
)


# ---------------------------
# BLUR DETECTOR
# ---------------------------

def normalize_label(label, include_m=False):
    label = (
        str(label)
        .strip()
        .lower()
        .replace("`", "")
        .replace("'", "")
        .replace('"', "")
    )

    if not include_m and label.endswith("m"):
        return None

    return label

def is_blurry(image, threshold=80):
    img = np.array(image.convert("L"))
    score = cv2.Laplacian(img, cv2.CV_64F).var()
    return score < threshold


class DatasetImporter:

 
    def __init__(self, loader, user):
        self.loader = loader
        self.camera_setup = None
        self.user = user

        self.cows_cache = {}
        self.sequences = {}
        self.views = {}
        self.rating_targets = {}

    # ---------------------------
    # RUN
    # ---------------------------

    def run(self):
        self.load_json_files()
        self.prepare_structure()
        self.detect_camera_setup()
        self.process_json_files()

    # ---------------------------
    # LOAD
    # ---------------------------

    def load_json_files(self):
        self.loader.load()

        try:
            self.json_items = list(self.loader)
        finally:
            self.loader.close()

        if not self.json_items:
            raise ValueError("No JSON files found")

    # ---------------------------
    # FARM ONLY
    # ---------------------------

    def prepare_structure(self):
        info = parse_filename(self.json_items[0]["path"].split("/")[-1])

        record_date = timezone.make_aware(
            datetime.strptime(
                f"{info['export_date']} {info['export_time']}",
                "%Y%m%d %H%M%S"
            )
        )
        self.farm, created = Farm.objects.get_or_create(
            name=info["farm"],
             defaults={
            "record_date": record_date,
            "device_id": info["camera_id"],
            }
        )

        # اگر فارم از قبل وجود داشت ولی record_date خالی بود
        if not created and self.farm.record_date is None:
            self.farm.record_date = record_date
            self.farm.save(update_fields=["record_date"])

    def detect_camera_setup(self):

        camera_alias = {
            "hoof_front1": "front1",
            "hoof_front2": "front2",
            "hoof_side": "side",
        }

        cameras = set()

        for item in self.json_items:
            info = parse_filename(item["path"].split("/")[-1])

            cam = camera_alias.get(info["camera"].lower())

            if cam:
                cameras.add(cam)

        self.camera_setup = "3" if "front2" in cameras else "2"

        print("Camera setup:", self.camera_setup)

    


    # ---------------------------
    # INIT PER COW
    # ---------------------------

    def get_system(self, cow_name):

        if cow_name in self.sequences:
            return

        cow, _ = Cow.objects.get_or_create(
            name=cow_name,
            farm=self.farm,
            defaults={"uploaded_by": self.user}
        )

        self.cows_cache[cow_name] = cow

        sequence = Sequence.objects.create(
            cow=cow,
            camera_setup=self.camera_setup,
            total_frames=0
        )

        self.sequences[cow_name] = sequence

        if self.camera_setup == "3":
            cameras = [
                "FRONT1",
                "FRONT2",
                "SIDE",
            ]
        else:
            cameras = [
                "FRONT1",
                "SIDE",
            ]

        self.views[cow_name] = {
            cam.lower(): CameraView.objects.create(
                sequence=sequence,
                camera=cam
            )
            for cam in cameras
        }

        self.rating_targets[cow_name] = self.create_rating_targets(sequence)

    # ---------------------------
    # RATING TARGETS
    # ---------------------------

    def create_rating_targets(self, sequence):

        if self.camera_setup == "3":
            targets = [
                "FRONT_PAIR_F1",
                "FRONT_PAIR_F2",
                "FRONT_PAIR_B1",
                "FRONT_PAIR_B2",
                "SIDE_F1",
                "SIDE_F2",
                "SIDE_B1",
                "SIDE_B2",
            ]
        else:
            targets = [
            "FRONT_F1",
            "FRONT_F2",
            "FRONT_B1",
            "FRONT_B2",
            "SIDE_F1",
            "SIDE_F2",
            "SIDE_B1",
            "SIDE_B2",
        ]

        return {
            t: RatingTarget.objects.create(
                sequence=sequence,
                target_type=t
            )
            for t in targets
        }

    # ---------------------------
    # PROCESS
    # ---------------------------

    def process_json_files(self):
        
        for item in self.json_items:

            path = item["path"]
            file_hash = item["hash"]
            
            json_obj, created = ImportedJson.objects.get_or_create(
            file_hash=file_hash,
            defaults={
                "farm": self.farm,
                "file_path": path,
            }
        )
            if json_obj.status == "processing":
                json_obj.status = "failed"
                json_obj.save(update_fields=["status"])

            # قبلا پردازش شده
            if json_obj.status == "done":
                continue

            json_obj.status = "processing"
            json_obj.save(update_fields=["status"])

            try:
                data = item["data"]
                
                filename = path.split("/")[-1]
                base_name = os.path.splitext(filename)[0]
                info = parse_filename(filename)
                
                camera = info["camera"].lower().strip()

                camera_alias = {
                    "hoof_front1": "front1",
                    "hoof_front2": "front2",
                    "hoof_side": "side",
                    "front1": "front1",
                    "front2": "front2",
                    "side": "side",
                }
             

                camera = camera_alias.get(camera)

                if camera is None:
                    print(f"Unknown camera: {info['camera']}")
                    continue

                cow_name = info["cow"]
                print(info)
                frame_number = info["frame_number"]

                self.get_system(cow_name)

                views = self.views[cow_name]
                rating_targets = self.rating_targets[cow_name]

                image = image_from_base64(data["imageData"])

                if is_blurry(image):
                    continue

                width, height = image.size

                image_filename = filename.replace(".json", ".jpg")

                original_file = save_pil_to_imagefield(
                    image,
                    image_filename
                )
                
                print("----------------")
                print(frame_number)
                print(camera)
                print(views[camera].id)
                frame, _ = Frame.objects.get_or_create(
                    view=views[camera],
                    frame_number=frame_number,
                    defaults={"image": original_file}
                )

                print(
                    f"FILE={filename} | "
                    f"CAMERA={camera} | "
                    f"FRAME={frame_number} | "
                    f"FRAME_ID={frame.id} | "
                    f"CREATED={created}"
                )

                for shape in data.get("shapes", []):

                    label = normalize_label(shape["label"])

                    if label is None:
                        continue

                    points = shape.get("points", [])

                    if len(points) != 2:
                        continue

                    (x1, y1), (x2, y2) = points

                    x1, x2 = sorted([int(x1), int(x2)])
                    y1, y2 = sorted([int(y1), int(y2)])

                    x1, y1, x2, y2 = clamp_bbox(
                        x1, y1, x2, y2,
                        width, height
                    )

                    if x2 <= x1 or y2 <= y1:
                        continue

                    crop_img = image.crop((x1, y1, x2, y2))

                    try:
                        target_key = get_rating_target(
                            self.camera_setup,
                            camera.upper(),
                            label
                        )
                    except KeyError:
                        print(
                            f"Unknown mapping: camera={camera}, label={label}"
                        )
                        continue

                    rating_target = rating_targets.get(target_key)

                    if not rating_target:
                        continue

                    crop_filename = f"{base_name}_{label.upper()}.jpg"
                    
                    cropped_file = save_pil_to_imagefield(
                        crop_img,
                        crop_filename,
                        base_path="cropped"
                    )
                    print("ContentFile name:", cropped_file.name)

                    full_name = (
                        f"cropped/"
                        f"{frame.view.sequence.cow.farm.name}/"
                        f"{frame.view.sequence.cow.name}/"
                        f"{frame.view.camera}/"
                        f"{label.upper()}/"
                        f"{crop_filename}"
                    )

                    if default_storage.exists(full_name):
                        default_storage.delete(full_name)

                    FrameAnnotation.objects.filter(
                        frame=frame,
                        rating_target=rating_target
                    ).delete()

                    FrameAnnotation.objects.create(
                        frame=frame,
                        hoof_label=label.upper(),
                        rating_target=rating_target,
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                        cropped_image=cropped_file
                    )
                    
                
                # اگر همه چیز موفق بود
                json_obj.status = "done"
                json_obj.processed_at = timezone.now()

                json_obj.save(
                    update_fields=[
                        "status",
                        "processed_at",
                    ]
                )

            except Exception as e:

                json_obj.status = "failed"
                json_obj.save(update_fields=["status"])

                print(f"Error processing {path}: {e}")

        