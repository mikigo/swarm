import click
import yaml
from loguru import logger

from swarm.cli import config as config_manager
from swarm.cli import task as task_cli


@click.group()
@click.option("--server", default="http://localhost:8000", help="Swarm server URL")
@click.pass_context
def cli(ctx, server):
    ctx.ensure_object(dict)
    ctx.obj["server"] = server


@cli.group()
def server():
    """Manage Swarm server"""
    pass


@server.command("start")
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, help="Server port")
def server_start(host, port):
    from swarm.server import main as server_main
    import uvicorn
    uvicorn.run(server_main.app, host=host, port=port)


@server.command("stop")
def server_stop():
    pass


@cli.group()
def client():
    """Manage Swarm client"""
    pass


@client.command("start")
@click.option("--server", default="http://localhost:8000", help="Swarm server URL")
def client_start(server):
    from swarm.client import main as client_main
    import asyncio
    asyncio.run(client_main.main())


@cli.group()
def run():
    """Run tests"""
    pass


@run.command("start")
@click.option("--repo", required=True, help="Git repository URL")
@click.option("-b", "--branch", default="main", help="Branch name")
@click.option("-k", help="Filter by test name")
@click.option("-m", help="Filter by marker")
@click.option("--client-timeout", type=int, help="Client timeout")
@click.option("--client-reruns", type=int, help="Client reruns")
@click.option("--config", type=click.Path(exists=True), help="Task config file")
@click.argument("test_paths", nargs=-1)
def run_start(repo, branch, k, m, client_timeout, client_reruns, config, test_paths):
    server = click.get_current_context().obj["server"]
    
    task_config = {}
    if config:
        with open(config) as f:
            task_config = yaml.safe_load(f)
    else:
        task_config = {
            "name": "Test Task",
            "repo_url": repo,
            "branch": branch,
            "test_paths": list(test_paths) if test_paths else [],
        }
        
        if k or m:
            task_config["filter_args"] = {}
            if k:
                task_config["filter_args"]["k"] = k
            if m:
                task_config["filter_args"]["m"] = m
        
        if client_timeout or client_reruns:
            task_config["client_args"] = {}
            if client_timeout:
                task_config["client_args"]["timeout"] = client_timeout
            if client_reruns:
                task_config["client_args"]["reruns"] = client_reruns
    
    import httpx
    with httpx.Client() as client:
        response = client.post(f"{server}/api/tasks", json=task_config)
    
    if response.status_code == 200:
        result = response.json()
        click.echo(f"Task created: {result['id']}")
    else:
        click.echo(f"Failed to create task")


@cli.group()
def task():
    """Manage tasks"""
    pass


@task.command("list")
@click.option("--status", help="Filter by status")
def task_list(status):
    server = click.get_current_context().obj["server"]
    task_cli.list_tasks(server, status)


@task.command("info")
@click.argument("task_id")
def task_info(task_id):
    server = click.get_current_context().obj["server"]
    task_cli.get_task_info(server, task_id)


@task.command("cancel")
@click.argument("task_id")
def task_cancel(task_id):
    server = click.get_current_context().obj["server"]
    task_cli.cancel_task(server, task_id)


def main():
    cli(obj={})