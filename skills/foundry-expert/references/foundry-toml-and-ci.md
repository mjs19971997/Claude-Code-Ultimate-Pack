# foundry.toml, Profiles and CI

## 1. Profiles

`foundry.toml` is organized in profiles. `[profile.default]` is used unless `FOUNDRY_PROFILE` selects another; other profiles inherit from `default` and override only what they set. Any key can also be overridden by a `FOUNDRY_<KEY>` environment variable (for example `FOUNDRY_FUZZ_RUNS`).

```toml
[profile.default]
src = "src"
test = "test"
script = "script"
out = "out"
libs = ["lib"]
solc = "0.8.38"
optimizer = true
optimizer_runs = 200
bytecode_hash = "none"
fs_permissions = [{ access = "read", path = "./script/config" }]

[profile.default.fuzz]
runs = 256

[profile.default.invariant]
runs = 256
depth = 128
fail_on_revert = false

[profile.ci]
verbosity = 3

[profile.ci.fuzz]
runs = 5000

[profile.ci.invariant]
runs = 512
depth = 500
fail_on_revert = true

[profile.production]
via_ir = true
optimizer_runs = 1_000_000

[fmt]
line_length = 120

[rpc_endpoints]
mainnet = "${MAINNET_RPC_URL}"
sepolia = "${SEPOLIA_RPC_URL}"

[etherscan]
mainnet = { key = "${ETHERSCAN_API_KEY}" }
sepolia = { key = "${ETHERSCAN_API_KEY}" }
```

Select a profile with `FOUNDRY_PROFILE=ci forge test`. A profile used to produce deployed bytecode (`production` above) must be used for both the broadcast and the verification step so the optimizer settings match.

## 2. Frequently used keys

| Key | Purpose |
|---|---|
| `src`, `test`, `script`, `out`, `libs`, `cache_path` | Project paths |
| `solc` (version or path), `auto_detect_solc`, `evm_version` | Compiler selection; pin `solc` for reproducible builds |
| `optimizer`, `optimizer_runs`, `via_ir`, `bytecode_hash`, `cbor_metadata` | Optimizer and metadata settings that determine deployed bytecode |
| `remappings` | Import remappings (or a `remappings.txt` file) |
| `ffi`, `fs_permissions` | Gate cheatcodes that run programs or touch files |
| `gas_reports`, `gas_reports_ignore` | Contracts included in `--gas-report` |
| `isolate` | Execute top-level calls as separate transactions for realistic gas numbers |
| `deny_warnings` / `deny` | Treat compiler warnings as errors |
| `[fuzz]`, `[invariant]` | See `testing-and-cheatcodes.md` |
| `[fmt]` | Formatter options; run `forge fmt --check` in CI |
| `[lint]` | Linter options (`severity`, `exclude_lints`, `ignore`, `lint_on_build`); run with `forge lint` |
| `[rpc_endpoints]`, `[etherscan]` | Named RPC URLs and explorer keys, with `${ENV}` interpolation |
| `block_timestamp`, `sender`, `initial_balance`, `gas_limit` | Defaults for the test environment |

If a key is not listed here, check the Foundry configuration reference for the installed version before using it.

## 3. Dependencies

- `forge install foundry-rs/forge-std` adds a git submodule under `lib/`; pin a tag with `forge install foundry-rs/forge-std@v1.17.0` and commit the submodule change.
- `forge soldeer init`, `forge soldeer install <package>~<version>`, `forge soldeer update` and `forge soldeer push` manage packages with Foundry's built-in Soldeer client; the dependency list lives in `foundry.toml` (a `[dependencies]` table) and a lock file.
- `forge remappings` prints inferred remappings; put overrides in `remappings.txt` or the `remappings` key.
- Clone with `git clone --recurse-submodules` (or `git submodule update --init --recursive`) when using submodule dependencies; the CI checkout must do the same.

## 4. Build, gas and coverage commands

```bash
forge build --sizes                 # contract sizes against the 24 KiB limit
forge test --gas-report             # per-function gas table
forge snapshot                      # write .gas-snapshot
forge snapshot --check              # fail when gas changed
forge coverage --report lcov        # lcov.info for coverage tooling
forge inspect Vault storageLayout   # storage slots
forge fmt --check
forge lint
```

## 5. GitHub Actions workflow

No `${{ ... }}` expression is placed inside a `run:` script; secrets reach tests only through `env:`, and the fork job is limited to trusted events.

```yaml
name: CI

permissions: {}

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    env:
      FOUNDRY_PROFILE: ci
    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false
          submodules: recursive

      - name: Install Foundry
        uses: foundry-rs/foundry-toolchain@v1
        with:
          version: v1.8.7

      - name: Format check
        run: forge fmt --check

      - name: Build
        run: forge build --sizes

      - name: Test
        run: forge test -vvv

      - name: Gas snapshot check
        run: forge snapshot --check

  fork-tests:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: read
    env:
      FOUNDRY_PROFILE: ci
      MAINNET_RPC_URL: ${{ secrets.MAINNET_RPC_URL }}
    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false
          submodules: recursive

      - name: Install Foundry
        uses: foundry-rs/foundry-toolchain@v1
        with:
          version: v1.8.7

      - name: Fork tests
        run: forge test --match-path "test/fork/*" -vvv
```

- `forge snapshot --check` needs a committed `.gas-snapshot` file; create it once with `forge snapshot`.
- Pull requests from forks do not receive repository secrets; keep fork tests on `push` to protected branches (as above) or behind a manually approved environment.
- Pin third-party actions to a full commit SHA if the repository policy requires it; the version tags above follow the official toolchain README.
- Deployment from CI is a separate, protected workflow; see `scripts-and-deployment.md` for the signer options.
