# Architecture - SudokuGame

## System Architecture

Modular game architecture with scene management, entity-component-system (ECS),
input handling, rendering pipeline, and local asset storage.

## Folder Structure

```
README.md
ARCHITECTURE.md
.gitignore
requirements.txt
src/
  entities/
  scenes/
  systems/
assets/
  sprites/
  audio/
tests/
docs/
```

## Technology Stack

- **Language:** C# / TypeScript
- **Framework:** Unity / WebGL
- **Rendering:** WebGL / OpenGL
- **State_Management:** Local Game Engine Loop
- **Database:** None (Local File / In-Memory)
- **Testing:** pytest
- **Deployment:** Standalone Executable / Local Python script

## Services

- **Core Application Logic:** Handles primary features and state management

## Database

- Primary: None (In-memory / Local File Storage)
- Cache: None

## Communication Flow

User Input → Event Handler → Game Engine Loop → Entity/State Update → Render Pipeline

## Deployment

Local execution / Standalone binary
