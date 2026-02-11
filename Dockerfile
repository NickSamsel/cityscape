FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    unzip \
    libpq-dev \
    ca-certificates \
    openssh-client \
    postgresql-client && \
    curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    rm -rf /var/lib/apt/lists/*

# Install uv globally so it's accessible to all users
ENV UV_INSTALL_DIR="/usr/local/bin"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dbt and prefect globally
RUN uv pip install --system dbt-bigquery prefect

# Install Terraform
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.7.5/terraform_1.7.5_linux_amd64.zip -o terraform.zip && \
    unzip terraform.zip && \
    mv terraform /usr/local/bin/ && \
    rm terraform.zip

WORKDIR /workspaces/cityscape

# Ensure the workspace is owned by the user, but for now, we'll let the container run
CMD ["sleep", "infinity"]