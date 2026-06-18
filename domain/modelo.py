from dataclasses import dataclass

@dataclass
class UserProfile:
    precision_avg: float = 0.0
    consistencia_avg: float = 0.0
    error_avg: float = 0.0
    sessions: int = 0