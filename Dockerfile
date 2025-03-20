FROM python:3.12-slim

# Install system packages needed for mysqlclient (and other build tools)
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Install `uv` package manager
RUN pip install uv

COPY . .
COPY pyproject.toml ./

RUN pip install --upgrade pip && pip install uv
RUN uv --version

# Copy requirements.txt first to leverage caching
#COPY requirements.txt /app/
#RUN test -f pyproject.toml && uv pip install --system || echo "pyproject.toml not found"

RUN uv pip install --system --requirements pyproject.toml


#RUN if [ -f "pyproject.toml" ]; then uv pip install --system; else echo "pyproject.toml not found"; fi

# Copy the rest of the project files

# Upgrade pip and install uv

# Verify that uv is installed correctly

# Install Python dependencies
#RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
#COPY . /app
# Ensure `uvicorn` is installed
RUN pip install uvicorn

# Expose the application port


# Run the FastAPI/uvicorn server

# Expose port 8000 for the FastAPI app
EXPOSE 8000

# Run the app with Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

