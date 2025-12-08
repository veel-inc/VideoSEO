FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation & safe linking for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy


# Install PostgreSQL development libraries and build dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies (using cache for faster builds)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy source code & install the project
COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose the application port
EXPOSE 80

# Reset entrypoint so uv is not auto-invoked
ENTRYPOINT []

# Start FastAPI using Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "::", "--port", "80"]