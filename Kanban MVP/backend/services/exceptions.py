class PhaseNotEmptyError(Exception):
    """Raised when trying to delete a phase that still contains cards."""
    def __init__(self, phase_name: str):
        self.phase_name = phase_name
        super().__init__(f"A fase '{phase_name}' não pode ser excluída pois contém cards.")
