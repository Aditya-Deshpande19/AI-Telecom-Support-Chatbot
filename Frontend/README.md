# Jio RAG Support Agent — Frontend

React + Vite SPA for the Jio RAG Support Agent backend.

## Prerequisites

- Node.js 20+
- Backend API running on `http://localhost:8080`

## Setup

```bash
npm install
cp .env.example .env   # edit VITE_API_URL if needed
npm run dev            # starts on http://localhost:8000
```

## Build for production

```bash
npm run build          # outputs to dist/
npm run preview        # preview the production build locally
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

## Notes

- All API requests require `X-API-Key` header — entered at the login screen
- The login screen validates the key against `/stats` before granting access
- Conversation history persists in the backend SQLite database