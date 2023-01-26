class Employee:
    def __init__(self, name: str, qualifications: list[str], vacations: list[int]):
        self.name = name
        self.qualifications = qualifications
        self.vacations = vacations

    def __str__(self):
        return f"Employee: {self.name} (qualifications: {self.qualifications}, vacations: {self.vacations})"

    def __repr__(self):
        return self.__str__()
