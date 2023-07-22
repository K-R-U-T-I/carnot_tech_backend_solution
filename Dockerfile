# official Python runtime as a base image
FROM python:3.9-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the required packages
RUN pip install pandas redis flask

# Expose port 8000 for the Flask app
EXPOSE 8000

# Run the Python application when the container starts
CMD ["python", "app.py"]
