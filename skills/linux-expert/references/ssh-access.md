# SSH and Access Control

Reference for OpenSSH server and client configuration, privilege escalation and account hygiene on Linux hosts.

## Contents
- [Versions and defaults](#versions-and-defaults)
- [sshd configuration](#sshd-configuration)
- [Keys and certificates](#keys-and-certificates)
- [Client configuration](#client-configuration)
- [sudo and sudoers](#sudo-and-sudoers)
- [Accounts and PAM](#accounts-and-pam)

## Versions and defaults

- OpenSSH 10.0 made the hybrid post-quantum key exchange `mlkem768x25519-sha256` the default for key agreement in `ssh`, and removed DSA signature support. The `diffie-hellman-group*` and `diffie-hellman-group-exchange-*` methods were removed from sshd's default KEX list. Defaults change between releases: check `ssh -V` and `sshd -T` on the host rather than assuming.
- Do not hard-code long `KexAlgorithms` or `Ciphers` lists unless a compliance profile demands it; pinned lists age badly and block upgrades. If you must, append to defaults with the `+` or `-` prefix (`KexAlgorithms -diffie-hellman-group14-sha256`) instead of replacing them.
- Recent OpenSSH 10.x releases changed how certificates with an empty principals list are matched; read the release notes for your version and review SSH CA workflows before upgrading.
- Ubuntu may start `sshd` through socket activation (`ssh.socket`); then the listen port comes from the socket unit rather than `Port` in `sshd_config`. Check `systemctl status ssh.socket ssh.service`.

## sshd configuration

Put local settings in a drop-in under `/etc/ssh/sshd_config.d/` (Debian and Ubuntu ship `Include /etc/ssh/sshd_config.d/*.conf` near the top of `sshd_config`). sshd uses the first value it reads for each keyword, so file names sort lexically and an earlier file wins. Do not edit the packaged `sshd_config`.

```
# /etc/ssh/sshd_config.d/10-hardening.conf
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
AllowGroups ssh-users
MaxAuthTries 3
LoginGraceTime 30
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
```

Validate and apply safely:
1. `sudo sshd -t` checks syntax; `sudo sshd -T | grep -Ei 'permitroot|passwordauth|allowgroups'` shows the effective values.
2. Keep an existing session open, reload (`systemctl reload ssh` on Debian and Ubuntu, `sshd` on RHEL family), and test a new login from a second terminal before closing the first.
3. Cloud images sometimes ship a `50-cloud-init.conf` with `PasswordAuthentication yes`; because the first value wins, name your drop-in so it sorts earlier (`10-`).

Other controls:
- `Match` blocks scope exceptions (for example allow `AllowTcpForwarding yes` for one bastion group).
- Restrict a key in `authorized_keys` with options such as `restrict`, `from="10.0.0.0/8"` and `command="/usr/local/bin/backup-only"` for automation keys.
- Keep administrative SSH off the public internet when possible (VPN, bastion with `ProxyJump`, or cloud-provider session tooling). Rate limiting with nftables or fail2ban reduces log noise but is not a substitute for key-only authentication.

## Keys and certificates

- Generate Ed25519 keys: `ssh-keygen -t ed25519 -a 100 -C "user@host"`; protect private keys with a passphrase or use a hardware key (`-t ed25519-sk`, needs a FIDO2 authenticator).
- Private keys are `0600` in a `0700` `~/.ssh`; never commit them, bake them into images or place them in cloud-init user-data.
- For fleets, use an SSH certificate authority: sign user keys with short validity (`ssh-keygen -s ca_key -I id -n principal -V +8h user.pub`), and set `TrustedUserCAKeys /etc/ssh/ca.pub` on servers; use `AuthorizedPrincipalsFile` to map principals to accounts. Protect the CA key offline or in an HSM or KMS-backed signer.
- Host keys: distribute known hosts or host certificates (`HostCertificate`, `@cert-authority` in `known_hosts`) so users never accept an unknown fingerprint blindly.
- Revoke with `RevokedKeys /etc/ssh/revoked_keys` (built with `ssh-keygen -k`).

## Client configuration

```
# ~/.ssh/config
Host bastion
    HostName bastion.example.com
    User admin
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes

Host app-*.internal
    ProxyJump bastion
    User deploy
```

- Prefer `ProxyJump` to agent forwarding; forwarded agents let a compromised intermediate host use your keys while connected.
- Avoid `StrictHostKeyChecking no` and `UserKnownHostsFile /dev/null` in automation; pre-seed `known_hosts` instead.
- Connection reuse: `ControlMaster auto`, `ControlPath ~/.ssh/cm-%C`, `ControlPersist 10m`.

## sudo and sudoers

Ubuntu has made the Rust implementation `sudo-rs` the default `sudo` (including 26.04 LTS); the original sudo remains installable as the `sudo.ws` package. `sudo-rs` aims for compatibility with common sudoers syntax but does not implement every sudoers feature, so test a policy with `sudo -l -U <user>` and `visudo -c` on the target host, and check the sudo-rs documentation before relying on rarely used options.

Rules:
- Never edit `/etc/sudoers` directly. Create files in `/etc/sudoers.d/` with `sudo visudo -f /etc/sudoers.d/<name>`; the file name must not contain a dot or end with `~`, or it is ignored. Mode `0440`, owner root.
- Grant specific commands by full path, with fixed arguments where possible. Never grant `ALL` for a service or automation account; never use `NOPASSWD:ALL`.
- Prefer requiring a password for humans. For unattended automation use a dedicated user that can run only exact commands; if a `NOPASSWD:` tag is unavoidable it applies to those exact command lines only, with no wildcards in arguments.
- Do not allow editors, shells, pagers or interpreters (`vim`, `less`, `python`, `bash`, `find`, `tar`) through sudo; each is a root shell escape. Use `sudoedit` for file edits (`Cmnd_Alias` with `sudoedit /etc/example/app.conf`).
- Wildcards in command arguments let users append options; avoid them or list each allowed form.
- Use group-based grants (`%ops`) instead of per-user lines, and audit with `sudo -l`, `/var/log/auth.log` (or `journalctl _COMM=sudo`).

```
# visudo -f /etc/sudoers.d/10-deploy
Cmnd_Alias APP_RESTART = /usr/bin/systemctl restart example-api.service, \
                         /usr/bin/systemctl status example-api.service
%deploy ALL=(root) APP_RESTART
```

## Accounts and PAM

- Lock or remove accounts that are not needed; service accounts use `/usr/sbin/nologin` and no password (`useradd --system --shell /usr/sbin/nologin --home-dir /var/lib/example example`).
- Root: leave the account without a password or locked (`passwd -l root`) and administer through sudo.
- Password policy and lockout for any remaining interactive passwords: `pam_pwquality`, and `pam_faillock` rather than the older `pam_tally2`.
- MFA for SSH: `AuthenticationMethods publickey,keyboard-interactive` with a PAM TOTP module, or FIDO2 keys (`ed25519-sk`).
- Audit logins with `last`, `lastb`, `journalctl -u ssh`, and `ausearch` when auditd is installed.
