FROM python:3.9.10-buster

LABEL maintainer="Josh Teng <joshteng@me.com>"

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

CMD ["python3.9", "start.py"]
