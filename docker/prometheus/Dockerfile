FROM prom/prometheus:latest
COPY prometheus.yml /etc/prometheus/prometheus.yml
COPY rules /etc/prometheus/rules
CMD ["--config.file=/etc/prometheus/prometheus.yml"]
