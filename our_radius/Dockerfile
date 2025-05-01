FROM freeradius/freeradius-server:latest


# Config files
COPY ./eap-template /etc/raddb/mods-available/eap-template
COPY ./server-template /etc/raddb/sites-available/server-template
COPY ./default /etc/raddb/sites-enabled/default
COPY ./clients.conf.template /etc/raddb/clients.conf.template
COPY ./cron /etc/cron.d/cron
COPY ./process_ssids.sh ./create_ssids.sh /usr/local/bin/

RUN apt-get update &&   \
    # We install envsubst
    apt-get install -y gettext cron && \ 
    rm -rf /var/lib/apt/lists/* && \
    mkdir /etc/freeradius/tlscache && \
    chmod 700 /etc/freeradius/tlscache && \
    touch /etc/raddb/clients.conf && \
    chmod 600 /etc/cron.d/cron && \ 
    chmod 700 /usr/local/bin/process_ssids.sh && \
    chmod 700 /usr/local/bin/create_ssids.sh && \
    crontab /etc/cron.d/cron  && \ 
    mkdir -p /etc/raddb/server_certs/processed /etc/raddb/server_certs/pending 

# Ports that are exposed
EXPOSE 1812/udp 1813/udp

# Env variables are replaced in the template, 
# cron is started 
# freeradius is started in debug mode as freerad user
CMD envsubst < /etc/raddb/clients.conf.template > /etc/raddb/clients.conf && \ 
    chown freerad:freerad /etc/raddb/clients.conf && \
    cron && \
    freeradius -X