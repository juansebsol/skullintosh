<#
.SYNOPSIS
  Skullintosh hardware inventory for Windows (read-only).

.DESCRIPTION
  Collects device IDs, audio codec, BIOS version, CPU, disk layout and firmware boot entries
  for the NUC6i7KYK. It only reads system information and writes text files into the output
  folder. It does not change boot entries, BIOS settings, disks or drivers.

  Serial numbers, UUIDs and MAC addresses are not requested. Run "skullintosh report" on the
  output to mask anything that slips through before sharing it.

.PARAMETER OutputDir
  Folder for the raw inventory (default: .\inventory-raw-<timestamp>).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\inventory\windows-inventory.ps1
  # Run from an elevated prompt to include firmware boot entries (bcdedit /enum firmware).
#>
[CmdletBinding()]
param(
  [string]$OutputDir = (".\inventory-raw-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
  ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

function Save([string]$Name, [scriptblock]$Block) {
  $path = Join-Path $OutputDir $Name
  try {
    & $Block | Out-String -Width 4096 | Set-Content -Encoding UTF8 -Path $path
  } catch {
    "# failed: $($_.Exception.Message)" | Set-Content -Encoding UTF8 -Path $path
  }
}

Write-Host "Writing inventory to $OutputDir"

Save "platform.txt" {
  Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, SystemType
  Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, Version
  Get-CimInstance Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion, ReleaseDate
  "Firmware type: $env:firmware_type"
  try { "Secure Boot enabled: " + (Confirm-SecureBootUEFI) } catch { "Secure Boot: unknown ($($_.Exception.Message))" }
}

Save "cpu.txt" {
  Get-CimInstance Win32_Processor |
    Select-Object Name, Manufacturer, NumberOfCores, NumberOfLogicalProcessors, ProcessorId,
      VirtualizationFirmwareEnabled
}

Save "pci.txt" {
  Get-PnpDevice -PresentOnly |
    Where-Object { $_.InstanceId -like "PCI\*" } |
    Sort-Object InstanceId |
    Select-Object Class, FriendlyName, InstanceId |
    Format-Table -AutoSize
}

Save "usb.txt" {
  Get-PnpDevice -PresentOnly |
    Where-Object { $_.InstanceId -like "USB\*" } |
    Sort-Object InstanceId |
    Select-Object Class, FriendlyName, InstanceId |
    Format-Table -AutoSize
}

Save "audio.txt" {
  Get-PnpDevice -PresentOnly |
    Where-Object { $_.InstanceId -like "HDAUDIO\*" } |
    Select-Object FriendlyName, InstanceId |
    Format-Table -AutoSize
}

Save "network.txt" {
  # InterfaceDescription only: no MAC addresses.
  Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue |
    Select-Object Name, InterfaceDescription, Status, LinkSpeed |
    Format-Table -AutoSize
}

Save "disks.txt" {
  # No SerialNumber, UniqueId or partition GUIDs.
  Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, BusType, MediaType,
    @{n = "SizeGB"; e = { [math]::Round($_.Size / 1GB) } }
  Get-Disk | Select-Object Number, FriendlyName, PartitionStyle, BusType, IsBoot, IsSystem
  Get-Partition | Select-Object DiskNumber, PartitionNumber, DriveLetter, Type, GptType,
    @{n = "SizeMB"; e = { [math]::Round($_.Size / 1MB) } }
}

if ($isAdmin) {
  Save "efiboot.txt" { bcdedit /enum firmware }
} else {
  "# skipped: run from an elevated prompt to read firmware boot entries" |
    Set-Content -Encoding UTF8 -Path (Join-Path $OutputDir "efiboot.txt")
}

@"
Raw Skullintosh inventory. PRIVATE: may still contain machine-specific identifiers.
Create a shareable version with:  skullintosh report --input <this folder> --output report.md
Review the report by eye before posting it anywhere.
"@ | Set-Content -Encoding UTF8 -Path (Join-Path $OutputDir "README.txt")

Write-Host "Done. Next: skullintosh report --input $OutputDir --output inventory-report.md"
