FROM continuumio/miniconda3:23.10.0-1

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y libtiff5 libusb-1.0-0 libraw1394-dev libcurl4
COPY requirements.txt /xtomo/requirements.txt
WORKDIR /xtomo

RUN python -m pip install -r requirements.txt

COPY vendor /xtomo/vendor

RUN ln -s /xtomo/vendor/ximea/include /usr/include/m3api
RUN ln -s /xtomo/vendor/ximea/api/X64/libm3api.so* /usr/lib/ &&\
    ln -s /xtomo/vendor/ximea/api/X64/libm3api.so.2 /usr/lib/libm3api.so &&\
    ldconfig


RUN cd /xtomo/vendor/ximc-2.10.5/ximc/deb && dpkg -i libximc7_2.10.5-1_amd64.deb libximc7-dev_2.10.5-1_amd64.deb && apt-get install -f

COPY drivers/ /xtomo/drivers
COPY experiment/ /xtomo/experiment


EXPOSE 5001

COPY tomograph_server.py /xtomo/tomograph_server.py
COPY redis_proxy.py /xtomo/redis_proxy.py

# ARG USER_ID=1000
# ARG GROUP_ID=1000
# RUN groupadd -g ${GROUP_ID} robotom &&\
#     useradd -l -m -u ${USER_ID} -g robotom robotom
    
# RUN chown -R robotom /drivers
# USER robotom

# CMD waitress-serve --port=5001 --host=0.0.0.0 --call experiment:create_app
CMD FLASK_DEBUG=1 FLASK_APP=experiment flask run --port=5001 --host=0.0.0.0 --no-reload

# RUN ls -la /dev/tty*
