# TORC execution

Waterology 0.3.1 requires TORC 0.40.0 or newer for managed execution. TORC owns workflow scheduling,
workers, retries, resource accounting, and its server. Waterology supplies the committed research
command, records the TORC identifiers, collects declared results, and seals the run archive.

The official TORC documentation remains the authority for
[installation](https://natlabrockies.github.io/torc/latest/getting-started/installation.html),
[network connectivity](https://natlabrockies.github.io/torc/latest/core/concepts/network-connectivity.html),
and [remote workers](https://natlabrockies.github.io/torc/latest/specialized/remote/remote-workers.html).

## Choose the layout

TORC uses one server and one or more runners.

| Layout | Server bind | Waterology profile URL |
| --- | --- | --- |
| One machine | `127.0.0.1` | `http://localhost:8080/torc-service/v1` |
| Private remote workers | A private address reachable by every worker | The same routable private address |
| Shared network or HPC | Routable address with authentication | The authenticated server address |

Do not give a remote or Slurm profile a localhost URL. The worker process would contact itself
instead of the TORC server.

## Install TORC

Install the same version on the server and every remote worker. Precompiled release archives are the
shortest route. A source installation can provide every binary:

```console
cargo install torc --version 0.40.0 --features "server-bin,mcp-server,dash,slurm-runner"
```

The server host needs `torc` and `torc-server`. Remote hosts need `torc`, `bash`, and key based SSH.
All three commands must work in a noninteractive session:

```console
torc --version
torc-server --help
ssh worker 'command -v bash; command -v torc; torc --version'
```

If `torc` works in an interactive terminal but not through SSH, put its directory on the SSH
session's PATH. Do not skip TORC's version check to conceal a mixed installation.

### Authenticated remote workers

TORC 0.40 remote workers read their API username and password from their own process environment.
The client that starts `torc remote run` does not forward its password over SSH. Give workers a
separate non-admin credential and expose it only to the remote `torc` process. One POSIX option is a
wrapper around the versioned executable:

```sh
#!/bin/sh
credential_file="$HOME/.config/torc/worker-password"
IFS= read -r TORC_PASSWORD < "$credential_file"
export TORC_PASSWORD
export TORC_USERNAME="waterology-worker-$(hostname -s)"
exec "$HOME/.local/libexec/torc-0.40.0" "$@"
```

Store each machine's distinct password file with mode `0600` and the wrapper at the `torc` location
on the noninteractive SSH PATH. Keep the real binary in the versioned `libexec` path. Send only the
bcrypt hash to the server. Do not copy an administrator credential or reusable plaintext worker
credential between machines.

Keep TORC access control enabled. Create one access group for the worker identities, then record its
numeric ID in each remote Waterology profile:

```console
torc access-groups create waterology-workers \
  --description "Authenticated workers for Waterology compute profiles"
torc access-groups add-user <group-id> <worker-username>
```

Waterology grants that group access after creating each remote workflow and before starting its
worker. This lets a non-admin worker claim the job without gaining access to unrelated workflows.

## Start the server

For local execution only, bind to loopback:

```console
torc-server run --host 127.0.0.1 --port 8080 --database torc.db
```

For remote workers, bind to a stable private address that every worker can reach. The user service
keeps the server running across terminal sessions:

```console
torc-server service install --user \
  --host <private-server-address> \
  --port 8080 \
  --threads 4 \
  --database <durable-database-path> \
  --completion-check-interval-secs 5 \
  --disable-admin-sql
torc-server service start --user
torc-server service status --user
```

Binding a control API beyond loopback expands who can submit commands. Prefer a private interface
and require authentication for a persistent remote server:

```console
torc-htpasswd add --file <auth-file> <username>
torc-server service install --user \
  --host <private-server-address> \
  --port 8080 \
  --database <durable-database-path> \
  --auth-file <auth-file> \
  --require-auth \
  --enforce-access-control \
  --admin-user <username> \
  --disable-admin-sql
```

Supply `TORC_PASSWORD` to the Waterology process; do not store it in either Waterology config file.

### macOS Keychain

On a personal Mac, Keychain can hold the client password while the TORC auth file contains only its
bcrypt hash. The first command prompts twice for the new password:

```console
security add-generic-password \
  -a "$USER" \
  -s waterology-torc \
  -l "Waterology TORC server" \
  -U -w
security find-generic-password -a "$USER" -s waterology-torc -w | \
  htpasswd -ciB -C 12 <auth-file> "$USER"
chmod 600 <auth-file>
```

Use a fish wrapper to expose the credential only to each TORC or Waterology command:

```fish
function __waterology_with_torc_password
    set -l torc_password (security find-generic-password \
        -a "$USER" \
        -s waterology-torc \
        -w 2>/dev/null)
    if test $status -ne 0; or test -z "$torc_password"
        echo "Waterology TORC credential not found in macOS Keychain" >&2
        return 1
    end
    set -lx TORC_PASSWORD "$torc_password"
    command $argv
end

function torc --wraps torc
    __waterology_with_torc_password torc $argv
end

function waterology --wraps waterology
    __waterology_with_torc_password waterology $argv
end
```

Place that block in `$HOME/.config/fish/conf.d/torc.fish`. The wrapper uses a function-local exported
variable, so the credential reaches the requested process but does not remain in the interactive
shell environment. Other shells can retrieve the same Keychain item and export `TORC_PASSWORD` only
for the command that needs it.

Test the server before adding Waterology:

```console
TORC_API_URL=http://<private-server-address>:8080/torc-service/v1 torc ping
```

Then test from every remote worker:

```console
ssh worker 'torc --url http://<private-server-address>:8080/torc-service/v1 ping'
```

## Configure Waterology

Create `$HOME/.config/waterology/config.toml` on the machine that launches Waterology:

```toml
trusted_profiles = []

[profiles.local]
provider = "torc"
mode = "local"
api_url = "http://localhost:8080/torc-service/v1"
target_shell = "posix"

[profiles.worker]
provider = "torc"
mode = "remote"
api_url = "http://<private-server-address>:8080/torc-service/v1"
ssh_alias = "worker"
access_group_id = 2
target_shell = "posix"
```

Use the routable server URL for both profiles when the server binds only to that private interface.
Add one remote profile for each SSH alias. Use the numeric ID returned by `torc access-groups
create`, not the group's name. See [Configuration](configuration.md) for Slurm fields and the
complete separation between project and machine settings.

## Verify Waterology

Run the checks in this order:

```console
waterology compute profile list
waterology doctor --torc-profile local
waterology doctor --torc-profile worker
```

The doctor checks the installed TORC version and server API. It does not prove that a remote host has
the correct binary or can reach the server, so keep the SSH checks from the installation section in
machine setup records.

Start the first remote run with explicit confirmation:

```console
waterology run start <experiment-id> --profile worker --confirm-remote
waterology run watch <run-id>
```

Remote workers need the experiment worktree at the same path because Waterology does not copy the
repository over SSH.

## Upgrade

Upgrade the server and every worker together. Stop active workflows first, replace the binaries,
restart the service, and verify every version before submitting new work:

```console
torc --version
ssh worker 'torc --version'
torc-server service stop --user
torc-server service start --user
waterology doctor --torc-profile worker
```

Use the official release digest when installing archives. `torc self update` applies only to
standalone installer installations; use the matching update method for Cargo, Docker, or a managed
site installation.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `torc command was not found` | Run `command -v torc` in the same noninteractive SSH session TORC uses. |
| Version mismatch | Install one TORC version on the server and every worker. |
| Connection refused | Confirm the service is running and bound to the profile address, not only loopback. |
| Worker starts then exits with 401 | Confirm its wrapper sets the matching username and password, then confirm the workflow was shared with its access group. |
| Jobs remain ready | Compare requested CPUs, memory, and GPUs with the worker resources. |
| Waterology reports `unknown` | Restore TORC API access, then inspect the recorded workflow ID. |
| Outputs are missing | Confirm the same experiment worktree path exists on the worker. |
