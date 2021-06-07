FROM fnproject/python:3.7.1-dev as build-stage

ADD . /function
WORKDIR /function

RUN pip3 install --target /python/  --no-cache --no-cache-dir -r requirements.txt

RUN rm -rf ~/.cache/pip /tmp* requirements.txt func.yaml Dockerfile .venv

FROM fnproject/python:3.7.1

RUN apt update -y && apt install -y libmagic1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build-stage /function /function
COPY --from=build-stage /python /python
ENV PYTHONPATH=/python

ENTRYPOINT ["/python/bin/fdk", "/function/func.py", "handler"]
