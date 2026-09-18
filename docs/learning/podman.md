# Learning: Podman

## What is Podman
A tool to run containers. Like Docker, but no background daemon.

## What is a container
One running app, isolated from your computer. Has its own files, but shares your OS kernel.

## What is an image
A frozen recipe/template. Pull an image, then create containers from it. One image → many containers.

## Container vs Image
- Image = blueprint (static)
- Container = running instance of that blueprint (live)

## Pod
A group of containers that share network + storage, act like one unit. Used for multi-container apps that must be tightly linked. Not needed for simple local dev.

## Volume
Disk storage that lives outside the container. Keeps your data safe even if container is deleted/recreated. Postgres data should always use a volume.

## Network
Lets containers talk to each other by name instead of IP. Podman creates a default network automatically.

## Secrets
Safe storage for passwords/API keys, instead of writing them in plain text. Alternative to `.env` file. Optional for local dev.

## Kubernetes (tab in Podman Desktop)
For running many containers across many servers (production scale). Not needed for local single-machine dev.

## Extensions
Plugins for the Podman Desktop app itself (UI features). Not related to your project containers.

## Multiple containers from same image
Yes, possible. Example: 2 Postgres containers, different names, different ports (5432, 5433), different volumes. Useful for testing, not needed normally.

## My setup notes (from personal_notes.md)

- Pulled `pgvector/pgvector:pg16` image — Postgres with pgvector pre-installed.
- Created named volume: `podman volume create cortex_pg_data` — keeps DB data safe if container is killed/upgraded.
- **Why volume matters:** without it, killing the container wipes the DB. Non-negotiable even in local dev — don't want to re-upload test documents every restart.

## What is a .yml file (docker-compose)

YAML = plain-text format for config, easy to read (no curly braces/commas like JSON).

**Problem it solves:** typing a long `podman run` command with 6+ flags is easy to mess up, not shareable, and doesn't scale (more containers = more commands).

**Fix:** write desired state once in a file. A tool reads it and creates everything correctly, every time. This is "declarative config over imperative commands" — same idea behind Kubernetes, Terraform, CI/CD.

## How to run docker-compose.yml

Podman needs `podman-compose` (separate install):

```bash
pip install podman-compose
```

From the folder with `docker-compose.yml`:

```bash
podman-compose up -d      # create + start everything, in background
podman-compose down       # stop + remove containers (data stays safe in volume)
podman-compose logs -f postgres   # view logs
```

When Redis joins later (Phase 5), just add a second `service:` block to the same file — one `podman-compose up -d` starts both, networked together automatically.

## Common commands

```bash
podman ps                # list running containers
podman ps -a              # list all containers (running + stopped)
podman images              # list downloaded images
podman start <name>         # start a container
podman stop <name>           # stop a container
podman logs <name>            # view container logs
podman exec -it <name> bash    # open shell inside container
```
