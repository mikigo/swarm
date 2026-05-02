import click
import httpx
from loguru import logger

from swarm.client import runner


@click.group()
@click.option("--server", default="http://localhost:8000", help="Swarm server URL")
@click.pass_context
def cli(ctx, server):
    ctx.ensure_object(dict)
    ctx.obj["server"] = server


@cli.command()
@click.pass_context
def start(ctx):
    server = ctx.obj["server"]
    logger.info(f"Starting Swarm client, connecting to {server}")
    runner.start_client(server)


def main():
    cli(obj={})