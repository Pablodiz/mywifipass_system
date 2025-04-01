FROM freeradius/freeradius-server:latest


# Config files
COPY ./eap /etc/raddb/mods-available/eap
COPY ./clients.conf.template /etc/raddb/clients.conf.template

RUN apt-get update &&   \
    # We install envsubst
    apt-get install -y gettext && \ 
    rm -rf /var/lib/apt/lists/* && \
    mkdir /etc/freeradius/tlscache && \
    chown freerad:freerad /etc/freeradius/tlscache && \
    chmod 700 /etc/freeradius/tlscache && \
    touch /etc/raddb/clients.conf && \
    chown freerad:freerad /etc/raddb/clients.conf && \
    chmod 600 /etc/raddb/clients.conf


# Ports that are exposed
EXPOSE 1812/udp 1813/udp

# We select  the user that will run the service
USER freerad


# Env variables are replaced in the template
CMD envsubst < /etc/raddb/clients.conf.template > /etc/raddb/clients.conf && \
# Service is started
    freeradius -X
