FRAME_PNG_FILENAME = 'image.png'
STORAGE_URI = 'http://localhost:5006'
STORAGE_FRAMES_URI = "{}/storage/frames/post".format(STORAGE_URI)
STORAGE_EXP_START_URI = "{}/storage/experiments/create".format(STORAGE_URI)
STORAGE_EXP_FINISH_URI = "{}/storage/experiments/finish".format(STORAGE_URI)

SUCCESSFUL_STOP_MSG = 'Experiment was finished successfully'
EMERGENCY_STOP_MSG = 'Experiment was emergency stopped'
SOMEONE_STOP_MSG = 'Experiment was stopped by someone'
