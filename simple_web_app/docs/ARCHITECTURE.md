# Architecture - Simple Web App

## System Architecture

Minimal, standalone single-package architecture for a web project.
Focuses on core functionality in a clean, flat layout without multi-service overhead.

## Folder Structure

```
README.md
ARCHITECTURE.md
.gitignore
package.json
src/
tests/
```

## Technology Stack

- **Language:** TypeScript
- **Framework:** React / Vite
- **Styling:** Tailwind CSS
- **State_Management:** Zustand
- **Database:** SQLite
- **Api:** REST API
- **Testing:** Vitest
- **Deployment:** Vercel / Local

## Services

- **Core Application Logic:** Handles primary features and state management

## Database

- Primary: None (In-memory / Local File Storage)
- Cache: None

## Communication Flow

Client Input → Application Controller → Service Layer → Data Storage

## Deployment

Local execution / Standalone binary
