from fastapi import FastAPI

app = FastAPI(title="Weather Proxy")


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
