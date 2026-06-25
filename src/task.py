from enum import StrEnum
from typing import Any, Callable
import uuid
import docker
import docker.errors
from docker.models.containers import Container
import secrets

from errors import GeneralError, ImageNotFound


class State(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

class RunStep(StrEnum):
    pull = "pull"
    create_container = "create"
    start_container = "start"

class Task:
    id: uuid.UUID
    state: State
    name: str
    image: str
    commands: list[str]

    container: Container|None

    def __init__(self, image: str, commands: list[str] = [], name: str|None = None) -> None:
        self.state = State.pending
        self.id = uuid.uuid4()
        self.image = image
        self.commands = commands
        self.container = None
        if name:
            self.name = name
        else:
            self.name = secrets.token_urlsafe(5)

    def run(self, client: docker.DockerClient, change_step: Callable[[RunStep], Any] = print) -> None:
        try:
            change_step(RunStep.pull)
            client.images.pull(self.image)
            change_step(RunStep.create_container)
            self.container = client.containers.create(self.image, self.commands, detach=True, name=self.name)
            change_step(RunStep.start_container)
            self.container.start()
            self.state = State.running
        except docker.errors.ImageNotFound:
            raise ImageNotFound()
        except docker.errors.APIError:
            raise GeneralError()

    def get_logs(self, stdout: bool = True, stderr: bool = True) -> str:
        if self.container:
            return self.container.logs(stdout=stdout, stderr=stderr).decode("utf-8")
        return ""

    def stop(self) -> None:
        if self.container:
            self.container.stop()
            self.state = State.completed

    def delete(self) -> None:
        if self.container:
            self.container.remove()

    def update_state(self) -> State:
        if not self.container:
            if self.status == State.pending:
                self.status = State.failed
        else:
            self.container.reload()
            if self.container.status == "exited":
                result = self.container.wait()
                if result["StatusCode"]:
                    self.state = State.failed
                else:
                    self.status = State.completed
        return self.status
