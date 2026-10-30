---
name: dao-expert
description: >-
  Designs and builds DAO governance with OpenZeppelin Governor 5.x: ERC20Votes tokens and delegation, GovernorSettings, GovernorCountingSimple, GovernorVotesQuorumFraction, GovernorTimelockControl with TimelockController, treasury ownership, Snapshot off-chain voting, Safe multisig and optimistic execution (oSnap), and governance attack analysis. Use when writing or reviewing Governor, timelock or voting-token contracts, choosing quorum and delay parameters, wiring roles, running proposal lifecycles in Foundry tests, or planning on-chain vs off-chain voting and DAO treasury controls. Not for general contract security review (use smart-contract-security-expert), DeFi protocol design (use defi-expert), or token or NFT standards (use solidity-expert or nft-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# DAO Expert

This skill covers the technical design of DAO governance: token-weighted voting with OpenZeppelin Governor and a timelock, treasury control, off-chain voting with Snapshot and how its results are executed, and the attacks that governance systems face. Contract code targets OpenZeppelin Contracts 5.x. Legal structure and tokenomics are covered only as design inputs that affect the contracts.

> Verified against Solidity 0.8.38, OpenZeppelin Contracts 5.6.1 (npm `latest`) and 5.7.0 (GitHub latest release, npm `dev` tag), forge-std (October 2026 checkout), `@snapshot-labs/snapshot.js` 0.18.0 and viem 2.x (2026-10). All Solidity examples compile with solc 0.8.38 against both OpenZeppelin versions.

## Contents
1. [Scope](#1-scope)
2. [Core Expertise](#2-core-expertise)
3. [Workflow](#3-workflow)
4. [Decision Rules](#4-decision-rules)
5. [Coding Standards](#5-coding-standards)
6. [Project Structure](#6-project-structure)
7. [Design Patterns](#7-design-patterns)
8. [Best Practices](#8-best-practices)
9. [Performance](#9-performance)
10. [Security](#10-security)
11. [Testing](#11-testing)
12. [Review Checklist](#12-review-checklist)
13. [Production Notes](#13-production-notes)
14. [Examples](#14-examples)
15. [Common Mistakes](#15-common-mistakes)
16. [References](#16-references)

## 1. Scope

- Covered: OpenZeppelin Governor modules and required overrides, `ERC20Votes` and the ERC-6372 clock, `TimelockController` roles, treasury ownership, parameter selection, Snapshot spaces and signed votes, execution of off-chain results, governance attacks, proposal review.
- Not covered: reviewing arbitrary contracts for vulnerabilities (smart-contract-security-expert); AMM, lending and staking design (defi-expert); NFT standards (nft-expert); Foundry and Hardhat configuration (foundry-expert, hardhat-expert).

## 2. Core Expertise

**Governor composition (OZ 5.x)**

| Concern | Module | Notes |
|---|---|---|
| Core | `Governor` | `propose`, `castVote`, `queue`, `execute`, `cancel`, `state` |
| Delay, period, threshold | `GovernorSettings` | Constructor `(uint48, uint32, uint256)`; changeable by governance |
| Counting | `GovernorCountingSimple` | Against, For, Abstain |
| Voting power and clock | `GovernorVotes` | Reads an ERC-5805 token; clock follows the token (ERC-6372) |
| Quorum | `GovernorVotesQuorumFraction` | Fraction of past total supply |
| Timelock | `GovernorTimelockControl` | Queue and execute through `TimelockController`; the timelock is the executor |
| Optional | `GovernorPreventLateQuorum`, `GovernorProposalGuardian`, `GovernorStorage`, `GovernorSuperQuorum`, `GovernorCountingFractional`, `GovernorCountingOverridable` | Full menu in [references/governor-setup.md](references/governor-setup.md) |

Proposal states: Pending, Active, Canceled, Defeated, Succeeded, Queued, Expired, Executed.

**Voting token**: `ERC20Votes` (with `ERC20Permit`) keeps checkpoints; voting power exists only after `delegate`. The default clock is the block number; override `clock()` and `CLOCK_MODE()` for timestamps.

**Timelock**: `TimelockController(minDelay, proposers, executors, admin)` with roles `PROPOSER_ROLE`, `EXECUTOR_ROLE`, `CANCELLER_ROLE` and `DEFAULT_ADMIN_ROLE`. The Governor is proposer and canceller; the timelock owns the treasury and protocol parameters.

**Off-chain**: Snapshot spaces, strategies, voting types and EIP-712 signed votes; execution via a multisig or an optimistic module (oSnap on a Safe). See [references/offchain-voting-and-execution.md](references/offchain-voting-and-execution.md).

**Other models** (design only): quadratic, conviction and reputation voting need Sybil resistance or a non-trivial identity layer; multisig plus timelock fits small or early DAOs.

## 3. Workflow

1. Decide what governance controls (treasury, parameters, upgrades) and what stays immutable; fewer controlled parameters mean a smaller attack surface.
2. Choose the venue: binding on-chain Governor for funds and upgrades, Snapshot for signaling, or a hybrid with an execution module.
3. Design the token: supply, minting rights, vesting, delegation, clock mode (blocks or timestamps).
4. Select parameters from expected holder distribution and turnout: voting delay, voting period, proposal threshold, quorum, timelock delay.
5. Compose the Governor from modules, resolve overrides, and deploy token, timelock, Governor and treasury with a script that wires and then renounces admin roles.
6. Write a fork-capable lifecycle test: delegate, propose, vote, queue, wait, execute, plus negative cases.
7. Verify roles and ownership on chain after deployment; audit before holding funds.
8. Publish a proposal process: forum draft, decoded calldata, simulation, on-chain proposal, monitoring.

## 4. Decision Rules

- Binding decisions that move funds or upgrade contracts: on-chain Governor with `GovernorTimelockControl`. Signaling and low-value choices: Snapshot.
- Use block-number clocks on Ethereum mainnet; use timestamp mode where block production or numbering is irregular (many L2s). Express `votingDelay` and `votingPeriod` in the token's clock unit.
- Use `GovernorVotesQuorumFraction` for quorum relative to supply; revisit the fraction as turnout data arrives.
- Use `GovernorPreventLateQuorum` when a single large vote could decide at the last block.
- Add `GovernorProposalGuardian` or grant `CANCELLER_ROLE` narrowly when a fast cancel path is needed; avoid a second all-powerful admin.
- Give the timelock, not the Governor or an EOA, ownership of everything governance controls.
- Pin the OpenZeppelin version exactly; 5.6.1 and 5.7.0 differ in `Governor.execute` state checks and in `GovernorPreventLateQuorum`.
- Prefer a Safe multisig for operational spending and reserve the Governor for large or structural decisions.

## 5. Coding Standards

- OpenZeppelin Contracts 5.x paths only (`@openzeppelin/contracts/governance/...`); never mix v4 patterns (`Counters`, `GovernorCompatibilityBravo`, `_beforeExecute`).
- Pin `pragma solidity ^0.8.24;` for the library range OZ 5 requires, and a single exact compiler for deployment.
- Override resolution functions only call `super`; keep logic out of them.
- Name roles and parameters in constants and events; document units (blocks or seconds) in NatSpec. No author tags.
- Scripts take addresses from environment variables or keystores, not hard-coded keys.

## 6. Project Structure

```text
src/
  GovToken.sol            ERC20Votes + ERC20Permit
  DaoGovernor.sol         Governor + selected modules
  Treasury.sol            owned by the timelock
script/Deploy.s.sol       deploy and role wiring
test/
  DaoGovernor.t.sol       full lifecycle and negative cases
  invariant/              role and supply invariants
snapshot/                 space settings, strategy notes, proposal templates
docs/governance.md        parameters, roles, proposal process
```

## 7. Design Patterns

- **Governor plus timelock**: Governor decides, timelock delays and executes; everything controlled is owned by the timelock.
- **Delegate-first onboarding**: self-delegate at distribution time (for example airdrop claims) so holders are counted in quorum.
- **Signal then bind**: Snapshot temperature check, then an on-chain proposal with the same payload.
- **Two-speed treasury**: Safe multisig with an approved budget for routine spend, timelocked proposals for large transfers.
- **Guardian cancel path**: a narrow role that can only cancel queued operations.
- **Timestamp clock**: token overrides `clock()` and `CLOCK_MODE()` and the Governor inherits it.

## 8. Best Practices

- Publish decoded calldata with every proposal and simulate it on a fork.
- Use `#proposer=0x<address>` description suffixes to prevent others from front-running your exact proposal.
- Keep parameter changes (`updateQuorumNumerator`, `setVotingPeriod`, `updateTimelock`) behind the same review as upgrades.
- Record deployed addresses, roles and parameters in the repository and verify contracts on the block explorer.
- Test the migration path (new Governor, new timelock) before it is needed.

## 9. Performance

- Voting checkpoint writes cost gas on every transfer of a delegated balance; keep the token simple and avoid extra hooks in `_update`.
- `castVote` is cheap; batch operations in one proposal rather than many proposals, but keep each proposal reviewable.
- Large `calldatas` increase proposal gas; split unrelated actions into separate proposals.
- Off-chain voting removes vote gas, at the cost of binding execution.

## 10. Security

- Voting power is read at the proposal snapshot from checkpoints, so tokens borrowed and returned in one transaction carry no weight; token voting is still purchasable, so budget for the cost of acquiring quorum.
- Verify after deployment that the deployer holds no admin role and that only the Governor can propose and cancel.
- Treat `onlyGovernance` setters and timelock self-calls as high-risk proposal contents.
- Late-quorum, low-turnout, proposal spam, delegate concentration and hostile treasury drains are covered in [references/governance-security.md](references/governance-security.md).
- Off-chain: control the Snapshot space with a multisig, review strategies for manipulable balances, and keep a delay between an off-chain result and execution.
- Run the contract-level checklist from smart-contract-security-expert on the Governor, token, timelock and treasury before launch.

## 11. Testing

- Lifecycle test in Foundry with `vm.roll` and `vm.warp`: delegate, propose, vote, queue, execute (see [references/governor-setup.md](references/governor-setup.md)).
- Negative cases: below threshold, quorum missed, voting twice, execute before the timelock delay, cancel by non-authorized account, spend from the treasury without governance.
- Invariants: no address other than the timelock owns the treasury; total supply equals the sum of balances; role sets match the documented list.
- Fork test proposals that touch live protocols before voting.
- Test the clock mode actually deployed (blocks vs timestamps) because units differ.

## 12. Review Checklist

- [ ] Compiler accepts the Governor with the exact override set: `votingDelay`, `votingPeriod`, `proposalThreshold`, `quorum`, `state`, `proposalNeedsQueuing`, `_queueOperations`, `_executeOperations`, `_cancel`, `_executor`.
- [ ] Units of `votingDelay` and `votingPeriod` match the token clock; the timelock delay is in seconds.
- [ ] Governor holds proposer and canceller roles; nobody else; deployer admin renounced.
- [ ] Treasury and governed contracts are owned by the timelock.
- [ ] Holders can and do delegate; initial delegation is planned.
- [ ] Quorum, threshold and delay justified from holder data.
- [ ] Mint rights and upgrade authority sit behind governance.
- [ ] Proposal review process and monitoring exist.

## 13. Production Notes

- Deploy with a script, then run a verification script that reads roles, owners and parameters from the chain.
- Monitor `ProposalCreated`, `VoteCast`, timelock `CallScheduled` and role events; alert on unexpected role changes.
- Provide a UI or documented manual path (Safe or script) for `propose`, `castVote`, `queue`, `execute`; do not depend on a single hosted front end, and check the current status of any hosted governance UI before relying on it.
- Keep an incident plan: who can cancel, how to pause integrations, how to communicate.
- Re-audit after any module change or OpenZeppelin upgrade.

## 14. Examples

Examples 1 and 2 compile with solc 0.8.38 against OpenZeppelin Contracts 5.6.1 and 5.7.0 (Example 2 also needs forge-std); Example 3 type-checks against `@snapshot-labs/snapshot.js` 0.18.0. The token, treasury and lifecycle test are in [references/governor-setup.md](references/governor-setup.md).

### Example 1: Governor with timelock (OZ 5 override set)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Governor} from "@openzeppelin/contracts/governance/Governor.sol";
import {GovernorSettings} from "@openzeppelin/contracts/governance/extensions/GovernorSettings.sol";
import {GovernorCountingSimple} from "@openzeppelin/contracts/governance/extensions/GovernorCountingSimple.sol";
import {GovernorVotes} from "@openzeppelin/contracts/governance/extensions/GovernorVotes.sol";
import {GovernorVotesQuorumFraction} from "@openzeppelin/contracts/governance/extensions/GovernorVotesQuorumFraction.sol";
import {GovernorTimelockControl} from "@openzeppelin/contracts/governance/extensions/GovernorTimelockControl.sol";
import {TimelockController} from "@openzeppelin/contracts/governance/TimelockController.sol";
import {IVotes} from "@openzeppelin/contracts/governance/utils/IVotes.sol";

/// @notice Token-weighted Governor. Passed proposals are queued in a TimelockController, which owns the treasury.
/// Time units follow the token clock: block numbers with the default ERC20Votes clock (12 s blocks on mainnet).
contract DaoGovernor is
    Governor,
    GovernorSettings,
    GovernorCountingSimple,
    GovernorVotes,
    GovernorVotesQuorumFraction,
    GovernorTimelockControl
{
    constructor(IVotes token, TimelockController timelock)
        Governor("DaoGovernor")
        GovernorSettings(7200 /* 1 day delay */, 50400 /* 7 day vote */, 100_000e18 /* proposal threshold */)
        GovernorVotes(token)
        GovernorVotesQuorumFraction(4) // 4% of past total supply
        GovernorTimelockControl(timelock)
    {}

    // The overrides below only resolve inheritance conflicts; they add no logic.

    function votingDelay() public view override(Governor, GovernorSettings) returns (uint256) {
        return super.votingDelay();
    }

    function votingPeriod() public view override(Governor, GovernorSettings) returns (uint256) {
        return super.votingPeriod();
    }

    function proposalThreshold() public view override(Governor, GovernorSettings) returns (uint256) {
        return super.proposalThreshold();
    }

    function quorum(uint256 timepoint) public view override(Governor, GovernorVotesQuorumFraction) returns (uint256) {
        return super.quorum(timepoint);
    }

    function state(uint256 proposalId) public view override(Governor, GovernorTimelockControl) returns (ProposalState) {
        return super.state(proposalId);
    }

    function proposalNeedsQueuing(uint256 proposalId)
        public
        view
        override(Governor, GovernorTimelockControl)
        returns (bool)
    {
        return super.proposalNeedsQueuing(proposalId);
    }

    function _queueOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) returns (uint48) {
        return super._queueOperations(proposalId, targets, values, calldatas, descriptionHash);
    }

    function _executeOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) {
        super._executeOperations(proposalId, targets, values, calldatas, descriptionHash);
    }

    function _cancel(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) returns (uint256) {
        return super._cancel(targets, values, calldatas, descriptionHash);
    }

    function _executor() internal view override(Governor, GovernorTimelockControl) returns (address) {
        return super._executor();
    }
}
```

### Example 2: Deployment and role wiring (Foundry script)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {TimelockController} from "@openzeppelin/contracts/governance/TimelockController.sol";
import {GovToken} from "./GovToken.sol";
import {DaoGovernor} from "./DaoGovernor.sol";
import {Treasury} from "./Treasury.sol";

/// forge script script/Deploy.s.sol --rpc-url <url> --account <keystore-name> --broadcast
contract DeployDao is Script {
    uint256 constant MIN_DELAY = 2 days; // pick a delay long enough for holders to react and exit

    function run() external returns (DaoGovernor governor, TimelockController timelock, Treasury treasury) {
        address initialHolder = vm.envAddress("INITIAL_HOLDER");

        vm.startBroadcast();
        (, address deployer,) = vm.readCallers();

        GovToken token = new GovToken(initialHolder, 10_000_000e18);

        // The deployer is a temporary admin; it is renounced below, after the Governor holds its roles.
        timelock = new TimelockController(MIN_DELAY, new address[](0), new address[](0), deployer);
        governor = new DaoGovernor(token, timelock);

        timelock.grantRole(timelock.PROPOSER_ROLE(), address(governor));
        timelock.grantRole(timelock.CANCELLER_ROLE(), address(governor));
        timelock.grantRole(timelock.EXECUTOR_ROLE(), address(0)); // anyone can execute a ready operation
        timelock.renounceRole(timelock.DEFAULT_ADMIN_ROLE(), deployer);

        treasury = new Treasury(address(timelock));
        vm.stopBroadcast();
    }
}
```

### Example 3: Casting a Snapshot vote from a browser wallet

```ts
import snapshot from '@snapshot-labs/snapshot.js';
import { Web3Provider, ExternalProvider } from '@ethersproject/providers';

const HUB = 'https://hub.snapshot.org';
const client = new snapshot.Client712(HUB);

declare global {
  interface Window {
    ethereum?: ExternalProvider;
  }
}

/** Casts a single-choice vote with the connected browser wallet; the wallet signs an EIP-712 message. */
export async function castVote(space: string, proposalId: string, choice: number, reason = ''): Promise<unknown> {
  if (!window.ethereum) throw new Error('No injected wallet found');
  const web3 = new Web3Provider(window.ethereum);
  const [account] = await web3.listAccounts();
  return client.vote(web3, account, {
    space,
    proposal: proposalId,
    type: 'single-choice',
    choice, // 1-based index into the proposal's choices
    reason,
    app: 'example-dao-ui',
  });
}
```

## 15. Common Mistakes

- Using v4 Governor APIs (`GovernorCompatibilityBravo`, `_execute` overrides, `Counters`) or copying v4 tutorials onto v5.
- Omitting overrides when combining modules; each function defined by more than one base must be overridden with `override(Governor, <module>)`.
- Giving the Governor, rather than the timelock, ownership of the treasury, which bypasses the delay.
- Leaving `DEFAULT_ADMIN_ROLE` with the deployer, so one key can grant itself `PROPOSER_ROLE`.
- Mixing units: a one-day delay of 86400 in a block-number clock, or 7200 blocks in a timestamp clock.
- Forgetting that voting power needs delegation, then finding quorum unreachable.
- Setting the quorum fraction from another DAO's numbers instead of local turnout.
- Treating a Snapshot result as binding with no execution mechanism or trust assumption.
- Approving a proposal by its title without decoding `targets`, `values` and `calldatas`.
- Building a dashboard on a hosted front end that may disappear instead of on `IGovernor` events.
- Inventing EIPs or modules; use only documented standards such as ERC-5805 (votes), ERC-6372 (clock) and ERC-7786 (crosschain gateways, used by `GovernorCrosschain`).

## 16. References

- [references/governor-setup.md](references/governor-setup.md): OZ 5 modules, token, treasury, clock modes, required overrides, lifecycle test, parameter changes.
- [references/offchain-voting-and-execution.md](references/offchain-voting-and-execution.md): Snapshot basics, signed votes in TypeScript, execution paths (multisig, oSnap), watching a Governor with viem.
- [references/governance-security.md](references/governance-security.md): attack classes, parameter selection, role hygiene, malicious proposals, token design, legal and operational notes.
- OpenZeppelin governance docs: https://docs.openzeppelin.com/contracts/5.x/governance
- OpenZeppelin Contracts source: https://github.com/OpenZeppelin/openzeppelin-contracts
