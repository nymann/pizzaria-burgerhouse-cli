FROM debian:bookworm AS base-image
RUN apt-get update && \
    apt-get install --assume-yes --no-install-recommends python3 && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m --shell /bin/bash -u 1000 non_privileged_user
ENV HOME="/home/non_privileged_user"
ENV VENV="$HOME/.venv"

FROM base-image AS compile-image
RUN apt-get update && \
    apt-get install -y --no-install-recommends make git python3-pip python3-venv &&\
    rm -rf /var/lib/apt/lists/*

USER non_privileged_user
ENV APP_DIR="$HOME/app"
RUN mkdir "$APP_DIR"
WORKDIR "$APP_DIR"

ENV PATH="$VENV/bin:$PATH"
RUN python3 -m venv $VENV && \
    pip install --upgrade pip setuptools wheel

COPY --chown=non_privileged_user:non_privileged_user . "$APP_DIR"
RUN make install

FROM base-image AS production-image
USER non_privileged_user
ENV PATH="$VENV/bin:$PATH"
COPY --from=compile-image --chown=non_privileged_user:non_privileged_user "$VENV" "$VENV"
CMD pizzaria_burgerhouse_cli --help
