# Makefile för KortSubs

.PHONY: help install run docker-build docker-run clean

help:
	@echo "Tillgängliga kommandon:"
	@echo "  make install       - Skapa venv och installera dependencies"
	@echo "  make run           - Starta FastAPI lokalt"
	@echo "  make docker-build  - Bygg Docker-image"
	@echo "  make docker-run    - Kör Docker-container"
	@echo "  make clean         - Ta bort venv och cache"

install:
	python -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

run:
	. .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t kortsubs .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env kortsubs

clean:
	rm -rf .venv __pycache__ */__pycache__
