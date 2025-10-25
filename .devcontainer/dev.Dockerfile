FROM mcr.microsoft.com/vscode/devcontainers/python:3.11

USER root
RUN apt-get update &&\
    apt-get install -y \
        default-jdk-headless

USER vscode