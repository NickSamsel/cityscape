FROM python:3.11-slim

# Added postgresql-client to the list
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
    rm -rf /var/lib/apt/lists/*

RUN curl -Ls https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# dbt-postgres and prefect install
RUN uv pip install --system dbt-postgres prefect

# Terraform install
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.7.5/terraform_1.7.5_linux_amd64.zip -o terraform.zip && \
    unzip terraform.zip && \
    mv terraform /usr/local/bin/ && \
    rm terraform.zip

WORKDIR /workspaces/cityscape
CMD ["sleep", "infinity"]