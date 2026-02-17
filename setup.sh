#!/bin/bash
# FINCENTER Setup Script
# This script sets up the entire project from scratch

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  FINCENTER - Setup Script${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."
    
    local missing=0
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        missing=1
    else
        python_version=$(python3 --version | cut -d' ' -f2)
        print_success "Python ${python_version} found"
    fi
    
    if ! command_exists docker; then
        print_error "Docker is not installed"
        missing=1
    else
        print_success "Docker found"
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed"
        missing=1
    else
        print_success "Docker Compose found"
    fi
    
    if [ $missing -eq 1 ]; then
        print_error "Please install missing prerequisites"
        exit 1
    fi
    
    echo ""
}

# Create virtual environment
setup_venv() {
    print_step "Setting up Python virtual environment..."
    
    if [ -d ".venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Delete and recreate? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf .venv
        else
            print_warning "Skipping venv creation"
            return
        fi
    fi
    
    python3 -m venv .venv
    print_success "Virtual environment created"
    
    # Activate venv
    source .venv/bin/activate
    print_success "Virtual environment activated"
    
    # Upgrade pip
    print_step "Upgrading pip..."
    pip install --upgrade pip -q
    print_success "Pip upgraded"
    
    echo ""
}

# Install dependencies
install_dependencies() {
    print_step "Installing Python dependencies..."
    
    # Make sure venv is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        print_error "Virtual environment not activated"
        source .venv/bin/activate
    fi
    
    # Install production dependencies
    print_step "Installing production dependencies..."
    pip install -r requirements.txt -q
    print_success "Production dependencies installed"
    
    # Install development dependencies
    read -p "Install development dependencies? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Installing development dependencies..."
        pip install -r requirements-dev.txt -q
        print_success "Development dependencies installed"
    fi
    
    # Download spaCy model
    print_step "Downloading spaCy French language model..."
    python -m spacy download fr_core_news_lg -q
    print_success "spaCy model downloaded"
    
    echo ""
}

# Setup environment variables
setup_env() {
    print_step "Setting up environment variables..."
    
    if [ -f ".env" ]; then
        print_warning ".env file already exists"
        read -p "Overwrite? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Skipping .env creation"
            return
        fi
    fi
    
    cp .env.example .env
    print_success ".env file created"
    print_warning "Please edit .env file with your configuration"
    
    echo ""
}

# Create directory structure
create_directories() {
    print_step "Creating directory structure..."
    
    mkdir -p data/{synthetic,processed,raw}/{budgets,invoices,contracts,accounting}
    mkdir -p data/vectors
    mkdir -p logs
    mkdir -p models
    
    print_success "Directories created"
    echo ""
}

# Start Docker services
start_docker() {
    print_step "Starting Docker services..."
    
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    
    docker-compose up -d
    
    print_success "Docker services started"
    print_step "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    print_step "Checking Neo4j..."
    if curl -s http://localhost:7474 > /dev/null; then
        print_success "Neo4j is ready (http://localhost:7474)"
    else
        print_warning "Neo4j may not be ready yet"
    fi
    
    print_step "Checking PostgreSQL..."
    if docker exec fincenter-postgres pg_isready -U fincenter > /dev/null 2>&1; then
        print_success "PostgreSQL is ready"
    else
        print_warning "PostgreSQL may not be ready yet"
    fi
    
    print_step "Checking Redis..."
    if docker exec fincenter-redis redis-cli -a fincenter2024 ping > /dev/null 2>&1; then
        print_success "Redis is ready"
    else
        print_warning "Redis may not be ready yet"
    fi
    
    echo ""
}

# Generate synthetic data
generate_data() {
    print_step "Generating synthetic data..."
    
    read -p "Generate synthetic data now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Make sure venv is activated
        if [ -z "$VIRTUAL_ENV" ]; then
            source .venv/bin/activate
        fi
        
        python scripts/producer.py \
            --output data/synthetic/ \
            --num-invoices 500 \
            --num-contracts 50 \
            --messiness 0.3
        
        print_success "Synthetic data generated"
    else
        print_warning "Skipping data generation"
    fi
    
    echo ""
}

# Run tests
run_tests() {
    print_step "Running tests..."
    
    read -p "Run tests now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Make sure venv is activated
        if [ -z "$VIRTUAL_ENV" ]; then
            source .venv/bin/activate
        fi
        
        pytest tests/ -v
        print_success "Tests completed"
    else
        print_warning "Skipping tests"
    fi
    
    echo ""
}

# Final instructions
print_final_instructions() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Setup Complete! 🎉${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Activate virtual environment:"
    echo -e "   ${BLUE}source .venv/bin/activate${NC}"
    echo ""
    echo "2. Edit configuration (if needed):"
    echo -e "   ${BLUE}nano .env${NC}"
    echo ""
    echo "3. Generate synthetic data (if not done):"
    echo -e "   ${BLUE}python scripts/producer.py --output data/synthetic/${NC}"
    echo ""
    echo "4. Run ingestion pipeline:"
    echo -e "   ${BLUE}python src/ingestion/pipeline.py --input data/synthetic/${NC}"
    echo ""
    echo "5. Start API server:"
    echo -e "   ${BLUE}python src/api/main.py --debug --port 8080${NC}"
    echo ""
    echo "6. Access services:"
    echo -e "   • API: ${BLUE}http://localhost:8080/docs${NC}"
    echo -e "   • Neo4j: ${BLUE}http://localhost:7474${NC} (neo4j/fincenter2024)"
    echo ""
    echo "For more information, see README.md"
    echo ""
}

# Main execution
main() {
    print_header
    
    check_prerequisites
    setup_venv
    install_dependencies
    setup_env
    create_directories
    start_docker
    generate_data
    run_tests
    print_final_instructions
}

# Run main function
main
