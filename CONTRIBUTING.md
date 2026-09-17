# Contributing to Aika Yokina Bot

Thank you for your interest in contributing to Aika Yokina, the BinRoom mascot Discord bot!

## Setting Up Development Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/aika-yokina-bot.git
   cd aika-yokina-bot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Unix/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Copy `.env.example` to `.env`
   - Fill in the required API keys and configuration values
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

## Development Guidelines

### Code Style
- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and modular

### Adding New Features
1. Create a new branch for your feature
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and test them thoroughly

3. Ensure environment variables are used for any sensitive data
   - Never hardcode API keys, tokens, or secrets
   - Use `os.getenv()` with sensible defaults

4. Test your changes
   - Test in a development environment first
   - Ensure existing features still work

### Adding New Cogs
- Place new cogs in the `cogs/` directory
- Follow the existing cog structure
- Include proper error handling
- Add appropriate permissions checks

### Database Changes
- Modify `database.py` for schema changes
- Include migration scripts if needed
- Test database operations thoroughly

## Submitting Changes

1. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

2. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request**
   - Describe your changes clearly
   - Reference any related issues
   - Include screenshots if applicable

## Code Review Process

- All submissions require review
- Address feedback from maintainers
- Ensure tests pass before merging

## Questions?

Feel free to open an issue for questions or discussions about contributions.

---

**Note**: This is a hobby project for the BinRoom community. Be respectful and follow Discord's Terms of Service when developing features.