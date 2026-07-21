# 🤝 Contributing to EcoBuddy AI

First off, thank you for considering contributing to **EcoBuddy AI**! 🌱

We welcome contributions of all kinds, including bug fixes, new features, documentation improvements, performance enhancements, and testing. Every contribution helps make EcoBuddy AI better for everyone.

---

# Table of Contents

* Ways to Contribute
* Getting Started
* Development Setup
* Branch Naming
* Commit Messages
* Pull Request Guidelines
* Coding Standards
* Reporting Bugs
* Suggesting Features
* Testing
* Community Guidelines

---

# Ways to Contribute

You can contribute by:

* 🐛 Fixing bugs
* ✨ Adding new features
* 📚 Improving documentation
* 🧪 Writing or improving tests
* ⚡ Optimizing performance
* 🎨 Improving the user interface
* 🔒 Enhancing security
* 📝 Improving code readability

---

# Getting Started

## 1. Fork the Repository

Fork the project to your GitHub account.

## 2. Clone Your Fork

```bash
git clone https://github.com/<your-username>/eco-buddy-ai.git
cd eco-buddy-ai
```

## 3. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Run the Application

```bash
streamlit run app.py
```

---

# Development Setup

Before making changes:

* Ensure all dependencies are installed.
* Create a new branch for your work.
* Test your changes before submitting a pull request.

---

# Branch Naming

Use descriptive branch names such as:

```
feature/add-pdf-export
feature/improve-dashboard
bugfix/database-error
docs/update-readme
test/add-emission-tests
refactor/recommendation-engine
```

---

# Commit Messages

Write concise and meaningful commit messages.

Examples:

```
feat: add eco score calculation
fix: resolve SQLite connection issue
docs: update installation guide
test: add recommendation unit tests
refactor: simplify emission calculations
```

---

# Pull Request Guidelines

Before submitting a pull request:

* Ensure your branch is up to date with the main branch.
* Keep pull requests focused on a single change.
* Update documentation if necessary.
* Include tests for new functionality.
* Ensure existing tests continue to pass.

Your pull request should include:

* A clear description of the changes
* Screenshots (if UI changes were made)
* Related issue number (if applicable)

Example:

```
Closes #12
```

---

# Coding Standards

Please follow these guidelines:

* Follow PEP 8 style guidelines for Python.
* Use meaningful variable and function names.
* Keep functions small and focused.
* Add comments where necessary.
* Remove unused imports and code.
* Write readable and maintainable code.

---

# Reporting Bugs

When reporting a bug, please include:

* Operating system
* Python version
* Steps to reproduce
* Expected behavior
* Actual behavior
* Error messages or logs
* Screenshots (if applicable)

---

# Suggesting Features

Feature requests should include:

* A clear description of the proposed feature
* The problem it solves
* Possible implementation ideas
* Any alternatives considered

---

# Testing

Run all tests before opening a pull request:

```bash
python test_db.py
python test_emissions.py
python test_recommendations.py
```

If you add new functionality, include corresponding tests whenever possible.

---

# Community Guidelines

Please be respectful and constructive when interacting with other contributors.

By participating in this project, you agree to abide by the project's **Code of Conduct**.

---

# Questions?

If you have questions or need assistance, feel free to open a GitHub Issue or start a discussion.

Thank you for contributing to **EcoBuddy AI** and helping build a more sustainable future! 🌱
