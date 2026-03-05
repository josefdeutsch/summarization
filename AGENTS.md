# AGENTS.md

## Repository Purpose

This repository contains a small Python service that exposes an API.

The service will provide endpoints that trigger structured processing workflows and return JSON responses.

The API is designed to run locally during development and later be deployed on AWS.

---

## Technology Stack

* Python
* FastAPI
* Uvicorn
* Docker (for containerization)

---

## Project Goals

* Maintain a minimal and readable architecture.
* Prefer simple implementations over complex frameworks.
* Ensure the service can run locally and inside a container.
* All endpoints should return JSON.

---

## Current Development Goal

Implement a minimal FastAPI server with:

Endpoint:
GET /health
Returns:
{"status": "ok"}

Endpoint:
POST /run-curator
Receives a request and returns a mock JSON response for now.

This endpoint will later trigger a processing workflow.

---

## Expected Project Structure

The project should remain small and easy to understand.

Example structure:

app/
main.py

requirements.txt
Dockerfile
README.md

Avoid unnecessary folders unless required.

---

## Coding Principles

* Keep implementations minimal.
* Avoid introducing large frameworks.
* Prefer clear, readable code.
* Modify only files relevant to the current task.

---

## Containerization

The API should run inside a Docker container.

Requirements:

* Use a lightweight Python base image
* Install dependencies from requirements.txt
* Start the server using uvicorn
* Expose port 8000

---

## Branch Workflow

Feature work happens on feature branches.

Example:
feature/aws-fastapi-server

Experimental work created by coding agents may use:
codex/*

Changes should remain focused and limited to the task being implemented.

---

## Important Constraints

* Do not introduce AWS infrastructure yet.
* Do not introduce authentication yet.
* Do not add unnecessary complexity.
* Prefer minimal working implementations first.
