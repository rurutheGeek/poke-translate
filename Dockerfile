# Serves the static site from a release archive. Build with the archive in the
# build context:
#   docker build --build-arg VERSION=1.0.0 -t poke-translate .
# The server listens on $PORT (8080 by default), so it runs as is on Knative,
# Cloud Run and other platforms that pass the port that way.
FROM python:3.13-alpine@sha256:c50ccfb66e5cc97a610dcd0b9597de6ef5b52c96280b51997b353a0fc87a8361
ARG VERSION
LABEL org.opencontainers.image.source="https://github.com/rurutheGeek/poke-translate" \
      org.opencontainers.image.description="Pokémon-aware translation site" \
      org.opencontainers.image.licenses="MIT"
# ADD unpacks a local tar.gz.
ADD poke-translate-site-v${VERSION}.tar.gz /srv/
ENV PORT=8080 PYTHONDONTWRITEBYTECODE=1
USER 65534:65534
EXPOSE 8080
CMD ["sh", "-c", "exec python3 -m http.server \"$PORT\" --directory /srv"]
