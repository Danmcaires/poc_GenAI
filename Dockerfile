# STAGE 1 - Install build dependencies
FROM python:3.8-slim AS builder

# Set workdir
WORKDIR /app

# Install required packages so the layer can
# compile Python libraries with binary dependencies
RUN apt update && \
    apt install -y build-essential python3-dev gcc

# Copy only requirements file
COPY ./requirements.txt .

# Create venv and install requirements
RUN python -m venv .venv && \
    .venv/bin/pip install --upgrade pip && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt

# Delete unnecessary files
RUN find /app/.venv \( -type d -a -name test -o -name tests \) -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) -exec rm -rf '{}' \+ && \
    find /app/.venv -name '__pycache__' | xargs rm -rf

# STAGE 2 - Copy only necessary files to runner stage
FROM python:3.8-slim

# Set workdir
WORKDIR /app

# Copy dependencies files from builder
COPY --from=builder /app /app

# Copy app source files
COPY ./src/* ./

# Define required variables for app to run
ENV PATH="/app/.venv/bin:$PATH"

# Specify the command to run when the container starts
CMD ["python", "main.py"]

# Expose the port that the server will be listening to
EXPOSE 2000
