FROM grafana/grafana:11.3.0

COPY provisioning /etc/grafana/provisioning
COPY dashboards /var/lib/grafana/dashboards

ENV GF_SECURITY_ALLOW_EMBEDDING=true \
    GF_SECURITY_COOKIE_SAMESITE=none \
    GF_USERS_ALLOW_SIGN_UP=false \
    GF_AUTH_ANONYMOUS_ENABLED=true \
    GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer

EXPOSE 3000
