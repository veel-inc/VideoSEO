# VideoSEO - aka Nuvia

Nuvia is derived from the combination of “nu” (new) and “via” (way) — symbolizing “a new way to see.” It represents a fresh, modern approach to interacting with intelligent systems.

VideoSEO is an innovative platform designed to revolutionize the way video content is optimized for search engines and user engagement. By leveraging cutting-edge technologies like AI, GraphQL, and FastAPI, VideoSEO empowers content creators, marketers, and businesses to:

- **Enhance Video Discoverability**: Optimize metadata, transcripts, and tags to improve search rankings.
- **Streamline Content Management**: Use advanced tools to manage and analyze video libraries efficiently.
- **Boost Viewer Engagement**: Deliver personalized and context-aware video recommendations.

Whether you're a small creator or a large enterprise, VideoSEO provides the tools you need to stay ahead in the competitive world of video content.


## Stack
```bash
Python
Strawberry GraphQL 
FastAPI 
Trunk # For linting, formatting, and security checks  
uv # For dependency management and virtual environments
```

## Design Principles
- Hexagonal architecture
- Clean Code
- SOLID Principles
- Test-Driven Development(TDD)

## Quick Start
### 1. Clone the Respository
``` bash
git clone git@github.com:veel-inc/VideoSEO.git
cd VideoSEO
```

### 2. Install Dependencies
Ensure you have [uv](https://github.com/astral-sh/uv) installed. If not, install it following the guide linked.

```bash
uv sync --frozen
```
### 3. Set Up Environment Variables

``` bash
cp .env.examples .env
```
Edit the .env file and provide the required configuration values.

## Setting Up PostgreSQL with Docker

To spin up a PostgreSQL database using Docker, follow these steps:

### 1. Run PostgreSQL Container
```bash
docker run --name postgres-db -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=admin -e POSTGRES_DB=videoseo -p 5432:5432 -d postgres
```

### 2. Use the PostgreSQL Adapter

Instead of using separate SQL scripts, refer to the `postgres_database_adapter.py` located in `src/adapters`. This module contains the necessary logic to initialize the database, create tables, and manage data.

## Run VideoSEO Using GraphQL

### Run via Python

``` bash
uvicorn src.main:app
```
Service will be available at: http://127.0.0.1:8000/graphql

### Run via docker
a. Build the image

``` bash
docker build -t VideoSEO .
```

b. Run the Container
``` bash
docker run -d --name VideoSEO -p "[::]:8000:80" VideoSEO
```
Service will be available at: `http://[::1]:8000/graphql`


## Contributing

We welcome contributions from the open source community! If you would like to contribute, please read our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started, coding standards, and the process for submitting pull requests.

### Ways to Contribute
- Report bugs or suggest features by opening an issue.
- Submit pull requests for new features, bug fixes, or documentation improvements.
- Review and comment on existing issues and pull requests.

### Community & Support
- For questions, open an issue or start a discussion in the repository.
- Please be respectful and follow our Code of Conduct.


## Linting and formatting
Setup the trunk using [Trunk](https://trunk.io/)
``` bash
trunk check . # to check 
trunk fmt . # to format files
```

## Testing
a. To run all unit tests, execute
```bash
pytest src/tests -v # (-v) If you want verbose output
```

b. To run a specific unit test file, execute:
``` bash
pytest src/tests/test_your_test_file.py -v
```

## Project Structure
``` bash
VideoSEO/
├── .trunk/                # Trunk configuration files
├── .gitignore             # Git ignore file
├── .dockerignore          # Docker ignore file
├── python-version         # Python version specification
├── src/
│   ├── adapters/          # External interfaces (e.g., database, APIs)
│   ├── application/       
│       ├── prompts/       # AI prompts management
│       ├── services/      # Application services
│   ├── core/              # configurations
│   ├── domain/            
│       ├── models/        # Domain models
│       └── rules/         # Rules for content moderation
│   ├── ports/             
│       ├── input/         # Input ports
│       └── output/        # Output ports
│   ├── tests/             # Unit tests
│   ├── utils/             # Utility functions and helpers
│   └── main.py            # Application entry point
├── .env_example           # Example environment variables file
├── Dockerfile             # Docker configuration
├── pyproject.toml         # Project dependencies
├── uv.lock                # uv dependency lock file
├── TAGS                   # Project tags
└── README.md              # Project documentation
```
