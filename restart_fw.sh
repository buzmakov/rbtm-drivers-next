export XIMEA_CAMERA_DEVICE="/dev/fw1:/dev/fw1"
export COMPOSE_BAKE=true

cd /home/robotom/workspace/xtomo/rbtm-drivers-next && \
docker compose down && \
docker compose build && \
docker compose up experiment redis tomograph_server
