from backend.app import create_app

app = create_app()


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
