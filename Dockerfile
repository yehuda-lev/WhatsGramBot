FROM python:3.10-alpine
# Set the working directory
WORKDIR /whatsgrambot

# Copy the current directory contents into the container at /whatsgrambot
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt

# Make port 8082 available to the world outside this container
ARG PORT=8080
ENV PORT=$PORT

# Expose the port configured by the environment variable
EXPOSE ${PORT}
