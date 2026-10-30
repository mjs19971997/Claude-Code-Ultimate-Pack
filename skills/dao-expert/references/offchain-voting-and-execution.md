# Off-chain Voting and Execution

Snapshot-style off-chain voting, how its results reach the chain, and how to watch an on-chain Governor from TypeScript. The TypeScript below was type-checked with TypeScript 5.x against `@snapshot-labs/snapshot.js` 0.18.0 and viem 2.x.

## Contents
1. [On-chain or off-chain](#1-on-chain-or-off-chain)
2. [Snapshot basics](#2-snapshot-basics)
3. [Casting a vote with snapshot.js](#3-casting-a-vote-with-snapshotjs)
4. [Executing off-chain results](#4-executing-off-chain-results)
5. [Front ends and tooling status](#5-front-ends-and-tooling-status)
6. [Watching an on-chain Governor](#6-watching-an-on-chain-governor)
7. [Off-chain security notes](#7-off-chain-security-notes)

## 1. On-chain or off-chain

| | On-chain Governor | Off-chain (Snapshot) |
|---|---|---|
| Vote cost | Gas per vote | Free (signed message) |
| Binding | Execution enforced by contracts and timelock | Signal only, unless an execution module or trusted signers enforce it |
| Voting power | Token checkpoints at the proposal snapshot | Strategies computed at a snapshot block by Snapshot's score service |
| Trust | Contract code and timelock | Snapshot infrastructure, strategy code, and whoever executes the result |
| Typical use | Treasury, parameters, upgrades | Temperature checks, signaling, grants prioritization, low-value decisions |

A common split: signal off-chain first, then put the binding proposal on chain.

## 2. Snapshot basics

- A **space** holds settings: network, voting strategies, proposal validation (who may propose), voting types and plugins. Space settings are controlled by the space controller (commonly an ENS name owner).
- **Strategies** compute voting power at a snapshot block (token balances, delegated balances, staked balances, and so on). Several strategies can be combined. Voting power is fixed at the snapshot block, so tokens acquired after it do not count.
- **Voting types** in `snapshot.js` 0.18.0: `single-choice`, `approval`, `quadratic`, `ranked-choice`, `weighted` and `basic`. Quadratic and weighted choices are sent as JSON strings by the client.
- Votes and proposals are EIP-712 typed-data messages signed by the voter's wallet and posted to Snapshot's sequencer; the typed-data domain is `{ name: "snapshot", version: "0.1.4" }` in that package version. Hub: `https://hub.snapshot.org`; testnet hub: `https://testnet.hub.snapshot.org`.
- Private voting (`privacy: 'shutter'`) exists as a proposal option in the client; check the current Snapshot docs for availability and trust model before relying on it.
- Quadratic voting and one-person-one-vote schemes need a Sybil-resistant identity layer; token-based quadratic voting is trivially split across addresses.

## 3. Casting a vote with snapshot.js

`@snapshot-labs/snapshot.js` signs through ethers v5 types (`Web3Provider` or `Wallet` from `@ethersproject/*`), so pair it with `@ethersproject/providers` rather than ethers v6 objects. The example uses the connected browser wallet, so no private key is handled by the app.

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

Notes:
- `choice` for `single-choice` is the 1-based index of the option.
- The wallet shows an EIP-712 request, not a transaction; vote messages cost no gas.
- Proposal creation uses `client.proposal(web3, account, { space, type, title, body, discussion, choices, start, end, snapshot, plugins })` where `snapshot` is a block number and `plugins` is a JSON string; check the package types for the installed version.
- To read voting power, `snapshot.utils.getVp(address, network, strategies, snapshotBlock, space, false)` calls Snapshot's score API; see the package source for the current signature.

## 4. Executing off-chain results

An off-chain result changes nothing on chain by itself. Options, from least to most trust-minimized:

1. **Signer-executed**: a Safe multisig executes the result by hand. Simple, but the signers can ignore or alter the result. Publish the transaction payload before voting and have signers verify the decoded calldata.
2. **Optimistic execution with oSnap**: a Zodiac module on a Safe lets anyone propose the transactions attached to a passed Snapshot proposal by posting a bond; after a challenge period without a dispute they execute, and disputes are resolved through UMA's oracle. It is configured through Snapshot's SafeSnap plugin using the module address. Details and parameters (bond, challenge window, minimum voting period, quorum) are in UMA's oSnap documentation; check them for the current version.
3. **SafeSnap with Reality.eth**: the earlier SafeSnap design uses a Safe module with Reality.eth as the oracle; some DAOs have migrated from it to oSnap.
4. **Move binding decisions on chain**: an OpenZeppelin Governor with a timelock executes without trusted signers; see [governor-setup.md](governor-setup.md).

Whatever the path, put a timelock or challenge period between the vote and the funds, keep the Safe threshold meaningful, and restrict the module with Safe guards or allowances if the tooling supports it.

## 5. Front ends and tooling status

- Hosted governance front ends (for example Tally) come and go; check the current status of any hosted UI before depending on it. The Governor contracts stay usable without it: any front end that reads `IGovernor` events and the ERC-6372 clock works, and calls such as `propose`, `castVote`, `queue` and `execute` can be sent from a Safe, a script or a block explorer.
- Index `ProposalCreated`, `VoteCast`, `ProposalQueued`, `ProposalExecuted` and `ProposalCanceled` yourself (viem, ethers, a subgraph) if you need a dashboard.
- For delegate discovery and delegation UX, publish delegate statements and a delegation page that calls `delegate` or `delegateBySig` on the token.

## 6. Watching an on-chain Governor

```ts
import { createPublicClient, http, parseAbi, type Address } from 'viem';
import { mainnet } from 'viem/chains';

const GOVERNOR = process.env.GOVERNOR_ADDRESS as Address;

const governorAbi = parseAbi([
  'event ProposalCreated(uint256 proposalId, address proposer, address[] targets, uint256[] values, string[] signatures, bytes[] calldatas, uint256 voteStart, uint256 voteEnd, string description)',
  'event VoteCast(address indexed voter, uint256 proposalId, uint8 support, uint256 weight, string reason)',
  'function state(uint256 proposalId) view returns (uint8)',
  'function proposalSnapshot(uint256 proposalId) view returns (uint256)',
  'function proposalDeadline(uint256 proposalId) view returns (uint256)',
]);

const STATES = ['Pending', 'Active', 'Canceled', 'Defeated', 'Succeeded', 'Queued', 'Expired', 'Executed'] as const;

const client = createPublicClient({ chain: mainnet, transport: http(process.env.RPC_URL) });

/** Prints new proposals with their decoded calls so reviewers can read the real effect, not just the title. */
export function watchProposals(): () => void {
  return client.watchContractEvent({
    address: GOVERNOR,
    abi: governorAbi,
    eventName: 'ProposalCreated',
    onLogs: async (logs) => {
      for (const log of logs) {
        const { proposalId, targets, values, calldatas, description } = log.args;
        if (proposalId === undefined) continue;
        const state = await client.readContract({ address: GOVERNOR, abi: governorAbi, functionName: 'state', args: [proposalId] });
        console.log(STATES[state], proposalId.toString(), description?.split('\n')[0]);
        targets?.forEach((t, i) => console.log('  call', t, values?.[i]?.toString(), calldatas?.[i]));
      }
    },
  });
}
```

Run it with `GOVERNOR_ADDRESS` and `RPC_URL` set. For production monitoring, alert on `ProposalCreated`, large `VoteCast` weights, timelock `CallScheduled` and any `RoleGranted` or `RoleRevoked` event on the timelock.

## 7. Off-chain security notes

- A signed vote message is harmless, but approve only EIP-712 requests whose domain and fields you recognize; a phishing site can request other typed-data signatures.
- Strategies that read manipulable balances (a lending pool's receipt token, an LP position) can be gamed at the snapshot block. Review strategy code and prefer simple, auditable sources.
- Proposal validation (a minimum balance or delegated power to propose) limits spam; set it high enough to matter and low enough not to exclude members.
- Space controller keys are powerful: they can change strategies and validation. Control the ENS name with a multisig.
- Treat results from a hosted service as a signal that can be unavailable or disputed; archive proposals and vote data for audit.
