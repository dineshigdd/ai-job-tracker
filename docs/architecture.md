# System Architecture
This document outlines the high-level architecture, data flows, and technology interactions for the application.

## 1. High-Level Architecture

The system follows a decoupled client-server architecture, containerized via Docker for development and production parity.

```
+-------------------------------------------------------------+
|                       React Frontend                        |
|                   (TypeScript + Vite)                       |
+-------------------------------------------------------------+
                               |
                        HTTP / REST (JWT)
                               |
                               v
+-------------------------------------------------------------+
|                      FastAPI Backend                        |
|                 (Python + Pydantic + JWT)                   |
+-------------------------------------------------------------+
            |                                   |
            | SQL Queries                       | API Calls
            v                                   v
+-----------------------+           +-------------------------+
|      PostgreSQL       |           |       OpenAI API        |
|    (Relational DB)    |           | (AI Generation Service) |
+-----------------------+           +-------------------------+

```