from functools import wraps
from threading import Lock

from fastapi import HTTPException


model_task_lock = Lock()


def model_task(function):
    @wraps(function)
    def run(*args, **kwargs):
        if not model_task_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="模型或燒錄任務執行中，請完成後再試。", headers={"Retry-After": "5"})
        try:
            return function(*args, **kwargs)
        finally:
            model_task_lock.release()
    return run
