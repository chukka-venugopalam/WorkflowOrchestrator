# Architecture - FoodApp

## System Architecture

Clean Architecture with UI view layer, domain state management,
and local data persistence.

## Folder Structure

```
README.md
ARCHITECTURE.md
.gitignore
pyproject.toml
app/
  screens/
  components/
  services/
  assets/
ios/
android/
tests/
docs/
```

## Technology Stack

- **Language:** Python
- **Framework:** Standard Library
- **Testing:** pytest
- **Deployment:** Local execution

## Services

- **Application Logic:** Core domain rules and state
- **Data Storage Service:** Local or remote data persistence

## Database

- Primary: SQLite
- Cache: In-memory LRU

## Communication Flow

Client Input → Application Controller → Service Layer → Data Storage

## Deployment

Cloud provider (AWS/GCP/Vercel)
