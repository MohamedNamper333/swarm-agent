---
name: code-design-patterns
description: Use for applying design patterns and software architecture decisions. Activate when the user asks about architecture, design patterns, system design, or code structure improvements.
---

# Design Patterns & Architecture

## Creational Patterns
- **Singleton**: one global instance (use sparingly)
- **Factory Method**: interface for creating objects
- **Abstract Factory**: families of related objects
- **Builder**: complex object construction step-by-step
- **Prototype**: clone existing objects

## Structural Patterns
- **Adapter**: make incompatible interfaces work together
- **Facade**: simplified interface to complex subsystem
- **Decorator**: add behavior dynamically without subclassing
- **Proxy**: control access to another object
- **Composite**: treat individual and composite objects uniformly

## Behavioral Patterns
- **Strategy**: interchangeable algorithms at runtime
- **Observer**: one-to-many dependency notification
- **Command**: encapsulate request as object (undoable)
- **Chain of Responsibility**: pass request along handler chain
- **State**: object behavior changes with internal state
- **Template Method**: skeleton algorithm, subclasses fill steps

## Architecture Patterns
- **Layered (N-tier)**: presentation → business → data
- **Hexagonal (Ports & Adapters)**: core logic isolated from IO
- **CQRS**: separate read from write models
- **Event-Driven**: decoupled services via events
- **Microservices**: independent deployable services
- **Clean Architecture**: dependency inversion at every layer

## When to Use
- Pattern first approach → leads to over-engineering
- Problem first → identify the pain point, then match the pattern
- Patterns solve specific problems, not all problems
