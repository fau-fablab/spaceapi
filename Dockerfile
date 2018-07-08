FROM fablab.fau.de/basislinux

RUN apt update && \
    apt -y install python3-pip libssl-dev && \
    apt clean

ADD . /srv/

RUN pip3 install -q --upgrade -r /srv/requirements-server.txt

# www-data already exists in base installation. Change to our docker UID range.
RUN usermod -u 400 www-data && groupmod -g 400 www-data
USER www-data

EXPOSE 8888

# more settings will be provided in /etc/spaceapi.py
CMD /srv/spaceapi/spaceapi.py --key /mnt/secrets/spaceapi/key --host '0.0.0.0' --port 8888
