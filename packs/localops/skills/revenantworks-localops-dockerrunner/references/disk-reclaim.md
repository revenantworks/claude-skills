# Disk — the dry list, prune, and getting space back on the host

**Read this file when:** `prune` runs, `audit` reports a large VHDX or low disk, or the user says
"my Docker disk keeps growing".

## Contents

1. Two numbers, not one
2. The prune list and the one owner command
3. Volumes
4. Reclaim — making the VHDX smaller
5. What needs admin

---

## 1. Two numbers, not one

`docker system df` reports what Docker uses **inside** the VM. The host sees the **VHDX file**
that holds it. A dynamic VHDX grows as images are pulled and does not shrink when they are
deleted (microsoft/WSL issue 4699, open since 2019). So a prune can free 30 GB inside and give
the host nothing back. The audit reports both, side by side, every time:

- inside: `docker system df` (images, containers, volumes, build cache; size and reclaimable);
- host: each VHDX's size and the free space on its drive.

Docker Desktop's data disk is usually `%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx`; older
installs used `%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx`. Desktop can move it (Settings →
Resources → Advanced → disk image location). When the script finds none, ask the user for the
path and pass `--vhdx PATH`. Distro VHDX files are found through the WSL registry entries.

## 2. The prune list and the one owner command

`python scripts/docker_preflight.py --mode prune-list` prints:

- stopped containers (exited or created), with name, image and status;
- dangling images (untagged layers), with size;
- the build cache's reclaimable size;
- dangling volumes — **listed, never included** unless named (section 3);
- `owner_command`: one line that removes **exactly the listed IDs**
  (`docker rm <ids>; docker rmi <ids>; docker builder prune -f`).

Show the list. The user reads it and runs the command, or says which lines to drop and gets a
new one. The skill never runs a prune itself. It never offers `docker system prune -a`,
`docker image prune -a` (removes every image with no container, including ones the user
pulled on purpose), or `--volumes`.

Removing by ID, not by filter, means the command removes what the user read — nothing that
stopped between the list and the run.

## 3. Volumes

Volumes hold data: databases, caches, models. **Never pruned by default.** A volume enters the
command only when the user names it, and only when it is in the dangling list (no container
uses it): `--volumes name1,name2`. A named volume that is in use or unknown is refused and
reported. `docker volume prune` and `docker compose down -v` are never offered.

## 4. Reclaim — making the VHDX smaller

After a prune, report the VHDX size again, then hand the user one route. The skill runs none
of them.

| Route | Command (the user runs it) | Needs | Notes |
|---|---|---|---|
| Sparse VHD | `wsl --manage <distro> --set-sparse true` | WSL; the distro stopped | Space returns over time. Works per distro; whether it applies to Docker Desktop's separate data disk is **unverified**, so prefer the next two for that file |
| Optimize-VHD | `wsl --shutdown; Optimize-VHD -Path "<vhdx>" -Mode Full` | An elevated PowerShell and the Hyper-V module | Compacts in place. Docker Desktop must be quit first |
| diskpart | `select vdisk file="<vhdx>"`, `attach vdisk readonly`, `compact vdisk`, `detach vdisk` | An elevated `diskpart` | Works without the Hyper-V module |

Default proposal: `sparseVhd=true` in `.wslconfig` for **new** disks (`references/wslconfig.md`),
plus Optimize-VHD for the existing Docker data disk when the Hyper-V module is present.

## 5. What needs admin

The `docker` CLI and `docker compose` need no admin once Docker Desktop runs (the user is in
`docker-users`). Installing or updating Desktop, `Optimize-VHD` and `diskpart` need admin. The
skill **never elevates itself**: it hands the command, says it needs an elevated shell, and stops.
Whether membership in Hyper-V Administrators alone is enough for Optimize-VHD is unverified;
treat it as admin.
