.PHONY: up down

up:
	@echo "🚀 Synthesizing VibeMap Cognitive Engine..."
	@docker-compose up -d
	@echo "🧠 Booting neural pathways (Backend & Frontend)..."
	@trap 'echo "🛑 Shutting down VibeMap..."; kill 0' SIGINT; \
		cd backend && .venv/bin/uvicorn main:app --reload --port 8000 & \
		cd frontend && npx serve -l 3000 & \
		wait

down:
	@echo "🛑 Stopping Qdrant and processes..."
	@docker-compose down
	@pkill -f "uvicorn main:app" || true
	@pkill -f "serve -l 3000" || true
