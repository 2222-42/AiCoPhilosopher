from typing import Any


class Container:
    def __init__(self, config: dict[str, Any] | None = None):
        self._registry: dict[str, Any] = {}
        self._instances: dict[str, Any] = {}
        self.config = config or {}

    def register(self, interface: type, implementation: Any) -> None:
        self._registry[interface.__name__] = implementation

    def resolve(self, interface_name: str) -> Any:
        if interface_name in self._instances:
            return self._instances[interface_name]
        if interface_name in self._registry:
            impl = self._registry[interface_name]
            instance = impl()
            self._instances[interface_name] = instance
            return instance
        raise NotImplementedError(f"No adapter registered for {interface_name}")

    def register_instance(self, interface_name: str, instance: Any) -> None:
        self._instances[interface_name] = instance
