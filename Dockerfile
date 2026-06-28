FROM python:3.12-alpine

# Set the working directory
WORKDIR /whatsgrambot

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    python3-dev \
    libffi-dev

# Copy the current directory contents into the container at /whatsgrambot
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt
