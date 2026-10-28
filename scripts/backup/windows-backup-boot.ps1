<#
.SYNOPSIS
  Back up the Windows boot configuration before any Skullintosh testing.

.DESCRIPTION
  Must run elevated. By default it only READS: it exports the BCD store (bcdedit /export
  writes a copy into the output folder), lists firmware boot entries, and records the disk
  and partition layout.

  With -CopyEsp it also copies the EFI System Partition. To do that it temporarily assigns a
  drive letter to the ESP (mountvol <letter>: /S) and removes it again afterwards
  (mountvol <letter>: /D). It asks for confirmation first. Nothing on the ESP is modified.

.PARAMETER OutputDir
  Destination folder. Prefer a USB stick or another disk.

.PARAMETER CopyEsp
  Also copy the ESP contents (temporarily mounts the ESP; asks first).

.PARAMETER EspLetter
  Free drive letter to use with -CopyEsp (default S).
#>
[CmdletBinding()]
param(
  [string]$OutputDir = (".\efi-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")),
  [switch]$CopyEsp,
  [ValidatePattern("^[D-Z]$")][string]$EspLetter = "S"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw "Run this script from an elevated (Administrator) PowerShell."
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$out = (Resolve-Path $OutputDir).Path
Write-Host "Backing up boot configuration to $out"

bcdedit /export (Join-Path $out "BCD-backup") | Out-Null
bcdedit /enum firmware | Set-Content -Encoding UTF8 (Join-Path $out "bcdedit-enum-firmware.txt")
bcdedit /enum all | Set-Content -Encoding UTF8 (Join-Path $out "bcdedit-enum-all.txt")
Get-Disk | Format-List Number, FriendlyName, PartitionStyle, IsBoot, IsSystem, Size |
  Out-String | Set-Content -Encoding UTF8 (Join-Path $out "disks.txt")
Get-Partition | Format-Table DiskNumber, PartitionNumber, DriveLetter, Type, GptType, Size -AutoSize |
  Out-String -Width 4096 | Set-Content -Encoding UTF8 (Join-Path $out "partitions.txt")

if ($CopyEsp) {
  if (Test-Path "$($EspLetter):\") { throw "Drive $($EspLetter): is already in use; pick another -EspLetter." }
  $answer = Read-Host "Temporarily mount the EFI System Partition as $($EspLetter): to copy it? (yes/no)"
  if ($answer -ne "yes") {
    Write-Host "Skipped ESP copy."
  } else {
    mountvol "$($EspLetter):" /S
    try {
      Copy-Item -Recurse -Force "$($EspLetter):\*" (New-Item -ItemType Directory -Force (Join-Path $out "ESP"))
      Write-Host "ESP copied."
    } finally {
      mountvol "$($EspLetter):" /D
    }
  }
}

Get-ChildItem -Recurse -File $out | Get-FileHash -Algorithm SHA256 |
  ForEach-Object { "$($_.Hash.ToLower())  $($_.Path.Substring($out.Length + 1))" } |
  Set-Content -Encoding UTF8 (Join-Path $out "SHA256SUMS")

Write-Host "Done. Keep $out private and off this machine's internal disks."
Write-Host "Restore instructions: docs/recovery.md"
