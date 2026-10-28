## What and why

<!-- What changes, and the evidence (source links, logs, measurements) behind it. -->

## Hardware impact

- [ ] No change to generated EFIs
- [ ] Changes generated EFIs. Profiles affected:
- [ ] Tested on a NUC6i7KYK (link the test report; quote both tree digests)

## Checklist

- [ ] `pytest`, `ruff check src tests`, `ruff format --check src tests` pass
- [ ] `pytest -m network` passes (if builds changed)
- [ ] `skullintosh scan-secrets` is clean
- [ ] Docs, compatibility matrix and CHANGELOG updated where behaviour changes
- [ ] No profile `status` change without a linked hardware report
- [ ] Nothing writes to disks, EFI partitions or boot entries automatically
