# Use an appropriate base image for Python
FROM python:3.8

# Set the working directory inside the container
WORKDIR /app

# Create src directory
RUN mkdir src

# Copy the requirements file into the container
COPY ./requirements.txt .

# Install the Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# Copies everything without the file structure so we don't need
# to even set the PYTHONPATH and just go with the flow
COPY ./src/* ./

# Specify the command to run when the container starts
CMD ["python", "main.py", "run"]

# Expose the port that the server will be listening to
EXPOSE 2000
