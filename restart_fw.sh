cd /home/robotom/workspace/xtomo/rbtm-drivers-next && \
docker compose down && \
docker compose build drivers_fw && \
docker compose up drivers_fw -d
