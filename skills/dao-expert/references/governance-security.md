# Governance Security and Design

Attack classes against token governance, how OpenZeppelin Governor 5.x addresses each, and design questions that precede the code. Contract behavior referenced here was checked against OpenZeppelin Contracts 5.6.1 and 5.7.0 sources; legal and economic points are general orientation, not advice.

## Contents
1. [Attack classes](#1-attack-classes)
2. [Parameter selection](#2-parameter-selection)
3. [Timelock and role hygiene](#3-timelock-and-role-hygiene)
4. [Malicious proposals](#4-malicious-proposals)
5. [Token and delegation design](#5-token-and-delegation-design)
6. [Governance minimization](#6-governance-minimization)
7. [Treasury operations](#7-treasury-operations)
8. [Legal and operational notes](#8-legal-and-operational-notes)
9. [Pre-launch checklist](#9-pre-launch-checklist)

## 1. Attack classes

| Attack | How it works | Mitigation |
|---|---|---|
| Flash-loan voting | Borrow tokens, vote, repay in one transaction | Voting power is read from checkpoints at the proposal snapshot (`proposalSnapshot`), so tokens borrowed and returned within one transaction leave no weight |
| Buying or borrowing power before the snapshot | Acquire tokens before the snapshot, vote, sell afterwards | Token voting is purchasable; raise the cost with a proposal threshold and quorum, keep a timelock and cancel path, or consider locked-token (vote-escrow) or non-transferable designs. A voting delay gives holders time to delegate and react, and also gives attackers time to buy |
| Late-quorum swing | A large holder votes in the last block to reach quorum | `GovernorPreventLateQuorum` extends the deadline; 5.7.0 caps the extension (`_maxLateQuorumVoteExtension`, default `votingPeriod()`) |
| Proposal spam | Many proposals to exhaust attention | `proposalThreshold` set as a meaningful share of supply, delegate-gated proposing, a guardian or proposer cancel path |
| Low-turnout capture | Quorum too low relative to active supply | Quorum fraction based on realistic participation (`GovernorVotesQuorumFraction`), review it as supply and turnout change |
| Delegation concentration | A few delegates hold a majority | Delegate statements, term-limited delegation programs, vote-power caps are policy choices implemented in a custom token or Governor |
| Hostile treasury drain | A passed proposal sends funds to an attacker | Timelock delay, cancel role held by a guardian, spending caps in the treasury contract |
| Timelock takeover | Someone holds `DEFAULT_ADMIN_ROLE`, `PROPOSER_ROLE` or `EXECUTOR_ROLE` unexpectedly | Renounce the deployer admin role, grant proposer and canceller only to the Governor, verify with `hasRole` on-chain after deployment |
| Proposal front-running | Someone submits your exact proposal first under their address | Append `#proposer=0x<your address>` to the description; the Governor rejects other proposers |
| Upgrade or parameter hijack | A proposal changes quorum, threshold or timelock to weaken future checks | Treat `onlyGovernance` setters as high-risk calls and review them like upgrades |

## 2. Parameter selection

- Units: `votingDelay` and `votingPeriod` follow the token clock (blocks by default, seconds in timestamp mode); the timelock delay is seconds.
- Choose the timelock delay to be longer than the time the community needs to notice, review and exit or cancel; the right number depends on the DAO, and OpenZeppelin does not prescribe one.
- Choose the proposal threshold and quorum from observed holder distribution and turnout, not from another DAO's numbers.
- Keep emergency paths narrow: a guardian that can only cancel, or a pause on a specific module, not a second admin.
- Document every parameter and who may change it.

## 3. Timelock and role hygiene

- Governor holds `PROPOSER_ROLE` and `CANCELLER_ROLE`; `EXECUTOR_ROLE` goes to the Governor or to `address(0)` (anyone can execute a ready operation).
- Nobody holds `DEFAULT_ADMIN_ROLE` after setup except the timelock itself (it administers itself); renounce the deployer's admin role in the deployment script.
- Contracts that governance controls (treasury, protocol parameters) have the timelock as owner or role holder, not the Governor and not an EOA.
- After deployment, verify roles by reading them from the chain in a script or test, not from the deployment logs.

## 4. Malicious proposals

- The title and description are not binding; only `targets`, `values` and `calldatas` execute. Decode and simulate every proposal on a fork before voting.
- Watch for calls to the timelock or Governor themselves (role changes, `updateTimelock`, `updateDelay`), `delegatecall`-based helpers, proxy upgrades and token mint functions.
- Avoid generic "execute arbitrary calldata" helper contracts in the treasury path; each allowed action should be explicit.
- Time-lock the review: publish the payload and decoded calls on the forum before the on-chain proposal goes up.

## 5. Token and delegation design

- Voting weight comes from `ERC20Votes` checkpoints and requires delegation; communicate this to holders, because undelegated tokens do not vote and do not count toward quorum.
- Supply model: fixed supply, capped mint behind governance, or inflation. A mintable token without a governance-controlled minter lets the minter dilute voters.
- Vesting and locked tokens: decide who votes with unvested tokens. OpenZeppelin `VestingWallet` holds tokens but has no delegation function, so extend or wrap it if beneficiaries should vote.
- Non-transferable or reputation tokens avoid purchasable votes but need a distribution and revocation process; `ERC20Votes` can be adapted by blocking transfers in `_update`.
- Alternatives for counting: `GovernorCountingFractional` lets a custodian split weight, and `GovernorCountingOverridable` lets delegators override their delegate (needs a `VotesExtended` token).

## 6. Governance minimization

- Fewer privileged parameters mean a smaller governance attack surface; make contracts immutable where upgrades are not required.
- Progressive decentralization: begin with a multisig and a published schedule to hand control to a timelock and Governor, and write the milestones down.
- For cross-chain protocols, decide where the authority lives (token chain or execution chain); `GovernorCrosschain` in OpenZeppelin 5.7.0 targets remote execution, and any bridge or gateway becomes part of the trust model.

## 7. Treasury operations

- Day-to-day spending: a Safe multisig with a budget approved by governance, or streaming through vesting-style contracts, so every payment does not need a vote.
- Large moves: through the timelock with an on-chain proposal.
- Publish balances, signers, thresholds and a spending report; rotate signers through a documented process.
- Diversification and yield strategies are risk decisions: each adds contract, oracle and counterparty risk that needs its own review.

## 8. Legal and operational notes

- An unincorporated DAO may leave members exposed to liability; several jurisdictions offer DAO-specific entities or foundations (for example Wyoming DAO LLC, Marshall Islands DAO LLC, Swiss association, Cayman foundation company). Laws change; get qualified counsel and check current statutes.
- Token classification (securities, commodities, payment tokens) depends on facts and jurisdiction; assess before distribution.
- Operations: documented onboarding and offboarding, a conflict-of-interest policy for delegates and grantees, and an incident plan that names who can cancel proposals and pause integrations.

## 9. Pre-launch checklist

- [ ] Contracts audited; Governor, token, timelock and treasury covered, with a fork test of the full lifecycle.
- [ ] Roles verified on-chain: no deployer admin, Governor is the only proposer and canceller, treasury owned by the timelock.
- [ ] Parameters (delay, period, threshold, quorum, timelock delay) documented with reasoning.
- [ ] Initial delegation plan and delegate outreach done; quorum is reachable.
- [ ] Monitoring on proposals, timelock events and role changes.
- [ ] Bug bounty and incident contact published.
- [ ] Forum, review and decoding process for proposals agreed before the first vote.
