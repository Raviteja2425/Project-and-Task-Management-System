from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path


DATA_DIR = Path(__file__).with_name("data")
PROJECTS_FILE = DATA_DIR / "projects.txt"
EMPLOYEES_FILE = DATA_DIR / "employees.txt"
TASKS_FILE = DATA_DIR / "tasks.txt"
PRIORITIES = {"low", "medium", "high", "critical"}
TASK_STATUSES = {"not started", "in progress", "completed", "blocked"}


def read_date(prompt: str) -> date:
    while True:
        value = input(prompt).strip()
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            print("Enter a valid date in YYYY-MM-DD format.")


def choose_from(values: set[str], prompt: str) -> str:
    while True:
        value = input(prompt).strip().lower()
        if value in values:
            return value
        print("Choose one of: " + ", ".join(sorted(values)))


class Employee:
    def __init__(self, employee_id: int, name: str, role: str):
        self.employee_id = employee_id
        self.name = name
        self.role = role

    def to_dict(self) -> dict:
        return {"employee_id": self.employee_id, "name": self.name, "role": self.role}

    @classmethod
    def from_dict(cls, data: dict) -> "Employee":
        return cls(data["employee_id"], data["name"], data["role"])


class Task:
    def __init__(self, task_id: int, title: str, description: str, priority: str,
                 deadline: date, assignee_id: int | None = None,
                 status: str = "not started"):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.priority = priority
        self.deadline = deadline
        self.assignee_id = assignee_id
        self.status = status

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id, "title": self.title,
            "description": self.description, "priority": self.priority,
            "deadline": self.deadline.isoformat(),
            "assignee_id": self.assignee_id, "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(data["task_id"], data["title"], data["description"],
                   data["priority"], date.fromisoformat(data["deadline"]),
                   data.get("assignee_id"), data.get("status", "not started"))

    def is_overdue(self) -> bool:
        return self.deadline < date.today() and self.status != "completed"


class Project:
    def __init__(self, project_id: int, name: str, description: str,
                 deadline: date, team: set[int] | None = None,
                 tasks: list[Task] | None = None):
        self.project_id = project_id
        self.name = name
        self.description = description
        self.deadline = deadline
        self.team = team if team is not None else set()
        self.tasks = tasks if tasks is not None else []

    def progress(self) -> int:
        if not self.tasks:
            return 0
        completed = sum(task.status == "completed" for task in self.tasks)
        return round(100 * completed / len(self.tasks))

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id, "name": self.name,
            "description": self.description, "deadline": self.deadline.isoformat(),
            "team": sorted(self.team), "tasks": [task.to_dict() for task in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return cls(data["project_id"], data["name"], data["description"],
                   date.fromisoformat(data["deadline"]), set(data.get("team", [])),
                   [Task.from_dict(item) for item in data.get("tasks", [])])


class ProjectManager:
    def __init__(self):
        self.projects: dict[int, Project] = {}
        self.employees: dict[int, Employee] = {}
        self.next_project_id = 1
        self.next_employee_id = 1
        self.next_task_id = 1
        self.load()

    def save(self) -> None:
        try:
            DATA_DIR.mkdir(exist_ok=True)
            PROJECTS_FILE.write_text(
                json.dumps([project.to_dict() for project in self.projects.values()], indent=2),
                encoding="utf-8",
            )
            EMPLOYEES_FILE.write_text(
                json.dumps([employee.to_dict() for employee in self.employees.values()], indent=2),
                encoding="utf-8",
            )
            TASKS_FILE.write_text(
                json.dumps([task.to_dict() for project in self.projects.values()
                            for task in project.tasks], indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            print(f"Could not save data: {error}")

    def load(self) -> None:
        try:
            DATA_DIR.mkdir(exist_ok=True)
            project_data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8-sig")) if PROJECTS_FILE.exists() else []
            employee_data = json.loads(EMPLOYEES_FILE.read_text(encoding="utf-8-sig")) if EMPLOYEES_FILE.exists() else []
            task_data = json.loads(TASKS_FILE.read_text(encoding="utf-8-sig")) if TASKS_FILE.exists() else []
            self.employees = {
                item["employee_id"]: Employee.from_dict(item)
                for item in employee_data
            }
            self.projects = {
                item["project_id"]: Project.from_dict(item)
                for item in project_data
            }
            tasks_by_id = {item["task_id"]: Task.from_dict(item) for item in task_data}
            for project in self.projects.values():
                project.tasks = [tasks_by_id[task.task_id] for task in project.tasks
                                 if task.task_id in tasks_by_id]
            self.next_project_id = max(self.projects, default=0) + 1
            self.next_employee_id = max(self.employees, default=0) + 1
            self.next_task_id = max(tasks_by_id, default=0) + 1
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            print(f"Saved data could not be loaded ({error}). Starting with empty data.")

    def add_employee(self, name: str, role: str) -> Employee:
        employee = Employee(self.next_employee_id, name, role)
        self.employees[employee.employee_id] = employee
        self.next_employee_id += 1
        self.save()
        return employee

    def add_project(self, name: str, description: str, deadline: date) -> Project:
        project = Project(self.next_project_id, name, description, deadline)
        self.projects[project.project_id] = project
        self.next_project_id += 1
        self.save()
        return project

    def add_task(self, project: Project, title: str, description: str,
                 priority: str, deadline: date) -> Task:
        task = Task(self.next_task_id, title, description, priority, deadline)
        project.tasks.append(task)
        self.next_task_id += 1
        self.save()
        return task

    def overdue_tasks(self) -> list[tuple[Project, Task]]:
        return [(project, task) for project in self.projects.values()
                for task in project.tasks if task.is_overdue()]


def print_employees(manager: ProjectManager) -> None:
    if not manager.employees:
        print("No employees have been added.")
        return
    for employee in manager.employees.values():
        print(f"  {employee.employee_id}: {employee.name} ({employee.role})")


def print_projects(manager: ProjectManager) -> None:
    if not manager.projects:
        print("No projects have been added.")
        return
    for project in manager.projects.values():
        print(f"  {project.project_id}: {project.name} | due {project.deadline} "
              f"| progress {project.progress()}% | team {len(project.team)} "
              f"| tasks {len(project.tasks)}")


def select_project(manager: ProjectManager) -> Project | None:
    print_projects(manager)
    if not manager.projects:
        return None
    try:
        project_id = int(input("Project ID: "))
        if project_id not in manager.projects:
            raise KeyError
        return manager.projects[project_id]
    except ValueError:
        print("Project ID must be a number.")
    except KeyError:
        print("Project not found.")
    return None


def add_employee_flow(manager: ProjectManager) -> None:
    name = input("Employee name: ").strip()
    role = input("Role: ").strip()
    if not name or not role:
        print("Name and role cannot be blank.")
        return
    employee = manager.add_employee(name, role)
    print(f"Added employee #{employee.employee_id}.")


def add_project_flow(manager: ProjectManager) -> None:
    name = input("Project name: ").strip()
    description = input("Description: ").strip()
    if not name:
        print("Project name cannot be blank.")
        return
    deadline = read_date("Project deadline (YYYY-MM-DD): ")
    project = manager.add_project(name, description, deadline)
    print(f"Created project #{project.project_id}.")


def allocate_team_flow(manager: ProjectManager) -> None:
    project = select_project(manager)
    if project is None:
        return
    print_employees(manager)
    if not manager.employees:
        return
    try:
        employee_id = int(input("Employee ID to add to team: "))
        if employee_id not in manager.employees:
            raise KeyError
        project.team.add(employee_id)
        manager.save()
        print(f"Added {manager.employees[employee_id].name} to {project.name}.")
    except ValueError:
        print("Employee ID must be a number.")
    except KeyError:
        print("Employee not found.")


def add_task_flow(manager: ProjectManager) -> None:
    project = select_project(manager)
    if project is None:
        return
    title = input("Task title: ").strip()
    description = input("Task description: ").strip()
    if not title:
        print("Task title cannot be blank.")
        return
    priority = choose_from(PRIORITIES, "Priority (low/medium/high/critical): ")
    deadline = read_date("Task deadline (YYYY-MM-DD): ")
    task = manager.add_task(project, title, description, priority, deadline)
    print(f"Added task #{task.task_id} to {project.name}.")


def assign_task_flow(manager: ProjectManager) -> None:
    project = select_project(manager)
    if project is None or not project.tasks:
        if project is not None:
            print("This project has no tasks.")
        return
    for task in project.tasks:
        print(f"  Task {task.task_id}: {task.title} (priority: {task.priority})")
    try:
        task_id = int(input("Task ID: "))
        task = next(task for task in project.tasks if task.task_id == task_id)
        print_employees(manager)
        employee_id = int(input("Employee ID to assign: "))
        if employee_id not in project.team:
            print("That employee is not on this project's team. Allocate them first.")
            return
        task.assignee_id = employee_id
        manager.save()
        print(f"Assigned {task.title} to {manager.employees[employee_id].name}.")
    except ValueError:
        print("IDs must be numbers.")
    except StopIteration:
        print("Task not found in this project.")


def update_status_flow(manager: ProjectManager) -> None:
    project = select_project(manager)
    if project is None or not project.tasks:
        if project is not None:
            print("This project has no tasks.")
        return
    for task in project.tasks:
        print(f"  Task {task.task_id}: {task.title} [{task.status}]")
    try:
        task_id = int(input("Task ID: "))
        task = next(task for task in project.tasks if task.task_id == task_id)
        task.status = choose_from(TASK_STATUSES,
                                  "Status (not started/in progress/completed/blocked): ")
        manager.save()
        print("Task status updated.")
    except ValueError:
        print("Task ID must be a number.")
    except StopIteration:
        print("Task not found in this project.")


def show_project_details(manager: ProjectManager) -> None:
    project = select_project(manager)
    if project is None:
        return
    team_names = [manager.employees[eid].name for eid in project.team
                  if eid in manager.employees]
    print(f"\n{project.name} — {project.description or 'No description'}")
    print(f"Deadline: {project.deadline} | Progress: {project.progress()}%")
    print("Team: " + (", ".join(team_names) if team_names else "No members"))
    if not project.tasks:
        print("Tasks: none")
        return
    print("Tasks:")
    for task in project.tasks:
        assignee = manager.employees.get(task.assignee_id)
        assignee_name = assignee.name if assignee else "Unassigned"
        overdue = " | OVERDUE" if task.is_overdue() else ""
        print(f"  #{task.task_id} {task.title} | {task.priority} | {task.status} "
              f"| due {task.deadline} | {assignee_name}{overdue}")


def show_overdue(manager: ProjectManager) -> None:
    tasks = manager.overdue_tasks()
    if not tasks:
        print("There are no overdue tasks.")
        return
    print("Overdue tasks:")
    for project, task in tasks:
        print(f"  {project.name} / {task.title} — due {task.deadline} ({task.status})")


def main() -> None:
    manager = ProjectManager()
    actions = {
        "1": ("Add employee", lambda: add_employee_flow(manager)),
        "2": ("Create project", lambda: add_project_flow(manager)),
        "3": ("Allocate employee to project team", lambda: allocate_team_flow(manager)),
        "4": ("Create task", lambda: add_task_flow(manager)),
        "5": ("Assign task to team member", lambda: assign_task_flow(manager)),
        "6": ("Update task status", lambda: update_status_flow(manager)),
        "7": ("View project details and progress", lambda: show_project_details(manager)),
        "8": ("List overdue tasks", lambda: show_overdue(manager)),
        "9": ("List projects", lambda: print_projects(manager)),
        "10": ("List employees", lambda: print_employees(manager)),
    }

    print("Project and Task Management System")
    while True:
        print("\n" + "\n".join(f"{key}. {label}" for key, (label, _) in actions.items()))
        print("0. Save and exit")
        choice = input("Select an option: ").strip()
        if choice == "0":
            manager.save()
            print("Data saved. Goodbye!")
            break
        action = actions.get(choice)
        if action is None:
            print("Invalid option. Enter a number from the menu.")
            continue
        try:
            action[1]()
        except (OSError, EOFError) as error:
            print(f"Operation could not be completed: {error}")


if __name__ == "__main__":
    main()
