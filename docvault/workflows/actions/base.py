"""Base class for workflow action backends."""

from abc import ABC, abstractmethod


class WorkflowAction(ABC):
    """
    Abstract base class for workflow action backends.

    Subclasses must implement execute() and optionally validate_config().
    """

    @abstractmethod
    def execute(self, instance, config):
        """
        Execute the action.

        Args:
            instance: WorkflowInstance the action is running on.
            config: Dict of configuration data from WorkflowStateAction.backend_data.
        """
        ...

    def validate_config(self, config):
        """
        Validate the action configuration.

        Args:
            config: Dict of configuration data to validate.

        Returns:
            List of error messages (empty if valid).
        """
        return []
