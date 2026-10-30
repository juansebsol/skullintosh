# Apple ID, iCloud and iMessage (optional)

Skip this unless you want Apple services. Installing and using macOS doesn't need it.

Every Skullintosh build carries a placeholder identity: serial `W00000000001`, board serial
`M0000000000000001` (OpenCore's sample values, the same in every copy), and the NUC's own
firmware UUID. Apple ID, iCloud, iMessage, FaceTime and App Store sign-in need a unique identity.
It stays on your machine and never goes into this repository.

> [!WARNING]
> Choose the identity **before** signing in, and keep it. Signing in with one serial and
> changing it later can get the Apple account flagged.

1. Run [GenSMBIOS](https://github.com/corpnewt/GenSMBIOS) outside this repository and generate
   an identity for the profile's model: `iMac17,1` for Monterey (other profiles name theirs in
   `profiles/<name>/profile.toml`).
2. Create `local/smbios.toml` in the repository. The `local/` folder is git-ignored.

   ```toml
   SystemSerialNumber = "<serial from GenSMBIOS>"
   MLB = "<board serial from GenSMBIOS>"
   SystemUUID = "<UUID from GenSMBIOS>"
   ROM = "<12 hex digits, e.g. the Ethernet MAC address>"
   ```

3. Build with it, keeping your other options:

   ```bash
   skullintosh build --target monterey --set wifi=airportitlwm --smbios local/smbios.toml
   ```

   The output goes to `build/monterey-release-personal/` and contains
   `PERSONALIZED-DO-NOT-SHARE.txt`. `skullintosh package` refuses to package it.
4. Install it with [Updating the EFI later](installation.md#updating-the-efi-later), reboot,
   then sign in under System Preferences → Apple ID.

Never paste these values into issues, logs or screenshots. `skullintosh scan-secrets` checks the
working tree for them.
