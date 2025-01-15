# Contributing to Harvester

Thank you for considering contributing to Harvester! Contributions are welcome in the form of bug reports, feature
requests, or pull requests. Please follow the guidelines below to ensure that your contributions are accepted.

## Setting up the development environment

1. Clone the repository:
   ```bash
   git clone https://github.com/blazaid/harvester.git
   cd harvester
   ```
2. Create a virtual environment and install the development dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # or in windows: .\venv\Scripts\activate
   pip install -e .[dev]
   ```

## Running tests and linting

- Run the tests:
  ```bash
  pytest
  ```
- Format the code:
  ```bash
  black .
  ```
- Sort the imports:
  ```bash
  isort .
  ```
- Check types (for both the library and tests):
  ```bash
  mypy harvester tests
  ```
- Analyze the code:
  ```bash
  flakes8 harvester tests
  ```

## Submitting changes

1. Fork the repository and create a new branch.
    - This is done by clicking the [Fork](https://github.com/blazaid/harvester/fork) button on the top right of the
      [repository page](https://github.com/blazaid/harvester).
2. Create a new branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes and commit them
    - Follow the [commit message conventions](https://www.conventionalcommits.org/en/v1.0.0/)
   ```python
   git add .
   git commit -m "feat: Description for the changes"
   ```
4. Push your changes to your fork:
   ```bash
    git push origin feature/your-feature-name
    ```
5. Create a pull request:
    - Go to the [pull requests](https://github.com/blazaid/harvester/pulls) page of the repository.