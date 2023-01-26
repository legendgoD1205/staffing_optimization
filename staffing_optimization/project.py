import json
from typing import TypedDict
import logging
import gurobipy

from entities import Employee, Job


class ProblemData(TypedDict):
    horizon: int
    qualifications: list[str]
    staff: list[Employee]
    jobs: list[Job]


def get_data(size: str) -> ProblemData:
    if size == "small":
        file: str = "data/toy_instance.json"
    elif size == "medium":
        file: str = "data/medium_instance.json"
    elif size == "large":
        file: str = "data/large_instance.json"
    else:
        raise ValueError(f"Unknown size {size}")

    with open(file) as f:
        data: dict = json.load(f)

    data["staff"] = [
        Employee(
            name=employee["name"],
            qualifications=employee["qualifications"],
            vacations=employee["vacations"],
        )
        for index, employee in enumerate(data["staff"])
    ]

    data["jobs"] = [
        Job(
            name=job["name"],
            gain=job["gain"],
            due_date=job["due_date"],
            daily_penalty=job["daily_penalty"],
            working_days_per_qualification=job["working_days_per_qualification"],
        )
        for index, job in enumerate(data["jobs"])
    ]

    return data


def get_profit(project: Job, end_date: int) -> int:
    if project.due_date >= end_date:
        return project.gain
    return max(project.gain - project.daily_penalty * (end_date - project.due_date), 0)


def solve_problem(
    data: ProblemData,
) -> gurobipy.Model:
    profits_jobs: dict = {
        (job_index, day): get_profit(job, day)
        for job_index, job in enumerate(data["jobs"])
        for day in range(data["horizon"])
    }
    model: gurobipy.Model = gurobipy.Model()

    # Create variables
    # X[e, j, d] = 1 if employee e works on job j on day d
    # Y[e, j, q] = 1 if employee e is assigned to job j for qualification q
    # Z[j, d] = 1 if job j is finished on day d

    X: gurobipy.tupledict = model.addVars(
        len(data["staff"]),
        len(data["jobs"]),
        data["horizon"],
        vtype=gurobipy.GRB.BINARY,
        name="X",
    )

    Y: gurobipy.tupledict = model.addVars(
        len(data["staff"]),
        len(data["jobs"]),
        len(data["qualifications"]),
        vtype=gurobipy.GRB.BINARY,
        name="Y",
    )

    Z: gurobipy.tupledict = model.addVars(
        len(data["jobs"]),
        data["horizon"],
        vtype=gurobipy.GRB.BINARY,
        name="Z",
    )

    # Preference 2: Minimize the number of jobs staffed for the person with the most jobs
    # Minimize(max(number_of_jobs_staffed)) for all employees
    # A = model.addVar(
    #     vtype=gurobipy.GRB.INTEGER,
    #     name="A",
    #     lb=0,
    #     ub=len(data["jobs"]),
    # )

    model.update()

    model.setObjective(
        gurobipy.quicksum(
            profits_jobs[job_index, day] * Z[job_index, day]
            for job_index, _ in enumerate(data["jobs"])
            for day in range(data["horizon"])
        ),
        gurobipy.GRB.MAXIMIZE,
    )

    # TODO: Fix preferences below to have a multi-objective optimization
    # model.addConstr(
    #     A
    #     == gurobipy.max_(
    #         gurobipy.quicksum(
    #             Y[employee_index, job_index, qualification_index]
    #             for job_index, _ in enumerate(data["jobs"])
    #             for qualification_index, _ in enumerate(data["qualifications"])
    #         )
    #         for employee_index, _ in enumerate(data["staff"])
    #     ),
    #     name="A",
    # )
    #
    # model.setObjective(
    #     A,
    #     gurobipy.GRB.MINIMIZE,
    # )

    # Preference 1: Minimize the length of longest job done
    # Minimize(max(end_date - start_date)) for all jobs_done
    # model.setObjective(
    #     (
    #         gurobipy.max_(
    #             Z[job_index, day] * day  # end_date
    #             - gurobipy.min_(
    #                 day_2
    #                 if gurobipy.and_(X[employee_index, job_index, day_2] >= 0.5)
    #                 else gurobipy.GRB.INFINITY
    #                 for employee_index, _ in enumerate(data["staff"])
    #                 for day_2 in range(data["horizon"])
    #             )  # start_date
    #             for day in range(data["horizon"])
    #             for job_index, _ in enumerate(data["jobs"])
    #         ),
    #     ),
    #     gurobipy.GRB.MINIMIZE,
    # )

    # Add constraints

    # Constraint 1 : An employee can only be assigned to a project qualification if he has this qualification
    model.addConstrs(
        (
            Y[employee_index, job_index, qualification_index] == 0
            for employee_index, employee in enumerate(data["staff"])
            for job_index, _ in enumerate(data["jobs"])
            for qualification_index, qualification in enumerate(data["qualifications"])
            if qualification not in employee.qualifications
        ),
        name="Need to have qualification to work on a job",
    )

    # Constraint 2: An employee can only be assigned to one qualification for a job
    # Number of qualifications per employee per job <= 1
    model.addConstrs(
        (
            gurobipy.quicksum(
                Y[employee_index, job_index, qualification_index]
                for qualification_index, _ in enumerate(data["qualifications"])
            )
            <= 1
            for employee_index, _ in enumerate(data["staff"])
            for job_index, _ in enumerate(data["jobs"])
        ),
        name="One qualification per employee per job",
    )

    # Constraint 3 : An employee can only be assigned to one project per day
    # Number of jobs per employee per day <= 1
    model.addConstrs(
        (
            gurobipy.quicksum(
                X[employee_index, job_index, day]
                for job_index, _ in enumerate(data["jobs"])
            )
            <= 1
            for employee_index, _ in enumerate(data["staff"])
            for day in range(data["horizon"])
        ),
        name="One job per employee per day",
    )

    # Constraint 4: An employee must not work on a day of vacation
    # X[e, j, d] = 0 if d in employee e vacations
    model.addConstrs(
        (
            X[employee_index, job_index, day] == 0
            for employee_index, employee in enumerate(data["staff"])
            for job_index, _ in enumerate(data["jobs"])
            for day in employee.vacations
        ),
        name="No work on vacation",
    )

    # Constraint 4: An employee must not work on a day of vacation
    # X[e, j, d] = 0 if d in employee e vacations
    model.addConstrs(
        (
            X[employee_index, job_index, day] == 0
            for employee_index, employee in enumerate(data["staff"])
            for job_index, _ in enumerate(data["jobs"])
            for day in employee.vacations
        ),
        name="No work on vacation",
    )

    # New constraint to help?
    # Nobody can be staffed to a job once a job is finished
    # Constraint 5: A project is realized when each qualification has been staffed
    # the right number of days

    # Z[j, d] = 1 if for all days d in 0..d,
    # sum(Y[e, j, q] * X[e, j, d]) == working_days_per_qualification[q] for all q
    # TODO: The code below doesn't work, because it needs to be done only the last day of execution and not the days after
    model.addConstrs(
        (
            Z[job_index, day] == 1
            if gurobipy.and_(
                gurobipy.all_(
                    gurobipy.quicksum(
                        Y[employee_index, job_index, qualification_index]
                        * X[employee_index, job_index, day_2]
                        for employee_index, _ in enumerate(data["staff"])
                        for day_2 in range(day + 1)
                    )
                    == job.working_days_per_qualification.get(qualification, 0)
                    for qualification_index, qualification in enumerate(
                        data["qualifications"]
                    )
                ),
                gurobipy.quicksum(
                    X[employee_index, job_index, day]
                    for employee_index, _ in enumerate(data["staff"])
                )
                >= 1,
            )
            else 0
            for job_index, job in enumerate(data["jobs"])
            for day in range(data["horizon"])
        ),
        name="Project is realized when each qualification has been staffed the right "
        "number of days",
    )

    # Constraint 6: A project can only be realized once
    model.addConstrs(
        (
            gurobipy.quicksum(Z[job_index, day]
                              for day in range(data["horizon"])) == 1
            for job_index, _ in enumerate(data["jobs"])
        ),
        name="A job can only be realized once",
    )

    # if an employee is assigned to a job for a qualification, he must work for this
    # job at least one day
    # Y[e, j, q] = 1 => sum(X[e, j, d] for d in 0..horizon) >= 1
    # <=> sum(X[e, j, d] for d in 0..horizon) >= Y[e, j, q]
    model.addConstrs(
        (
            gurobipy.quicksum(
                X[employee_index, job_index, day] for day in range(data["horizon"])
            )
            >= Y[employee_index, job_index, qualification_index]
            for employee_index, _ in enumerate(data["staff"])
            for job_index, _ in enumerate(data["jobs"])
            for qualification_index, qualification in enumerate(data["qualifications"])
        ),
        name="If an employee is assigned to a job for a qualification, he must work for this job at least one day",
    )

    # You can't assign more days of work of qualification than the number of days of
    # work of the qualification sum(X[e, j, d] for d in 0..horizon) <=
    # working_days_per_qualification[q] * Y[e, j, q]
    model.addConstrs(
        (
            gurobipy.quicksum(
                X[employee_index, job_index, day]
                * Y[employee_index, job_index, qualification_index]
                for employee_index, _ in enumerate(data["staff"])
                for day in range(data["horizon"])
            )
            <= job.working_days_per_qualification.get(qualification, 0)
            for job_index, job in enumerate(data["jobs"])
            for qualification_index, qualification in enumerate(data["qualifications"])
        ),
        name="Staffed days of qualification <= number of days of work of the qualification",
    )

    # Don't assign people if job is not done
    # X[e, j, d] = 0 if Z[j, d] = 0 for all e, d
    # TODO

    # Constraint 7: The problem takes place over a given period of time
    # Already solved?

    model.optimize()

    if model.Status == gurobipy.GRB.OPTIMAL:
        print("Optimal solution found", model.ObjVal)
        for v in model.getVars():
            if v.x == 1:
                if v.varName[0] == "X":
                    print(
                        "Employee",
                        data["staff"][int(v.varName[2])].name,
                        "works on job",
                        data["jobs"][int(v.varName[4])].name,
                        "on day",
                        int(v.varName[6]),
                    )
                elif v.varName[0] == "Y":
                    print(
                        "Employee",
                        data["staff"][int(v.varName[2])].name,
                        "is assigned to job",
                        data["jobs"][int(v.varName[4])].name,
                        "for qualification",
                        data["qualifications"][int(v.varName[6])],
                    )
                elif v.varName[0] == "Z":
                    print(
                        "Job",
                        data["jobs"][int(v.varName[2])].name,
                        "is finished on day",
                        int(v.varName[4]),
                    )

        print("Objective value:", model.ObjVal)
    return model


def main() -> None:
    data: ProblemData = get_data("small")

    model: gurobipy.Model = solve_problem(data)


if __name__ == "__main__":
    main()
