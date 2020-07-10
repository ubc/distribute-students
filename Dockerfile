FROM python:3.7-slim

ENV SECTION_ENROLLMENT_LIMIT 35

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY app/ /app
WORKDIR /app

CMD ["python", "-u", "test_connection.py"]
