param(
    [string]$SourceDir = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$OutputPath = "",
    [switch]$IncludeGitHub
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$SourceDir = (Resolve-Path $SourceDir).Path
$projectName = Split-Path $SourceDir -Leaf
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path (Split-Path $SourceDir -Parent) "$projectName-deploy-$timestamp.zip"
}

$OutputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
$outputName = Split-Path $OutputPath -Leaf

$excludeDirNames = @(
    ".git",
    ".claude",
    ".codebuddy",
    ".idea",
    ".vscode",
    ".vs",
    "node_modules",
    "otherproj",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".vite",
    ".venv",
    ".env",
    "venv",
    "env",
    "ENV",
    "logs",
    "log",
    "dist",
    "build",
    "htmlcov",
    ".cov",
    "coverage",
    "downloads",
    "eggs",
    ".eggs",
    "lib",
    "lib64",
    "parts",
    "sdist",
    "var",
    "wheels"
)

if (-not $IncludeGitHub) {
    $excludeDirNames += ".github"
}

$excludeFilePatterns = @(
    ".env",
    ".env.local",
    ".env.dev",
    ".env.development.local",
    ".env.production.local",
    "CODEBUDDY.md",
    "*.log",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.7z",
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.swp",
    "*.swo",
    "*~",
    ".DS_Store",
    "Thumbs.db",
    ".coverage",
    "coverage.xml",
    "*.egg",
    "*.egg-info",
    "MANIFEST"
)

if (Test-Path $OutputPath) {
    Remove-Item $OutputPath -Force
}

$sourcePrefix = $SourceDir.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

$files = Get-ChildItem $SourceDir -Recurse -File -Force | Where-Object {
    $relativePath = $_.FullName.Substring($sourcePrefix.Length)
    $normalizedRelativePath = $relativePath.Replace([System.IO.Path]::DirectorySeparatorChar, "/")
    $pathParts = $relativePath -split "[\\/]"

    foreach ($dirName in $excludeDirNames) {
        if ($pathParts -contains $dirName) {
            return $false
        }
    }

    foreach ($pattern in $excludeFilePatterns) {
        if ($_.Name -like $pattern) {
            return $false
        }
    }

    if ($_.Name -eq ".env.production" -and $normalizedRelativePath -ne "frontend/.env.production") {
        return $false
    }

    $_.Name -ne $outputName
}

if (-not $files) {
    throw "No files found to package."
}

$zip = [System.IO.Compression.ZipFile]::Open($OutputPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($sourcePrefix.Length).Replace([System.IO.Path]::DirectorySeparatorChar, "/")
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $file.FullName, $relativePath, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
}
finally {
    $zip.Dispose()
}

Write-Host "Deployment package created: $OutputPath"
Write-Host "Packaged files: $($files.Count)"
Write-Host "Directory structure: preserved"
Write-Host "Upload this zip to the onsite server, unzip it, then run:"
Write-Host "  cp .env.docker .env"
Write-Host "  docker-compose build"
Write-Host "  docker-compose up -d"
