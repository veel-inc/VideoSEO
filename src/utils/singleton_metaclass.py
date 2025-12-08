from abc import ABCMeta
from threading import Lock
from typing import Dict


class SingletonMetaClass(type):
    """
    A thread-safe implementation of Singleton metaclass.
    """

    _instances: Dict = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            return cls._instances[cls]


class SingletonABCMeta(SingletonMetaClass, ABCMeta):
    pass
