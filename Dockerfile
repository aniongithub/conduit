FROM python:3.11-slim AS base

RUN apt-get update &&\
    apt-get install -y \
        git \
        build-essential \
        netcat-traditional \
        default-jdk-headless

FROM base AS runtime

WORKDIR /conduit

ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} conduit && \
    useradd -u ${USER_ID} -g ${GROUP_ID} -d /conduit -s /bin/bash conduit

COPY --chown=conduit:conduit . /conduit
RUN pip install -e .

USER conduit

ENTRYPOINT ["conduit-cli"]