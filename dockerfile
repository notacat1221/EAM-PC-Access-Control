# Use a Windows base image with Python pre-installed
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000 for the Flask app and 80 for Azure
EXPOSE 5000

# Define environment variable for Flask app
ENV FLASK_APP=app.py

# Run the Flask app
CMD ["python", "app.py", "run", "--host=0.0.0.0", "--port=5000"]

