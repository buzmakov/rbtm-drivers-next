cd /home/robotom/workspace/xtomo/rbtm-drivers-next && \
docker compose down && \
docker compose build drivers_usb && \
docker compose up drivers_usb -d
