FROM grafana/loki:3.2.1

COPY loki-config.yml /etc/loki/local-config.yaml

ENTRYPOINT ["/usr/bin/loki"]
CMD ["-config.file=/etc/loki/local-config.yaml"]
