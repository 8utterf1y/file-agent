param()

$ErrorActionPreference = "Stop"

function Test-Administrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Host "== Docker Desktop Hyper-V backend preflight =="
Write-Host ""

$isAdmin = Test-Administrator
if ($isAdmin) {
    Write-Host "Administrator: yes"
} else {
    Write-Host "Administrator: no"
    Write-Host "Some feature checks and Enable-WindowsOptionalFeature commands require an elevated PowerShell."
}

Write-Host ""
Write-Host "Windows version:"
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsHardwareAbstractionLayer | Format-List

Write-Host "Windows optional feature status:"
$featureNames = @("Microsoft-Hyper-V", "Containers")
foreach ($name in $featureNames) {
    try {
        $feature = Get-WindowsOptionalFeature -Online -FeatureName $name
        Write-Host ("{0}: {1}" -f $name, $feature.State)
    } catch {
        Write-Host ("{0}: unable to query ({1})" -f $name, $_.Exception.Message)
    }
}

Write-Host ""
Write-Host "If Hyper-V or Containers is disabled, you can enable them from an elevated PowerShell:"
Write-Host "  Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All"
Write-Host "  Enable-WindowsOptionalFeature -Online -FeatureName Containers -All"
Write-Host ""

$answer = Read-Host "Do you want to run the enable commands now? This may require reboot. Type YES to continue"
if ($answer -eq "YES") {
    if (-not $isAdmin) {
        Write-Host "Please re-run this script from an elevated PowerShell before enabling Windows features."
        exit 1
    }
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
    Enable-WindowsOptionalFeature -Online -FeatureName Containers -All
    Write-Host "Feature commands finished. Reboot Windows if prompted."
} else {
    Write-Host "No Windows features were changed."
}

Write-Host ""
Write-Host "Checklist:"
Write-Host "- Enable hardware virtualization in BIOS/UEFI."
Write-Host "- Use Windows 10/11 Pro, Enterprise, or Education for this Hyper-V route."
Write-Host "- Install Docker Desktop with all-users installation so Hyper-V backend can be selected."
Write-Host "- Use Linux containers in Docker Desktop."
Write-Host "- This script does not download or install Docker Desktop automatically."
Write-Host ""
Write-Host "Docker Desktop command-line install example:"
Write-Host "  Start-Process 'Docker Desktop Installer.exe' -Wait -ArgumentList 'install', '--backend=hyper-v', '--accept-license'"
