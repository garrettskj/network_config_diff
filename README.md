# Network Device Configuration Comparison Tool

A modern web application for comparing network device configurations with File and SSH connectivity, built with Flask, netmiko, and comprehensive testing.

## Features

- **Dual-device interface** for side-by-side configuration comparison
- **Multi-vendor support** (Cisco IOS/NX-OS/ASA, Juniper JunOS)
- **Color-coded diff visualization** with statistics
- **Parallel SSH connections** for faster performance
- **File upload capability** - upload configuration files as alternative to SSH
- **Configuration storage** - automatically saves retrieved configs with timestamps
- **Comprehensive logging** with logzero for debugging and monitoring
- **Type-safe Python** with full type hints
- **98% test coverage** with comprehensive test suite
- **Production-ready Docker setup** with persistent storage

## Architecture

```
config_diff/
   app.py                 # Flask web application
   lib/
      network_client.py  # SSH connectivity & device management
      config_diff.py     # Configuration comparison & diff generation
   templates/             # HTML templates
   tests/                 # Comprehensive test suite (42 tests)
   Dockerfile            # Production container setup
   docker-compose.yml    # Container orchestration
```

## Quick Start

### Option 1: Docker (Recommended)

1. **Clone and run with Docker Compose:**
   ```bash
   git clone <repository-url>
   cd network_config_diff
   docker-compose up --build
   ```

2. **Access the application:**
   - Open http://localhost:5000 in your browser

### Option 2: Local Development

1. **Prerequisites:**
   - Python 3.11+
   - uv package manager

2. **Install dependencies:**
   ```bash
   # Install uv if not already installed
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install project dependencies
   uv sync
   ```

3. **Run the application:**
   ```bash
   # Development server
   uv run python app.py
   
   # Production server with Gunicorn
   uv run gunicorn --bind 0.0.0.0:5000 --workers 2 app:app
   ```

4. **Access the application:**
   - Open http://localhost:5000 in your browser

## Usage

### Input Methods

For each device, you can choose between two input methods:

1. **SSH Connection:**
   - Device Type (Cisco IOS, NX-OS, ASA, or Juniper JunOS)
   - IP Address
   - Username and Password

2. **File Upload:**
   - Upload configuration files (.txt, .cfg, .conf)
   - Optional device name for better identification
   - Drag-and-drop support for easy file selection

### Comparison Process

1. **Select input method** for each device using toggle buttons
2. **Provide credentials or upload files** as appropriate
3. **Click "Compare Configurations"**
4. **View color-coded diff** in new window with statistics

### Security Notes

- Credentials are not stored or logged
- SSH connections use industry-standard libraries
- Application runs as non-root user in Docker
- Uploaded files are validated before processing

### Configuration Storage
- Retrieved configurations are automatically saved to `stored_configs/`
- Both SSH-retrieved and uploaded configs are stored with metadata
- Files include timestamp and device/file information
- Accessible via Docker volumes for persistence

### File Upload Requirements

- **Supported formats:** .txt, .cfg, .conf
- **Content validation:** Files must contain network configuration elements
- **Size limits:** Reasonable file sizes (handled by Flask)
- **Encoding:** UTF-8 text files only

### Logging and Debugging

- Set `LOG_LEVEL=DEBUG` for detailed debugging information
- Logs include SSH connections, file uploads, validation, and diff generation
- Use `LOG_FILE` environment variable for persistent log storage

## Development

### Running Tests

```bash
# Run all tests with coverage
uv run pytest tests/ -v --cov=lib --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/test_network_client.py -v

# Generate coverage report
uv run pytest --cov=lib --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

### Code Quality

```bash
# Format code with Black
uv run black lib/ app.py tests/

# Lint with Ruff (PEP 8 compliance)
uv run ruff check lib/ app.py tests/

# Auto-fix linting issues
uv run ruff check --fix lib/ app.py tests/
```

### Project Structure

- **`lib/network_client.py`** - NetworkClient class for SSH device connectivity
- **`lib/config_diff.py`** - ConfigDiffer class for configuration comparison
- **`app.py`** - Flask application with type hints and error handling
- **`tests/`** - Comprehensive test suite with mocking

### Adding New Device Types

1. **Add device type to templates/index.html:**
   ```html
   <option value="new_device_type">New Device Type</option>
   ```

2. **Ensure netmiko supports the device type** (most are already supported)

3. **Add tests** in `tests/test_network_client.py` for the new device type

## Testing Coverage

Current test coverage: **90%**

- **Network Client Tests:** SSH connectivity, error handling, parameter validation, configuration storage, file upload validation
- **Config Diff Tests:** Diff generation, HTML escaping, statistics calculation, logging
- **Flask App Tests:** Routes, form handling, error responses, threading, file upload functionality
- **Integration Tests:** End-to-end workflow testing with both SSH and file upload methods

## Production Deployment

### Docker Production Setup

The Dockerfile uses a **multi-stage build** for optimized production images:

- **Build stage**: Compiles dependencies with build tools
- **Production stage**: Lightweight runtime image with only necessary components
- **Security**: Runs as non-root user with minimal attack surface
- **Performance**: Smaller image size and faster deployment

```bash
# Build production image (multi-stage)
docker build -t config-diff:latest .

# Run with custom configuration
docker run -d \
  --name config-diff \
  -p 5000:5000 \
  --restart unless-stopped \
  config-diff:latest
```

**Multi-stage benefits:**
- Reduced image size (excludes build dependencies)
- Enhanced security (minimal runtime footprint)
- Faster deployment and container startup
- Cached dependency layers for efficient rebuilds

### Environment Variables

- **`FLASK_ENV`** - Set to `production` for production deployment
- **`FLASK_DEBUG`** - Set to `0` for production (default in Docker)
- **`LOG_LEVEL`** - Set logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
- **`LOG_FILE`** - Optional path to log file for persistent logging

### Security Considerations

- Application runs as non-root user in container
- No credential storage or logging (passwords masked in logs)
- SSH connections timeout after 30 seconds
- Input validation and HTML escaping
- Configuration files stored securely with proper permissions
- Regular security updates via base image updates

## Troubleshooting

### Common Issues

1. **SSH Connection Failures:**
   - Verify device IP and credentials
   - Check network connectivity
   - Ensure SSH is enabled on target devices

2. **Import Errors:**
   - Ensure all dependencies installed: `uv sync`
   - Check Python version (3.11+ required)

3. **Docker Build Issues:**
   - Clear Docker cache: `docker system prune`
   - Ensure sufficient disk space

### Debug Mode

```bash
# Run with debug logging
LOG_LEVEL=DEBUG uv run python app.py

# With log file
LOG_LEVEL=DEBUG LOG_FILE=debug.log uv run python app.py

# Docker with debug logging
docker run -e LOG_LEVEL=DEBUG -e LOG_FILE=/app/logs/debug.log config-diff
```

### Configuration Storage

- **Location:** `stored_configs/` directory
- **Format:** `{host}_{device_type}_{timestamp}.cfg`
- **Contents:** Original config with metadata header
- **Persistence:** Use Docker volumes for long-term storage

## Contributing

1. **Fork the repository**
2. **Create feature branch:** `git checkout -b feature-name`
3. **Add tests** for new functionality
4. **Ensure 100% test coverage:** `uv run pytest --cov=lib --cov=app`
5. **Format code:** `uv run black . && uv run ruff check --fix .`
6. **Submit pull request**

## License

MIT License - See LICENSE file for details.

## Dependencies

- **Flask** - Web framework
- **netmiko** - SSH network device connectivity
- **logzero** - Simple and effective logging
- **uv** - Modern Python package manager
- **pytest** - Testing framework
- **black** - Code formatting
- **ruff** - Fast Python linter

For complete dependency list, see `pyproject.toml`.

