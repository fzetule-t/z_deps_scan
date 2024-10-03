FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1  # Prevent Python from writing .pyc files
ENV PYTHONUNBUFFERED 1         # Ensure that Python output is sent straight to the terminal (real-time)

# Set work directory
RUN mkdir -p /app/data
WORKDIR /app

RUN apt-get update
RUN apt-get install -y openjdk-17-jdk
RUN apt-get install -y maven

# Set MAVEN_HOME environment variable
ENV MAVEN_HOME=/usr/share/maven
ENV PATH=$MAVEN_HOME/bin:$PATH

RUN apt-get update
RUN apt-get install -y git
RUN apt-get install -y gcc

# Install dependencies
RUN pip install --upgrade pip

# Copy requirements file to the container
COPY ./requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

COPY . /app

# Replace .env file
RUN if [ -f /app/z_deps_scan/.env ]; then rm /app/z_deps_scan/.env; fi
COPY Docker.env /app/z_deps_scan/.env

RUN python manage.py collectstatic --noinput --clear
RUN python manage.py migrate

# Expose the necessary ports
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000" , "--workers", "3" , "z_deps_scan.wsgi"]
