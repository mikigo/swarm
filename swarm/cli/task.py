import httpx
import yaml
from rich.console import Console
from rich.table import Table

from swarm.cli import config as config_manager


console = Console()


def list_tasks(server_url: str, status: str = None):
    with httpx.Client() as client:
        url = f"{server_url}/api/tasks"
        if status:
            url += f"?status={status}"
        response = client.get(url)
    
    if response.status_code != 200:
        console.print(f"[red]Failed to fetch tasks[/red]")
        return
    
    tasks = response.json()
    cli_config = config_manager.config
    columns = cli_config.get_columns()
    widths = cli_config.get_column_widths()
    colors = cli_config.get_column_colors()
    
    table = Table(show_header=True, header_style="bold magenta")
    
    for col in columns:
        width = widths.get(col, 20)
        table.add_column(col, width=min(width, 50) if width else None)
    
    for task in tasks:
        row = []
        for col in columns:
            value = str(task.get(col, ""))
            if col == "status" and value in colors:
                value = f"[{colors[value]}]{value}[/{colors[value]}]"
            row.append(value)
        table.add_row(*row)
    
    console.print(table)


def get_task_info(server_url: str, task_id: str):
    with httpx.Client() as client:
        response = client.get(f"{server_url}/api/tasks/{task_id}")
    
    if response.status_code != 200:
        console.print(f"[red]Task not found[/red]")
        return
    
    task = response.json()
    
    console.print(f"[bold]Task: {task['name']}[/bold]")
    console.print(f"ID: {task['id']}")
    console.print(f"Status: {task['status']}")
    console.print(f"Repository: {task['repo_url']}")
    console.print(f"Branch: {task['branch']}")
    console.print(f"Created: {task['created_at']}")
    
    if task.get("started_at"):
        console.print(f"Started: {task['started_at']}")
    if task.get("finished_at"):
        console.print(f"Finished: {task['finished_at']}")


def cancel_task(server_url: str, task_id: str):
    with httpx.Client() as client:
        response = client.delete(f"{server_url}/api/tasks/{task_id}")
    
    if response.status_code == 200:
        console.print(f"[green]Task cancelled[/green]")
    else:
        console.print(f"[red]Failed to cancel task: {response.text}[/red]")


def create_task_from_config(server_url: str, config_file: str):
    with open(config_file) as f:
        config = yaml.safe_load(f)
    
    with httpx.Client() as client:
        response = client.post(f"{server_url}/api/tasks", json=config)
    
    if response.status_code == 200:
        result = response.json()
        console.print(f"[green]Task created: {result['id']}[/green]")
    else:
        console.print(f"[red]Failed to create task: {response.text}[/red]")