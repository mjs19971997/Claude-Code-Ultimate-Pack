# Governor Setup (OpenZeppelin Contracts 5.x)

Building blocks for an on-chain DAO with OpenZeppelin Governor, a `TimelockController` and an `ERC20Votes` token. All Solidity here compiles with solc 0.8.38 against OpenZeppelin Contracts 5.6.1 and 5.7.0 (compiled, not executed; run the Foundry test in your project). The Governor itself is Example 1 in `SKILL.md` and the deployment script is Example 2.

## Contents
1. [Version notes](#1-version-notes)
2. [Module menu](#2-module-menu)
3. [Voting token](#3-voting-token)
4. [Treasury](#4-treasury)
5. [Time units and the clock](#5-time-units-and-the-clock)
6. [Required overrides](#6-required-overrides)
7. [Lifecycle test](#7-lifecycle-test)
8. [Proposal operations](#8-proposal-operations)
9. [Upgrading and changing parameters](#9-upgrading-and-changing-parameters)

## 1. Version notes

- OpenZeppelin Contracts 5.6.1 is the npm `latest` tag; 5.7.0 was released on 2026-07-29 and is the latest GitHub release, but npm tags it `dev`. Pin an exact version and check the release notes before choosing.
- 5.7.0 changes that touch governance: `Governor.execute` enforces the expected proposal state based on `proposalNeedsQueuing`; `GovernorQueueNotImplemented` is replaced by `GovernorProposalQueueingNotRequired` and `GovernorProposalQueueingFailed`; `GovernorPreventLateQuorum` caps the extension with `_maxLateQuorumVoteExtension` (default `votingPeriod()`); a new `GovernorCrosschain` module executes crosschain operations via ERC-7786 gateways; `EIP712` names and versions must fit in 31 bytes.
- v4 APIs are gone in v5: `GovernorCompatibilityBravo`, the v4 `_execute`, `_beforeExecute` and `_afterExecute` hooks, `Counters`, and `Ownable()` without an owner. v5 Governor splits execution into `_queueOperations` and `_executeOperations`.
- Imports use `@openzeppelin/contracts/governance/...`; token imports use `@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol`. Upgradeable variants live in `@openzeppelin/contracts-upgradeable` with the same names plus `Upgradeable`.

## 2. Module menu

| Module (`governance/extensions/`) | Purpose |
|---|---|
| `GovernorSettings` | Voting delay, voting period and proposal threshold, changeable by governance. Constructor `(uint48 delay, uint32 period, uint256 threshold)` |
| `GovernorCountingSimple` | Against, For, Abstain counting; quorum counts For and Abstain |
| `GovernorVotes` | Reads voting power and the clock from an ERC-5805 token (`ERC20Votes`, `ERC721Votes`) |
| `GovernorVotesQuorumFraction` | Quorum as a percentage of past total supply, updatable by governance |
| `GovernorTimelockControl` | Queues and executes through an OZ `TimelockController`; the timelock is the executor |
| `GovernorPreventLateQuorum` | Extends voting when quorum is reached late so others can react |
| `GovernorProposalGuardian` | A guardian that can cancel proposals at any stage; without one, proposers cancel their own |
| `GovernorStorage` | Stores proposal details on chain so UIs and callers can queue and execute by id |
| `GovernorSuperQuorum`, `GovernorVotesSuperQuorumFraction` | Proposals above a super quorum succeed before the deadline |
| `GovernorCountingFractional` | Voters can split their weight across Against, For and Abstain |
| `GovernorCountingOverridable` | Delegators override their delegate's vote; needs a token based on `VotesExtended` |
| `GovernorNoncesKeyed` | Per-proposal nonce keys for vote-by-signature |
| `GovernorSequentialProposalId` | Sequential proposal ids instead of hashes |
| `GovernorTimelockAccess`, `GovernorTimelockCompound` | Timelocking through an `AccessManager` or a Compound Timelock |
| `GovernorCrosschain` (5.7.0) | Crosschain execution through remote executors and ERC-7786 gateways |

Mixing modules requires overriding every function that more than one base defines; the compiler lists them. Add one module at a time and keep the override set minimal.

## 3. Voting token

Voting power exists only after delegation (self-delegation counts). Checkpoints are written on transfer for delegated balances, and the Governor reads past checkpoints at the proposal snapshot, so tokens acquired after the snapshot (including by flash loan) carry no weight.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {ERC20Votes} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import {Nonces} from "@openzeppelin/contracts/utils/Nonces.sol";

/// @notice Fixed-supply governance token. Holders must delegate (to themselves or others) to have voting power.
contract GovToken is ERC20, ERC20Permit, ERC20Votes {
    constructor(address recipient, uint256 supply) ERC20("Gov Token", "GOV") ERC20Permit("Gov Token") {
        _mint(recipient, supply);
    }

    // Required overrides: both ERC20 and ERC20Votes define _update; ERC20Permit and Nonces define nonces.
    function _update(address from, address to, uint256 value) internal override(ERC20, ERC20Votes) {
        super._update(from, to, value);
    }

    function nonces(address owner) public view override(ERC20Permit, Nonces) returns (uint256) {
        return super.nonces(owner);
    }
}
```

Choose the supply and mint model deliberately: `ERC20Votes` caps total supply at `type(uint208).max`; mintable tokens let the minter dilute voters, so put the minter behind governance.

## 4. Treasury

The timelock owns the treasury, so only a passed and delayed proposal can spend. Contracts governed this way should use `Ownable(timelock)` or `AccessControl` roles granted to the timelock, never to the Governor directly.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Address} from "@openzeppelin/contracts/utils/Address.sol";

/// @notice Holds ETH. The owner is the TimelockController, so only passed and delayed proposals can spend.
contract Treasury is Ownable {
    event Released(address indexed to, uint256 amount);

    constructor(address timelock) Ownable(timelock) {}

    receive() external payable {}

    function release(address payable to, uint256 amount) external onlyOwner {
        Address.sendValue(to, amount);
        emit Released(to, amount);
    }
}
```

## 5. Time units and the clock

- `votingDelay` and `votingPeriod` use the token's clock (ERC-6372). `ERC20Votes` defaults to block numbers (`clock()` returns `block.number`, `CLOCK_MODE()` returns `"mode=blocknumber&from=default"`), so with 12 s mainnet blocks a day is 7200 blocks and a week is 50400.
- The timelock delay is always in seconds, independent of the clock.
- On chains where block numbers are a poor time proxy, switch the token to timestamps by overriding both `clock()` and `CLOCK_MODE()`; the Governor follows the token's clock automatically (`GovernorVotes.clock()` calls `token().clock()` and falls back to block numbers when the token does not implement ERC-6372).

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {ERC20Votes} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import {Nonces} from "@openzeppelin/contracts/utils/Nonces.sol";

/// @notice Votes token that checkpoints by timestamp (ERC-6372 "mode=timestamp").
/// A Governor built on it reads this clock, so votingDelay and votingPeriod are expressed in seconds.
contract GovTokenTimestamp is ERC20, ERC20Permit, ERC20Votes {
    constructor(address recipient, uint256 supply) ERC20("Gov Token", "GOV") ERC20Permit("Gov Token") {
        _mint(recipient, supply);
    }

    function clock() public view override returns (uint48) {
        return uint48(block.timestamp);
    }

    // solhint-disable-next-line func-name-mixedcase
    function CLOCK_MODE() public pure override returns (string memory) {
        return "mode=timestamp";
    }

    function _update(address from, address to, uint256 value) internal override(ERC20, ERC20Votes) {
        super._update(from, to, value);
    }

    function nonces(address owner) public view override(ERC20Permit, Nonces) returns (uint256) {
        return super.nonces(owner);
    }
}
```

## 6. Required overrides

For `Governor + GovernorSettings + GovernorCountingSimple + GovernorVotes + GovernorVotesQuorumFraction + GovernorTimelockControl` the compiler requires overrides of exactly: `votingDelay`, `votingPeriod`, `proposalThreshold`, `quorum`, `state`, `proposalNeedsQueuing`, `_queueOperations`, `_executeOperations`, `_cancel` and `_executor` (each `override(Governor, <module>)`, calling `super`). The token needs `_update` and `nonces` overrides. Adding `GovernorPreventLateQuorum`, `GovernorStorage` or `GovernorProposalGuardian` adds further overrides; read the compiler error rather than guessing.

## 7. Lifecycle test

Foundry test covering propose, vote, queue, delay and execute against the contracts above. It was compiled with solc 0.8.38 for OpenZeppelin 5.6.1 and 5.7.0.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {TimelockController} from "@openzeppelin/contracts/governance/TimelockController.sol";
import {IGovernor} from "@openzeppelin/contracts/governance/IGovernor.sol";
import {GovToken} from "./GovToken.sol";
import {DaoGovernor} from "./DaoGovernor.sol";
import {Treasury} from "./Treasury.sol";

contract DaoGovernorTest is Test {
    uint256 constant MIN_DELAY = 2 days;

    GovToken token;
    TimelockController timelock;
    DaoGovernor governor;
    Treasury treasury;

    address voter = makeAddr("voter");
    address recipient = makeAddr("recipient");

    function setUp() public {
        token = new GovToken(voter, 10_000_000e18);

        // The deployer is a temporary admin so roles can be granted once the Governor exists.
        timelock = new TimelockController(MIN_DELAY, new address[](0), new address[](0), address(this));
        governor = new DaoGovernor(token, timelock);

        timelock.grantRole(timelock.PROPOSER_ROLE(), address(governor));
        timelock.grantRole(timelock.CANCELLER_ROLE(), address(governor));
        timelock.grantRole(timelock.EXECUTOR_ROLE(), address(0)); // anyone may execute a ready operation
        timelock.renounceRole(timelock.DEFAULT_ADMIN_ROLE(), address(this)); // from here on only governance changes roles

        treasury = new Treasury(address(timelock));
        vm.deal(address(treasury), 10 ether);

        vm.prank(voter);
        token.delegate(voter); // voting power exists only after delegation
        vm.roll(block.number + 1);
    }

    function test_proposalLifecycle() public {
        address[] memory targets = new address[](1);
        uint256[] memory values = new uint256[](1);
        bytes[] memory calldatas = new bytes[](1);
        targets[0] = address(treasury);
        calldatas[0] = abi.encodeCall(Treasury.release, (payable(recipient), 1 ether));
        string memory description = "Pay 1 ETH to recipient";

        vm.prank(voter);
        uint256 id = governor.propose(targets, values, calldatas, description);
        assertEq(uint8(governor.state(id)), uint8(IGovernor.ProposalState.Pending));

        vm.roll(governor.proposalSnapshot(id) + 1);
        vm.prank(voter);
        governor.castVote(id, 1); // 0 = Against, 1 = For, 2 = Abstain

        vm.roll(governor.proposalDeadline(id) + 1);
        assertEq(uint8(governor.state(id)), uint8(IGovernor.ProposalState.Succeeded));

        bytes32 descriptionHash = keccak256(bytes(description));
        governor.queue(targets, values, calldatas, descriptionHash);

        vm.expectRevert(); // timelock delay has not elapsed
        governor.execute(targets, values, calldatas, descriptionHash);

        vm.warp(block.timestamp + MIN_DELAY + 1);
        governor.execute(targets, values, calldatas, descriptionHash);

        assertEq(recipient.balance, 1 ether);
        assertEq(uint8(governor.state(id)), uint8(IGovernor.ProposalState.Executed));
    }
}
```

Extend it with: a proposer below the threshold reverts, a proposal that misses quorum is `Defeated`, `cancel` from the proposer while `Pending`, tokens bought after the snapshot do not count, and a call to `treasury.release` from any other address reverts.

## 8. Proposal operations

- `propose(targets, values, calldatas, description)` returns the proposal id; the id is `hashProposal(targets, values, calldatas, keccak256(bytes(description)))`. A description ending in `#proposer=0x<address>` restricts who can submit that exact proposal (front-running protection built into Governor).
- `castVote(id, support)` uses 0 Against, 1 For, 2 Abstain. `castVoteWithReason`, `castVoteBySig` and the `...WithParams` variants exist on `IGovernor`.
- `state(id)` returns one of Pending, Active, Canceled, Defeated, Succeeded, Queued, Expired, Executed.
- With `GovernorTimelockControl`, `queue` schedules the operation in the timelock and `proposalEta(id)` returns the earliest execution time; `execute` runs it through the timelock.
- Events to index: `ProposalCreated`, `VoteCast`, `VoteCastWithParams`, `ProposalQueued`, `ProposalExecuted`, `ProposalCanceled` (all on `IGovernor`), and `CallScheduled`, `CallExecuted`, `Cancelled` on the timelock.
- Review calldata, not titles: a proposal's real effect is its `targets`, `values` and `calldatas`; verify decoded calls and simulate on a fork before voting.

## 9. Upgrading and changing parameters

- Parameters (`setVotingDelay`, `setVotingPeriod`, `setProposalThreshold`, `updateQuorumNumerator`) have `onlyGovernance` and are changed through proposals.
- `updateTimelock(newTimelock)` is `onlyGovernance`; the old timelock should be drained or handed over deliberately.
- Changing the timelock delay requires a proposal that makes the timelock call `updateDelay` on itself.
- Replacing the Governor: deploy the new Governor, grant it the proposer and canceller roles on the timelock through a proposal, then revoke the old Governor's roles in the same or a later proposal.
- A Governor that is itself upgradeable needs `_authorizeUpgrade` restricted with `onlyGovernance`.
