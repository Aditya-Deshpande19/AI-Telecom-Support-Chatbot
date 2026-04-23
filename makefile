# Jio RAG — Docker helpers
# Usage: make <target>
# Requires: Docker, Docker Compose

.PHONY: up down logs migrate-db

## Start the API container (build if needed)
up:
	docker-compose up --build -d

## Stop the API container
down:
	docker-compose down

## Stream container logs
logs:
	docker-compose logs -f api

## Migrate an existing ./chat_history.db bind-mount file into the named volume.
##
## Run this ONCE if you previously ran the container with the old bind-mount
## (./chat_history.db:/app/chat_history.db) and want to preserve your data
## after upgrading to the named-volume configuration (chat_history_data).
##
## Steps performed:
##   1. Create the volume by starting the service (if not already running)
##   2. Copy ./chat_history.db from the host into the chat_history_data volume
##   3. Restart the container so it picks up the migrated file
migrate-db:
	@echo "==> Checking for ./chat_history.db on host..."
	@if [ ! -f ./chat_history.db ]; then \
		echo "ERROR: ./chat_history.db not found. Nothing to migrate."; exit 1; \
	fi
	@echo "==> Starting container to ensure volume exists..."
	docker-compose up -d
	@echo "==> Copying ./chat_history.db into chat_history_data volume (requires Compose v2.18+)..."
	docker compose cp ./chat_history.db api:/app/data/chat_history.db
	@echo "==> Restarting container..."
	docker-compose restart api
	@echo ""
	@echo "Migration complete. Your chat history is now stored in the"
	@echo "'chat_history_data' named volume managed by Docker."
	@echo ""
	@echo "You can safely rename or remove ./chat_history.db from the host"
	@echo "once you have verified the container is working correctly."
	@echo ""
	@echo "To back up the volume at any time:"
	@echo "  docker run --rm -v chat_history_data:/data -v \$$(pwd):/backup alpine tar czf /backup/chat_history_backup.tar.gz -C /data ."