FROM continuumio/miniconda3:4.7.12

ENV DEBIAN_FRONTEND=noninteractive

COPY requirements.txt /drivers/requirements.txt
WORKDIR /drivers

RUN python -m pip install -r requirements.txt

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /drivers/

EXPOSE 5001
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} robotom &&\
    useradd -l -m -u ${USER_ID} -g robotom robotom
# RUN useradd -ms /bin/bash makov
RUN chown -R robotom /drivers

USER makov

RUN FLASK_DEBUG=1 FLASK_APP=experiment flask run --port=5001 --host=0.0.0.0 --no-reload