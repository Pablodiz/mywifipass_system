FROM python:latest


ENV DIR="/djangox509"
RUN mkdir $DIR
WORKDIR $DIR
COPY . $DIR
RUN apt-get update && apt-get install -y \
    sqlite3 \
    libsqlite3-dev
RUN pip3 install -U pip setuptools wheel
RUN pip3 install -e .
RUN echo "django-x509 Installed"

WORKDIR $DIR/tests
EXPOSE 8000
ENV NAME djangox509

CMD ["./docker-entrypoint.sh"]
