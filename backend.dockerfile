FROM python:3.6

COPY ./requirements.txt /var/www/requirements.txt
RUN pip install -r /var/www/requirements.txt

WORKDIR /var/www
ENV PYTHONPATH /var/www/:$PYTHONPATH
EXPOSE 8000
EXPOSE 8001
