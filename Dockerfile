FROM python:3.12-alpine
# Set the working directory
WORKDIR /whatsgrambot

# Copy the current directory contents into the container at /whatsgrambot
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt
