# realivideo pipeline — build a test príkazy
# Použitie: make <cieľ>   (make bez argumentu vypíše nápovedu)

IMAGE_CPU ?= realivideo-cpu:dev
IMAGE_GPU ?= realivideo-gpu:dev

.DEFAULT_GOAL := help
.PHONY: help build-cpu build-cpu-amd64 smoke-cpu shell-cpu build-gpu clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

build-cpu: ## Zostaví CPU image natívne (na Macu = arm64) — na lokálne testovanie
	docker build -f docker/Dockerfile.cpu -t $(IMAGE_CPU) .

build-cpu-amd64: ## Zostaví CPU image pre RunPod (x86_64) — na Macu cez emuláciu, pomalé
	docker build --platform linux/amd64 -f docker/Dockerfile.cpu -t $(IMAGE_CPU)-amd64 .

smoke-cpu: ## Overí, že COLMAP + ffmpeg v CPU image naozaj fungujú
	docker run --rm -v "$(PWD)/scripts:/workspace/scripts:ro" $(IMAGE_CPU) \
	  bash /workspace/scripts/smoke-test-cpu.sh

shell-cpu: ## Interaktívny shell v CPU image (data/ sa namountuje do /workspace)
	@mkdir -p data
	docker run --rm -it -v "$(PWD)/data:/workspace/data" $(IMAGE_CPU) bash

build-gpu: ## Zostaví GPU image — VYŽADUJE x86_64 stroj s Dockerom, nie Mac
	@uname -m | grep -q x86_64 || { \
	  echo "❌ Si na $$(uname -m). GPU image sa dá zostaviť len na x86_64."; \
	  echo "   Viď README, sekcia 'Kde zostaviť GPU image'."; exit 1; }
	docker build -f docker/Dockerfile.gpu -t $(IMAGE_GPU) .

clean: ## Zmaže lokálne image-y
	-docker rmi $(IMAGE_CPU) $(IMAGE_CPU)-amd64 $(IMAGE_GPU) 2>/dev/null
