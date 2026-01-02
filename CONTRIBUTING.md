# Contributing to VideoSEO

Thank you for your interest in contributing to VideoSEO! We welcome contributions from the open source community to help improve and grow the project.

## How to Contribute

### 1. Fork the Repository
- Click the **Fork** button at the top right of this repository page to create your own copy.

### 2. Clone Your Fork
```bash
git clone https://github.com/your-username/VideoSEO.git
cd VideoSEO
```


### 3. Create a Branch
- Use a descriptive branch name based on the type of change:
	- `feat/your-feature-name` for new features
	- `fix/your-bugfix` for bug fixes
	- `chore/your-chore` for maintenance or chores
	- `enhance/your-enhancement` for improvements
```bash
git checkout -b feat/your-feature-name
```

### 4. Install Dependencies
- Ensure you have [uv](https://github.com/astral-sh/uv) installed.
- Install dependencies:
```bash
uv sync --frozen
```

### 5. Make Your Changes
- Follow the project's coding standards and guidelines (see below).
- Add or update tests as appropriate.

### 6. Run Linting, Formatting, and Tests
```bash
trunk check .
trunk fmt .
pytest src/tests -v
```

### 7. Commit and Push
```bash
git add .
git commit -m "Describe your changes"
git push origin feature/your-feature-name
```


### 8. Raise an Issue First
- Before starting work, please [raise an issue](ISSUE_TEMPLATE.md) describing the bug, feature, or enhancement you plan to work on. Wait for feedback or approval from the maintainers before submitting a pull request.

### 9. Open a Pull Request
- Go to your fork on GitHub and open a Pull Request (PR) to the `main` branch of this repository.
- Provide a clear description of your changes and reference the related issue number.

---

## Join Our Community
Join our community on Discord to connect with other users and contributors! You can find the demo and discussions in the `#video-seo-discussions` channel. [Click here to join our Discord](https://discord.gg/PWbHPNnRvj).

## Code of Conduct
Please be respectful and considerate in all interactions. See [Contributor Covenant](https://www.contributor-covenant.org/) for guidelines.

## Coding Guidelines
- Follow [PEP8](https://www.python.org/dev/peps/pep-0008/) for Python code style.
- Write clear, concise commit messages.
- Add docstrings and comments where necessary.
- Write and maintain tests for new and changed functionality.

## Need Help?
If you have questions, open an issue or start a discussion in the repository.

Happy contributing!
