.PHONY: install setup-sample-db run test docker-up docker-down lint clean

# Install all Python dependencies
install:
	pip install -r requirements.txt

# Create the sample SQLite database
setup-sample-db:
	python database/sample_data.py

# Run the Streamlit app (creates sample DB if missing)
run: setup-sample-db
	streamlit run app.py

# Run the test suite
test:
	pytest tests/ -v

# Start all services with Docker Compose
docker-up:
	docker compose up --build -d
	@echo ""
	@echo "Services started. Open http://localhost:8501"
	@echo "Pull an Ollama model:  docker compose exec ollama ollama pull llama3.2"

# Stop Docker services
docker-down:
	docker compose down

# Lint with ruff (install separately: pip install ruff)
lint:
	ruff check .

# Remove generated artefacts
clean:
	rm -f sample_ecommerce.db
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
