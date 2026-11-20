# Native TORC setup

Use [TORC](https://github.com/NatLabRockies/torc) directly (`torc` CLI and `torc-dash`) when an analysis, simulation study, or `autoresearch` loop needs managed multi-job dependencies, remote SSH workers, or Slurm execution. Simple local tasks should run directly through `pixi run` or `uv run` without starting `torc-server`.

See the official TORC documentation for [installation](https://natlabrockies.github.io/torc/latest/getting-started/installation.html), [network connectivity](https://natlabrockies.github.io/torc/latest/core/concepts/network-connectivity.html), and [remote workers](https://natlabrockies.github.io/torc/latest/specialized/remote/remote-workers.html).

## Install and verify

Keep identical TORC versions across the server and remote workers:

```console
cargo install torc --version 0.40.0 --features "server-bin,mcp-server,dash,slurm-runner"
torc --version
ssh worker 'command -v bash; command -v torc; torc --version'
```

## Server and macOS Keychain credentials

For local workflows, bind to loopback (`torc-server run --host 127.0.0.1 --port 8080 --database torc.db`). For remote workers, bind to a private interface with authentication (`--require-auth --enforce-access-control --disable-admin-sql`) and keep `TORC_PASSWORD` in macOS Keychain rather than plaintext files:

```fish
function __with_torc_password
    set -l torc_password (security find-generic-password -a "$USER" -s waterology-torc -w 2>/dev/null)
    if test $status -ne 0; or test -z "$torc_password"
        echo "TORC credential not found in macOS Keychain" >&2
        return 1
    end
    set -lx TORC_PASSWORD "$torc_password"
    command $argv
end

function torc --wraps torc
    __with_torc_password torc $argv
end
```
