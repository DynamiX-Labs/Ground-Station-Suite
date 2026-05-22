# DynamiX-Labs Ground Station Suite - Development Manual

This guide provides comprehensive instructions for setting up the development environment, compiling software-defined radio (SDR) components, running tests, and adhering to engineering standards within the DynamiX-Labs Ground Station Suite ecosystem.

## Engineering Prerequisites

To construct and execute the suite locally, the following runtime environments are required:

*   **Python:** Version 3.12 (Strictly matching `pyproject.toml` specification)
*   **Node.js:** Version 18.0 or later (Recommended for the Vite-based React frontend)
*   **C++ Toolchain:** GCC/Clang with CMake (Required for building GNU Radio out-of-tree modules)
*   **Docker Engine:** Optional, for isolated container deployment

---

## Workspace Installation

You can configure your local environment using the modern `pyproject.toml` packaging system (highly recommended) or traditional requirements files.

### Option 1: Using pyproject.toml (Standard Workflow)

The Python backend leverages standard Python packaging configurations. This isolates dependencies and simplifies module resolution.

#### 1. Backend Environment Setup
Navigate to the backend directory, establish a virtual environment, and install the package in editable mode:

```bash
cd backend
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Install core packages in editable mode
pip install -e .

# Install development-specific dependencies (testing, formatting, and analysis tools)
pip install -e ".[dev]"

# Start the development server
python app.py --host 0.0.0.0 --port 5000
```

#### 2. Frontend Environment Setup
Navigate to the frontend directory, install npm packages, and launch the Vite development server:

```bash
cd frontend
npm install
npm run dev
```

The development server proxies API requests and WebSocket channels to the backend server (configured in `.env.development`, defaulting to `localhost:5000`).

### Option 2: Using requirements.txt (Legacy/Fallback Workflow)

#### 1. Backend Environment Setup
```bash
cd backend
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Install standard dependencies
pip install -r requirements.txt

# Install development-specific dependencies
pip install -r requirements-dev.txt

# Launch the backend service
python app.py --host 0.0.0.0 --port 5000
```

#### 2. Frontend Environment Setup
```bash
cd frontend
npm install
npm run dev
```

---

## Out-Of-Tree Modules and LoRa Decoder Compilation

The suite integrates an advanced LoRa physical layer decoder utilizing GNU Radio 3.10 and `gr-lora_sdr`. To guarantee compatibility with NumPy 2.x, GNU Radio and its associated out-of-tree modules must be built from source if deployed outside of Docker.

### 1. Build and System Dependencies
Install compilation tools and required libraries:

```bash
sudo apt-get update
sudo apt-get install -y cmake libboost-all-dev libgmp-dev libmpfr-dev \
    liblog4cpp5-dev libspdlog-dev libfmt-dev libvolk-dev \
    pybind11-dev python3-pybind11
```

### 2. Compile GNU Radio 3.10 from Source
To prevent system-wide package conflicts, compile GNU Radio directly inside the active virtual environment:

```bash
# Verify virtual environment activation
source backend/venv/bin/activate

# Install required build packages
pip install packaging pybind11

# Clone and compile GNU Radio repository
cd /tmp
git clone --recursive https://github.com/gnuradio/gnuradio.git
cd gnuradio
git checkout maint-3.10
mkdir build && cd build

# Configure CMake to target the virtual environment paths
cmake -DCMAKE_BUILD_TYPE=Release \
      -DENABLE_PYTHON=ON \
      -DENABLE_GR_QTGUI=OFF \
      -DENABLE_TESTING=OFF \
      -DPython3_EXECUTABLE=$VIRTUAL_ENV/bin/python3 \
      -DPYTHON_EXECUTABLE=$VIRTUAL_ENV/bin/python3 \
      -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV \
      ..

# Compile and install
make -j$(nproc)
make install
```

### 3. Compile gr-lora_sdr Out-of-Tree Module
Once GNU Radio is installed in the virtual environment, compile the custom LoRa SDR blocks:

```bash
cd /tmp
git clone https://github.com/tapparelj/gr-lora_sdr.git
cd gr-lora_sdr
mkdir build && cd build

# Install to virtual environment prefix
cmake -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV ..
make -j$(nproc)
make install
```

### 4. Adjust Environment Variables
Append the virtual environment's library paths to make Python aware of the compiled modules:

```bash
cd <project-root>
echo 'export LD_LIBRARY_PATH=$VIRTUAL_ENV/lib:$LD_LIBRARY_PATH' >> backend/venv/bin/activate
source backend/venv/bin/activate
```

### 5. Verification
Execute the following verification script to confirm that both GNU Radio and the LoRa decoder are accessible within Python:

```bash
python -c "from gnuradio import gr, lora_sdr; print('LoRa decoder integration validated successfully.')"
```

> [!NOTE]
> Out-of-tree module compilation is only required for native local development. Pre-built multi-architecture Docker images contain fully compiled environments containing GNU Radio, SoapySDR, and necessary decoder blocks.

---

## Code Quality, Formatting, and Workflows

To preserve the engineering standards of DynamiX-Labs, all contributions must undergo automated styling and formatting checks.

### Code Formatting and Formatting Rules

All Python code must be formatted using Black and imports sorted via isort prior to submission:

```bash
# Auto-format all Python code blocks (configured line length: 100)
black .

# Standardize Python imports
isort .
```

### Automated Testing

#### 1. Backend Testing (Python)
Unit and integration tests are driven by `pytest`. Ensure your virtual environment is active before running tests:

```bash
cd backend

# Execute complete test suite with coverage analysis
pytest

# Execute specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m slow          # Long-running benchmark and signal processing tests

# Generate interactive HTML coverage reports
pytest --cov=crud --cov=server --cov=controllers --cov-report=html
```

#### 2. Frontend Testing (React / Vitest)
The React client leverages Vitest for lightning-fast unit tests and Playwright/Cypress for comprehensive end-to-end integration flows.

```bash
cd frontend

# Execute unit and component tests
npm test

# Generate frontend coverage report
npm run test:coverage

# Execute end-to-end tests (requires active development server)
npm run test:e2e

# Launch the interactive end-to-end test runner
npm run test:e2e:ui
```

### Pre-commit Integration
We utilize pre-commit hooks to automate formatting validation before commits are allowed in git.

```bash
# Initialize pre-commit within the environment
pre-commit install

# Execute pre-commit validation manually across the entire codebase
pre-commit run --all-files
```

---

## Package and Build Configurations

The Python backend is managed as a structured, discoverable package with the following attributes:

*   **Package Name:** `ground-station`
*   **Active Specification Version:** `0.1.0`
*   **Minimum Target Python Runtime:** `3.12`
*   **Core License:** `GNU GPL v3`
*   **Suite CLI Entrypoint:** `ground-station` (launches server daemon)

You can run the ground station system globally by installing it directly to your environment:

```bash
pip install -e .
ground-station
```
