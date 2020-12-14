FROM continuumio/miniconda3:4.7.12

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y libtiff-dev libusb-1.0-0 libraw1394-dev
COPY requirements.txt /drivers/requirements.txt
WORKDIR /drivers

RUN python -m pip install -r requirements.txt

COPY . /drivers/
RUN ln -s /drivers/vendor/ximea/include /usr/include/m3api
RUN ln -s /drivers/vendor/ximea/api/X64/libm3api.so* /usr/lib/ &&\
    ln -s /drivers/vendor/ximea/api/X64/libm3api.so.2 /usr/lib/libm3api.so &&\
    ldconfig

RUN cd /drivers/vendor/ximc-2.10.5/ximc/deb && dpkg -i libximc7_2.10.5-1_amd64.deb libximc7-dev_2.10.5-1_amd64.deb && apt-get install -f

EXPOSE 5001
# ARG USER_ID=1000
# ARG GROUP_ID=1000
# RUN groupadd -g ${GROUP_ID} robotom &&\
#     useradd -l -m -u ${USER_ID} -g robotom robotom
    
# RUN chown -R robotom /drivers
# USER robotom

CMD FLASK_DEBUG=1 FLASK_APP=experiment flask run --port=5001 --host=0.0.0.0 --no-reload
# RUN ls -la /dev/tty*