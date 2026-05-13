from typing import Any, overload


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
        self._registry[self._key(interface)] = implementation

    @overload
    def resolve(self, interface: type) -> Any: ...
    @overload
    def resolve(self, interface: str) -> Any: ...
    def resolve(self, interface: type | str) -> Any:
        key = interface if isinstance(interface, str) else self._key(interface)
        if key in self._instances:
            return self._instances[key]
        if key in self._registry:
            impl = self._registry[key]
            instance = impl()
            self._instances[key] = instance
            return instance
        raise NotImplementedError(f"No adapter registered for {key}")

    def register_instance(self, interface: type | str, instance: Any) -> None:
        """Register a pre-built instance for a given interface type or name."""
        key = interface if isinstance(interface, str) else self._key(interface)
        self._instances[key] = instance

    @staticmethod
    def _key(interface: type) -> str:
        mod = getattr(interface, "__module__", "")
        name = getattr(interface, "__name__", str(interface))
        return f"{mod}.{name}" if mod else name
