THREE_CAMERA_MAP = {

    "FRONT1": {
        "f1": "FRONT_PAIR_F1",
        "f2": "FRONT_PAIR_F2",
        "b1": "FRONT_PAIR_B1",
        "b2": "FRONT_PAIR_B2",
    },

    # Front2 برعکس Front1 است
    "FRONT2": {
        "f1": "FRONT_PAIR_F2",
        "f2": "FRONT_PAIR_F1",
        "b1": "FRONT_PAIR_B2",
        "b2": "FRONT_PAIR_B1",
    },

    "SIDE": {
        "f1": "SIDE_F1",
        "f2": "SIDE_F2",
        "b1": "SIDE_B1",
        "b2": "SIDE_B2",
    },
}


TWO_CAMERA_MAP = {

    "FRONT1": {
        "f1": "FRONT1_F1",
        "f2": "FRONT1_F2",
        "b1": "FRONT1_B1",
        "b2": "FRONT1_B2",
    },

    "SIDE": {
        "f1": "SIDE_F1",
        "f2": "SIDE_F2",
        "b1": "SIDE_B1",
        "b2": "SIDE_B2",
    },
}


def get_rating_target(camera_setup, camera, label):
    camera = camera.upper()
    label = label.lower()

    if camera_setup == "3":
        return THREE_CAMERA_MAP[camera][label]

    return TWO_CAMERA_MAP[camera][label]