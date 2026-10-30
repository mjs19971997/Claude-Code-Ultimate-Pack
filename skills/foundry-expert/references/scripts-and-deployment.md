# Foundry Scripts, Keystores and Deployment

## 1. Script anatomy

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {Script} from "forge-std/Script.sol";
import {Vault} from "../src/Vault.sol";

contract DeployVault is Script {
    function run() external returns (Vault vault) {
        vm.startBroadcast(); // signer is supplied by the CLI (--account, --ledger, ...)
        vault = new Vault();
        vm.stopBroadcast();
        require(address(vault).code.length > 0, "deploy failed");
    }
}
```

- Everything between `vm.startBroadcast()` and `vm.stopBroadcast()` that creates a transaction is recorded and, with `--broadcast`, sent. Code outside runs only in simulation.
- `vm.broadcast()` wraps only the next call. `vm.startBroadcast(address)` selects an unlocked or provided signer; the no-argument form uses the signer chosen on the command line (`--account`, `--ledger`, `--trezor`, `--sender`).
- Scripts run first as a simulation against the RPC endpoint; if the simulation succeeds and `--broadcast` is set, the transactions are sent in order.
- Entry point other than `run()`: `--sig "deploy(uint256)" 1000`; select a contract in a multi-contract file with `--target-contract DeployVault`.

## 2. Keystore accounts

Create an encrypted keystore entry (stored under `~/.foundry/keystores` by default) and use it by name:

```bash
cast wallet import deployer --interactive      # prompts for the private key, then a password
cast wallet list                               # names of stored accounts
cast wallet address --account deployer         # show the address (prompts for the password)
```

```bash
forge script script/DeployVault.s.sol:DeployVault \
  --rpc-url sepolia \
  --account deployer \
  --sender 0xYourDeployerAddress
```

- `--sender` must match the keystore address so that simulation and broadcast use the same account.
- Alternatives that keep keys off disk: `--ledger`, `--trezor`. Do not use `--private-key` or `--mnemonic` on shared machines or in CI logs.
- `cast wallet import <name> --private-key ...` and the `CAST_UNSAFE_PASSWORD` variable exist for automation; both put secrets where shell history and process lists can see them, so prefer the interactive prompt.
- In CI, deploying from a hosted runner needs a deliberate secret-handling design (environment protection rules, a short-lived deployer account, or a multisig proposal) rather than a long-lived key in repository secrets.

## 3. Simulate, broadcast, verify

```bash
# 1. Simulation only (no --broadcast): prints transactions, gas and addresses
forge script script/DeployVault.s.sol --rpc-url sepolia --account deployer --sender 0xYourDeployerAddress

# 2. Broadcast and verify
forge script script/DeployVault.s.sol --rpc-url sepolia --account deployer --sender 0xYourDeployerAddress --broadcast --verify

# 3. Retry a broadcast that was interrupted, or verification that failed
forge script script/DeployVault.s.sol --rpc-url sepolia --account deployer --sender 0xYourDeployerAddress --broadcast --verify --resume
```

- `--verify` requires `--broadcast` and an explorer key: set it in `foundry.toml` (`[etherscan]`) or pass `--etherscan-api-key` (also read from the `ETHERSCAN_API_KEY` environment variable).
- Other flags: `--slow` (wait for each transaction before sending the next), `--legacy` (pre-EIP-1559 chains), `--with-gas-price`, `--priority-gas-price`, `--gas-estimate-multiplier` (default 130), `--skip-simulation`, `--non-interactive`, `--chain <name-or-id>`.
- Run artifacts are written to `broadcast/<ScriptName>/<chainId>/run-latest.json` (plus a timestamped copy); simulations without `--broadcast` are written under `broadcast/dry-run/`.
- Verify an existing deployment: `forge verify-contract <address> src/Vault.sol:Vault --chain sepolia --watch` (add `--constructor-args $(cast abi-encode "constructor(uint256)" 100)` when the constructor takes arguments). Select another verifier with `--verifier` (for example `blockscout` or `sourcify`) and, for self-hosted explorers, `--verifier-url`; run `forge verify-contract --help` for the values the installed version supports.

## 4. Configuration for scripts

```toml
[rpc_endpoints]
sepolia = "${SEPOLIA_RPC_URL}"
mainnet = "${MAINNET_RPC_URL}"

[etherscan]
sepolia = { key = "${ETHERSCAN_API_KEY}" }
mainnet = { key = "${ETHERSCAN_API_KEY}" }

fs_permissions = [{ access = "read", path = "./script/config" }]
```

- Reference variables with `${NAME}` so secrets stay in the environment (or the shell's secret manager), not in the file.
- Read per-chain parameters (token addresses, admin multisig) from `script/config/<chainId>.json` with `vm.readFile` and `stdJson`, and review that file in pull requests.

## 5. Deployment safety

- Set the admin or owner to a multisig address from config in the constructor or `initialize`, not to the deployer, or transfer ownership in the same script and assert it afterwards.
- Add `require`/`assertEq` checks at the end of the script (owner, parameters, code length) so a bad deployment fails before it is considered done.
- Simulate against a fork of the target chain first (`anvil --fork-url "$SEPOLIA_RPC_URL"`, then `--rpc-url http://127.0.0.1:8545`), confirm gas and addresses, then run the real broadcast.
- Keep deployments deterministic where useful: `new Vault{salt: SALT}()` inside a broadcast uses the CREATE2 deployer; the resulting address can be predicted with `vm.computeCreate2Address`.
- After deployment, record addresses and the commit hash in a reviewed file; do not rely on `broadcast/` alone.

## 6. cast

```bash
cast call 0xToken "balanceOf(address)(uint256)" 0xHolder --rpc-url mainnet
cast send 0xVault "deposit()" --value 0.1ether --rpc-url sepolia --account deployer
cast abi-encode "constructor(address,uint256)" 0xAdmin 100
cast sig "transfer(address,uint256)"                 # 4-byte selector
cast 4byte 0xa9059cbb                                # reverse lookup
cast storage 0xVault 0 --rpc-url mainnet             # read a storage slot
cast block-number --rpc-url mainnet
cast to-wei 1 ether
cast wallet sign --account deployer "message"
```

- Reads (`call`, `storage`, `balance`, `logs`) need only `--rpc-url`; writes (`send`) need a signer (`--account`, `--ledger`, ...).
- `cast run <txhash>` replays a mined transaction locally with a trace; `cast tx`, `cast receipt` and `cast logs` inspect chain data.

## 7. anvil

```bash
anvil                                          # local chain on 127.0.0.1:8545, 10 funded dev accounts
anvil --fork-url "$MAINNET_RPC_URL" --fork-block-number 21000000
anvil --chain-id 31337 --block-time 2          # interval mining
```

- The default accounts and keys printed by `anvil` are public development keys; never reuse them on a live network.
- Cheat RPC methods (`anvil_setBalance`, `anvil_impersonateAccount`, `evm_increaseTime`, `evm_mine`) are available through `cast rpc`.
- Bind to `127.0.0.1` (the default); exposing anvil with `--host 0.0.0.0` publishes unlocked funded accounts.

## 8. chisel

`chisel` starts a Solidity REPL: type expressions and statements, use `!help` for commands, `!source` to see generated code, `!save` and `!load` to keep and restore sessions, and `!export` to turn a session into a script. Use it to check encoding, rounding and unit conversions before writing a test. Use `chisel --fork-url <rpc>` to evaluate against live state.
