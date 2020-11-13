FROM continuumio/miniconda3:4.7.12

ENV DEBIAN_FRONTEND=noninteractive

COPY requirements.txt /drivers/requirements.txt
WORKDIR /drivers

RUN python -m pip install -r requirements.txt

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /drivers/

RUN FLASK_DEBUG=1 FLASK_APP=experiment flask run --port=5001 --host=0.0.0.0 --no-reload