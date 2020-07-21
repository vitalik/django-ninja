FROM python:3.8

RUN apt install curl
RUN curl https://pyenv.run | bash

RUN /root/.pyenv/bin/pyenv install --help

RUN /root/.pyenv/bin/pyenv install 3.6.10
RUN /root/.pyenv/bin/pyenv install 3.7.7
RUN /root/.pyenv/bin/pyenv install 3.8.3
RUN /root/.pyenv/bin/pyenv install 3.9.0b3

ENV HOME  /root
ENV PYENV_ROOT $HOME/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

COPY tests/env-matrix/install_env.sh /install_env.sh

RUN bash /install_env.sh 3.6.10  2.0.13  env-36-20
RUN bash /install_env.sh 3.6.10  2.1.15  env-36-21
RUN bash /install_env.sh 3.6.10  2.2.12  env-36-22
RUN bash /install_env.sh 3.6.10  3.0.6   env-36-30
RUN bash /install_env.sh 3.6.10  3.1b1   env-36-31
RUN bash /install_env.sh 3.7.7   2.0.13  env-37-20
RUN bash /install_env.sh 3.7.7   2.1.15  env-37-21
RUN bash /install_env.sh 3.7.7   2.2.12  env-37-22
RUN bash /install_env.sh 3.7.7   3.0.6   env-37-30
RUN bash /install_env.sh 3.7.7   3.1b1   env-37-31
RUN bash /install_env.sh 3.8.3   2.0.13  env-38-20
RUN bash /install_env.sh 3.8.3   2.1.15  env-38-21
RUN bash /install_env.sh 3.8.3   2.2.12  env-38-22
RUN bash /install_env.sh 3.8.3   3.0.6   env-38-30
RUN bash /install_env.sh 3.8.3   3.1b1   env-38-31

RUN bash /install_env.sh 3.9.0b3 3.0     env-39-30


COPY ninja /ninja
COPY tests /tests
COPY docs /docs


COPY tests/env-matrix/run.sh /run.sh

WORKDIR /



RUN bash /run.sh env-36-20 &&\
    bash /run.sh env-36-21 &&\
    bash /run.sh env-36-22 &&\
    bash /run.sh env-36-30 &&\
    bash /run.sh env-36-31 &&\
    bash /run.sh env-37-20 &&\
    bash /run.sh env-37-21 &&\
    bash /run.sh env-37-22 &&\
    bash /run.sh env-37-30 &&\
    bash /run.sh env-37-31 &&\
    bash /run.sh env-38-20 &&\
    bash /run.sh env-38-21 &&\
    bash /run.sh env-38-22 &&\
    bash /run.sh env-38-30 &&\
    bash /run.sh env-38-31 &&\
    echo "done"

RUN bash /run.sh env-39-30
