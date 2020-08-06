FROM python:3.8

RUN apt install curl
RUN curl https://pyenv.run | bash

ENV HOME  /root
ENV PYENV_ROOT $HOME/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

RUN eval "$(pyenv init -)"
RUN eval "$(pyenv virtualenv-init -)"

COPY tests/env-matrix/install_env.sh /install_env.sh
RUN chmod u+x /install_env.sh
RUN pyenv install 3.6.10
RUN pyenv install 3.7.7
RUN pyenv install 3.8.3

# Django 2.1.15
RUN /install_env.sh 3.6.10  2.1.15  env-36-21
RUN /install_env.sh 3.7.7   2.1.15  env-37-21
RUN /install_env.sh 3.8.3   2.1.15  env-38-21

# Django 2.2.12
RUN /install_env.sh 3.6.10  2.2.12  env-36-22
RUN /install_env.sh 3.7.7   2.2.12  env-37-22
RUN /install_env.sh 3.8.3   2.2.12  env-38-22

# Django 3.0.6
RUN /install_env.sh 3.6.10  3.0.6   env-36-30
RUN /install_env.sh 3.7.7   3.0.6   env-37-30
RUN /install_env.sh 3.8.3   3.0.6   env-38-30

# Django 3.1
RUN /install_env.sh 3.6.10  3.1     env-36-31
RUN /install_env.sh 3.7.7   3.1     env-37-31
RUN /install_env.sh 3.8.3   3.1     env-38-31

COPY ninja /ninja
COPY tests /tests
COPY docs /docs
COPY tests/env-matrix/run.sh /run.sh
RUN chmod u+x /run.sh

RUN echo 'Dependencies installed. Now running tests...' &&\
    /run.sh env-36-21  &&\
    /run.sh env-37-21  &&\
    /run.sh env-38-21  &&\
    /run.sh env-36-22  &&\
    /run.sh env-37-22  &&\
    /run.sh env-38-22  &&\
    /run.sh env-36-30  &&\
    /run.sh env-37-30  &&\
    /run.sh env-38-30  &&\
    /run.sh env-36-31  &&\
    /run.sh env-37-31  &&\
    /run.sh env-38-31  &&\
    echo 'Done.'
