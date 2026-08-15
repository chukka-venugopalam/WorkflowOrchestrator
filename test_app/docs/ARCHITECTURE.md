# Architecture - Test App

## System Architecture

Layered architecture with presentation layer (UI components),
application layer (services, controllers), and domain layer.
Communicates via HTTP RESTful or GraphQL endpoints.

## Folder Structure

```
README.md
ARCHITECTURE.md
.gitignore
package.json
src/
  components/
  pages/
  api/
  lib/
  utils/
  styles/
  hooks/
  types/
public/
tests/
  unit/
  integration/
scripts/
config/
docs/
```

## Technology Stack

- **Language:** TypeScript
- **Framework:** Next.js 14+
- **Styling:** Tailwind CSS
- **State_Management:** Zustand
- **Database:** SQLite
- **Api:** REST API
- **Testing:** Vitest
- **Deployment:** Vercel / Local

## Services

- **Application Logic:** Core domain rules and state
- **Data Storage Service:** Local or remote data persistence
- **Auth Service:** Authentication and authorization
- **API Gateway:** Routing and validation

## Database

- Primary: SQLite
- Cache: In-memory LRU

## Communication Flow

Client Input → Application Controller → Service Layer → Data Storage

## Deployment

Cloud provider (AWS/GCP/Vercel)
