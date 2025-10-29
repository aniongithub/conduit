FROM python:3.11-slim AS base

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update &&\
    apt-get install -y \
        git \
        build-essential \
        wget \
        curl \
        netcat-traditional \
        default-jdk-headless

# Install yq
RUN wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq &&\
    chmod +x /usr/local/bin/yq

# Add root directory to PYTHONPATH so /elements package can be found
ENV PYTHONPATH="/:${PYTHONPATH}"
# Add /elements to schema generator search paths so custom elements appear in schema
ENV CONDUIT_SEARCH_PATHS="/elements"

# Create example custom element
RUN mkdir -p /elements
COPY ExampleCustom.py /elements/
RUN echo "from .ExampleCustom import ExampleCustom" > /elements/__init__.py

FROM base AS runtime

# Install Conduit
WORKDIR /conduit

ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} conduit && \
    useradd -u ${USER_ID} -g ${GROUP_ID} -d /conduit -s /bin/bash conduit

COPY --chown=conduit:conduit . /conduit
RUN pip install -e .

RUN chown -R conduit:conduit /elements

USER conduit

ENTRYPOINT ["conduit-cli"]