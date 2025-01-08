# Harvester: An easy-to-use Web Scraping tool.

<!-- [![Build Status](https://travis-ci.org/blazaid/harvester.svg?branch=master)](https://travis-ci.org/blazaid/harvester) -->
<!-- [![Coverage Status](https://coveralls.io/repos/github/blazaid/harvester/badge.svg?branch=master)](https://coveralls.io/github/blazaid/harvester?branch=master) -->
<!-- [![PyPI version](https://badge.fury.io/py/harvester.svg)](https://badge.fury.io/py/harvester) -->
<!-- [![Documentation Status](https://readthedocs.org/projects/harvester/badge/?version=latest)](http://harvester.readthedocs.io/en/latest/?badge=latest) -->

Harvester is a lightweight, pure Python library designed for straightforward web scraping without external dependencies.

## Features

- **Pure Python**: No third-party dependencies required.
- **`Model`-`Field` structure**: Define scraping targets using a clear, class-based approach.
- **Flexible parsing**: Use Python's standard libraries to parse and extract data.

## Installation

Installing via pip:

```bash
pip install harvester
```

Or directly from the source code:

```bash
pip install git+https://github.com/blazaid/harvester
```

## Requirements

Harvester is compatible with Python >= 3.8 versions. There are no mandatory external dependencies. However, for certain
features, the `chardet` library may be beneficial. If `chardet` is not installed, those features will be bypassed with a
warning.

## Usage

Define your data models by subclassing `Model` and specifying fields:

```python
from harvester import Model, StringField, IntegerField

class Product(Model):
    name = StringField()
    price = IntegerField()
```

Parse the HTML content and extract data using the model:

```python
from harvester import parse_html

html_content = """
<html>
<body>
    <h1 class="product-name">Example Product</h1>
    <span class="product-price">100</span>
</body>
</html>
"""

mapping = {
    "name": "h1.product-name",
    "price": "span.product-price"
}

product = parse_html(html_content, Product, mapping=mapping)
print(product.to_dict())
```

This will output:

```python
{"name": "Example Product", "price": 100}
```

## Documentation

Comprehensive documentation is forthcoming and will be available on Read the Docs. In the meantime, the source code is
the best place to find information.

## Contributing

Contributions are welcome! Please review the [issues](https://github.com/blazaid/harvester/issues) for current topics
and feel free to submit pull requests. Also make sure to read the [contributing guidelines](CONTRIBUTING.md) to get
started.

## License

Harvester is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file detailed information.
