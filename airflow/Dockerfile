
FROM apache/airflow:3.4.0-python3.11

USER airflow

COPY --chown=airflow:root airflow/requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir \
    "apache-airflow==${AIRFLOW_VERSION}" \
    -r /tmp/requirements.txt \
    && pip check

ENV PYTHONPATH=/opt/tta-risk:/opt/tta-risk/src

WORKDIR /opt/airflow
