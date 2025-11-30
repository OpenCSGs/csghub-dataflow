import uvicorn
import os

# API_SERVER = os.environ.get("API_SERVER", "192.168.10.72")
API_SERVER = os.environ.get("API_SERVER", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", 8000))


def serve():
    uvicorn.run("data_server.main:app", host=API_SERVER, port=API_PORT)


if __name__ == "__main__":
    serve()
    # print(API_SERVER)