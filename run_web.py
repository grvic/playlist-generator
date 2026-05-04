"""Entry point for running the web server."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "playlist_generator.web:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
