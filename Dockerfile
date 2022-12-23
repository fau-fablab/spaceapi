FROM ubuntu:22.04.1
# (note: within the FAU FabLab installation, this image is aliased to the custom "basislinux")

RUN apt-get update && \
    apt-get -y install python3-pip libssl-dev tini && \
    apt-get clean

ADD . /srv/

RUN pip3 install -q --upgrade -r /srv/requirements-server.txt

# www-data already exists in base installation. Change to our docker UID range.
RUN usermod -u 400 www-data && groupmod -g 400 www-data
USER www-data

EXPOSE 8888

# more settings will be provided in /etc/spaceapi.py
CMD ["tini", "--", "/srv/spaceapi/spaceapi.py", "--key", "/mnt/secrets/spaceapi/key", "--host", "0.0.0.0", "--port", "8888"]
