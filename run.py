import os
from multiprocessing import freeze_support

import uvicorn
from dotenv import load_dotenv


def main():
    load_dotenv()
    uvicorn.run("backend.app:app", host="127.0.0.1", port=int(os.getenv("PORT", "3000")), reload=True)


if __name__ == "__main__":
    freeze_support()
    main()
