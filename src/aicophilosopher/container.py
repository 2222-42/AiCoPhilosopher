from typing import Any


class Container:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._registry: dict[str, type[Any]] = {}
        self._instances: dict[str, Any] = {}
        self.config = config or {}

    def register(self, interface: type, implementation: type[Any]) -> None:
        """Register an adapter class (not instance) for a given interface type.

        `implementation` must be a class/callable that `resolve()` will instantiate
        via `implementation()`. Use `register_instance()` for pre-built instances.
        """
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
        """Register a pre-built instance for a given interface name."""
        self._instances[interface_name] = instance
