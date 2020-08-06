PYTHON = ["3.6.10", "3.7.7", "3.8.3"]  # 3.9.0b3
DJANGO = ["2.1.15", "2.2.12", "3.0.6", "3.1"]


HEADER = """
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
""".strip()


def envname(py, dj):
    py = "".join(py.split(".")[:2])
    dj = "".join(dj.split(".")[:2])[:2]
    return f"env-{py}-{dj}"


print(HEADER)

for py in PYTHON:
    print(f"RUN pyenv install {py}")


for d in DJANGO:
    print()
    print(f"# Django {d}")
    for p in PYTHON:
        e = envname(p, d)
        print(f"RUN /install_env.sh {p:<7} {d:<7} {e}")


print(
    """
COPY ninja /ninja
COPY tests /tests
COPY docs /docs
COPY tests/env-matrix/run.sh /run.sh
RUN chmod u+x /run.sh
"""
)


print("RUN echo 'Dependencies installed. Now running tests...' &&\\")

for d in DJANGO:
    for p in PYTHON:
        e = envname(p, d)
        print(f"    /run.sh {e}  &&\\")

print("    echo 'Done.'")
