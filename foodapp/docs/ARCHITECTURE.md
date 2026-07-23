# Architecture - FoodApp

## System Architecture

Clean layered architecture with separation of concerns.
Core domain logic isolated from infrastructure concerns.
Dependency injection for testability and flexibility.

## Folder Structure

```
README.md
CHANGELOG.md
ARCHITECTURE.md
CONTRIBUTING.md
LICENSE
.gitignore
.env.example
Cargo.toml
src/
  components/
  pages/
  api/
  lib/
  utils/
  styles/
  hooks/
  types/
  middleware/
public/
tests/
  unit/
  integration/
  e2e/
scripts/
config/
docs/
docker/
```

## Technology Stack

- **Language:** TypeScript
- **Framework:** Next.js 14+
- **Styling:** Tailwind CSS
- **State_Management:** Zustand / React Query
- **Database:** PostgreSQL + Prisma ORM
- **Api:** Next.js API Routes / tRPC
- **Testing:** Vitest + Playwright
- **Deployment:** Vercel / Docker
- **Ci_Cd:** GitHub Actions

## Services

- **Auth Service:** Authentication and authorization
- **API Gateway:** Request routing and rate limiting
- **Data Service:** Data persistence and retrieval
- **Cache Service:** In-memory caching for performance

## Database

- Primary: PostgreSQL
- Cache: Redis

## Communication Flow

Client → API Gateway → Service Layer → Data Layer
Synchronous: HTTP REST/gRPC for request-response patterns
Asynchronous: Message queue for event-driven communication
Caching: Redis cache between service and data layers
Monitoring: Centralized logging and metrics collection

## Deployment

Cloud provider (AWS/GCP/Azure) or Vercel/Railway
