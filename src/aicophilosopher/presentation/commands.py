

class Commands:
    async def new_project(self, title: str, question: str | None = None, directory: str | None = None) -> dict[str, object]:
        raise NotImplementedError

    async def list_projects(self, status: str | None = None) -> list[dict[str, object]]:
        raise NotImplementedError

    async def open_project(self, project_id: str) -> dict[str, object]:
        raise NotImplementedError

    async def refine_goal(self) -> dict[str, object]:
        raise NotImplementedError

    async def start_workstream(self, workstream_type: str, goal: str | None = None, instructions: str | None = None) -> dict[str, object]:
        raise NotImplementedError

    async def pause(self, workstream_id: str) -> dict[str, object]:
        raise NotImplementedError

    async def resume(self, workstream_id: str) -> dict[str, object]:
        raise NotImplementedError

    async def steer(self, workstream_id: str, instruction: str) -> dict[str, object]:
        raise NotImplementedError

    async def show_hypotheses(self, status: str | None = None, tradition: str | None = None) -> list[dict[str, object]]:
        raise NotImplementedError

    async def show_dead_ends(self) -> list[dict[str, object]]:
        raise NotImplementedError

    async def show_document(self, section: str | None = None, show_annotations: bool = False) -> str:
        raise NotImplementedError

    async def add_note(self, text: str, attach_to: str | None = None) -> dict[str, object]:
        raise NotImplementedError

    async def status(self) -> dict[str, object]:
        raise NotImplementedError

    async def compare_traditions(self, topic: str, traditions: list[str] | None = None) -> dict[str, object]:
        raise NotImplementedError

    async def config(self, key: str | None = None, value: str | None = None) -> dict[str, object]:
        raise NotImplementedError
