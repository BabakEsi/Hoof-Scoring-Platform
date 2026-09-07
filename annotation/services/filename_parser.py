from pathlib import Path


def parse_filename(filename):

    filename = Path(filename).stem
    parts = filename.split("_")

    if len(parts) != 12:
        raise ValueError(f"Invalid filename: {filename}")

    return {
        "camera_id": parts[0],          # MPF8E4E3
        "export_date": parts[1],        # 20260417
        "export_time": parts[2],        # 150750

        "farm": parts[3],               # can20260417females

        "session_date": parts[4],       # 20260417
        "session_time": parts[5],       # 092701

        "sequence_id": parts[6],        # 000000000000

        "cow": parts[7],                # can12n

        "run_number": parts[8],         # 0001

        "camera": f"{parts[9]}_{parts[10]}",   # hoof_side / hoof_front1 / hoof_front2

        "frame_number": int(parts[11]),

        "filename": filename,
    }