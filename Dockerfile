FROM python:3
COPY src/requirements.txt /opt/app/requirements.txt
WORKDIR /opt/app
RUN pip install -r requirements.txt
COPY src /opt/app
ENTRYPOINT ["python3","-u","/opt/app/deploy.py"]
