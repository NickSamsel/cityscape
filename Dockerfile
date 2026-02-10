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
    # Official Docker CLI installation script
    curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    rm -rf /var/lib/apt/lists/*

# Install uv (Python package installer)
RUN curl -Ls https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Install dbt and prefect
RUN uv pip install --system dbt-postgres prefect

# Install Terraform
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.7.5/terraform_1.7.5_linux_amd64.zip -o terraform.zip && \
    unzip terraform.zip && \
    mv terraform /usr/local/bin/ && \
    rm terraform.zip

WORKDIR /workspaces/cityscape
CMD ["sleep", "infinity"]