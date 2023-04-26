FROM python:3.9

WORKDIR /fastapi-app
COPY reqs.txt .
RUN pip install -r reqs.txt
COPY ./app ./app

CMD ["python", "./app/main.py"]