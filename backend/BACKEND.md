# AdsGenerator Backend

Starter FastAPI backend scaffold for the AdsGenerator app.

## Tech

- FastAPI
- Uvicorn
- Pydantic Settings

## Project Structure

```text
backend/
  app/
    api/
      v1/
        endpoints/
    core/
    services/
    main.py
  tests/
  pyproject.toml
```

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -e .`
3. Run the API:
   - `uvicorn app.main:app --reload`
4. Open docs:
   - <http://127.0.0.1:8000/docs>

## Notes

- AI model and Firebase integrations are intentionally stubs for now.
- Add real implementations under `app/services/`.
