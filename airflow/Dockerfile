FROM apache/airflow:3.0.1-python3.11

USER airflow

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY --chown=airflow:root dags/ /opt/airflow/dags/
COPY --chown=airflow:root include/ /opt/airflow/include/

ENV PYTHONPATH=/opt/airflow/include:${PYTHONPATH}
