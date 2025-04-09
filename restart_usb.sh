export XIMEA_CAMERA_DEVICE="/dev/bus/usb/004/003:/dev/bus/usb/004/003"
export COMPOSE_BAKE=true

cd /home/robotom/workspace/xtomo/rbtm-drivers-next && \
docker compose down && \
docker compose build && \
docker compose up experiment redis tomograph_server