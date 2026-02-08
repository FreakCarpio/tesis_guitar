class modelo_adaptativo:
    def __init__(self, alpha=0.8):
        self.alpha = alpha

    def update(self, profile, precision, consistency, error):
        profile.precision_avg = (
            self.alpha * profile.precision_avg + (1 - self.alpha) * precision
        )
        profile.consistency_avg = (
            self.alpha * profile.consistency_avg + (1 - self.alpha) * consistency
        )
        profile.error_avg = (
            self.alpha * profile.error_avg + (1 - self.alpha) * error
        )
        return profile
