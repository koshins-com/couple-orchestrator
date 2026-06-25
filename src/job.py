import uuid
from task import Task


class Job:
    id: uuid.UUID
    tasks: list[Task]
