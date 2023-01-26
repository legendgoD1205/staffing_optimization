class Job:
    def __init__(
        self,
        name: str,
        gain: int,
        due_date: int,
        daily_penalty: int,
        working_days_per_qualification: dict[str, int],
    ):
        self.name: str = name
        self.gain: int = gain
        self.due_date: int = due_date
        self.daily_penalty: int = daily_penalty
        self.working_days_per_qualification: dict[
            str, int
        ] = working_days_per_qualification

    def __str__(self):
        return f"Project: {self.name} (gain: {self.gain}, due date: {self.due_date}, daily penalty: {self.daily_penalty}, working days per qualification: {self.working_days_per_qualification})"

    def __repr__(self):
        return self.__str__()
