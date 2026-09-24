#Requires -Version 5.1
<#
.SYNOPSIS
    Приводит регистр имён запечённых спрайтов к тому, что записан в SpriteInfo/*.foinfo.

.DESCRIPTION
    Движок ищет ресурсы регистрозависимо, а ключ секции в SpriteInfo/<Pack>.foinfo — это ровно тот
    путь, который запрашивает рендер (для art/critters/* ImageBaker намеренно пишет нижний регистр).
    Если на диске лежит файл с другим регистром, спрайт молча не находится.

    Скрипт читает ключи из *.foinfo и переименовывает реальные файлы под них. Переименование идёт
    в два шага через временное имя, иначе на регистронезависимой ФС (NTFS) смена только регистра
    не срабатывает. Скрипт идемпотентен: повторный запуск ничего не делает.

    ВНИМАНИЕ: игра (клиент и сервер) должна быть закрыта.

.PARAMETER Roots
    Каталоги Baking для обработки. По умолчанию — корневой Baking и оба Binaries/*/Baking.

.PARAMETER DryRun
    Только показать расхождения, ничего не переименовывать.

.EXAMPLE
    .\Normalize-BakedArtCase.ps1 -DryRun
.EXAMPLE
    .\Normalize-BakedArtCase.ps1
#>
[CmdletBinding()]
param(
    [string[]] $Roots,
    [switch]   $DryRun
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

if (-not $Roots -or $Roots.Count -eq 0) {
    $candidates = @(
        (Join-Path $repoRoot 'Baking'),
        (Join-Path $repoRoot 'Binaries\Client-Windows-win64\Baking'),
        (Join-Path $repoRoot 'Binaries\Server-Windows-win64\Baking')
    )
    $Roots = $candidates | Where-Object { Test-Path -LiteralPath $_ }
}

if (-not $Roots -or $Roots.Count -eq 0) {
    Write-Warning "Не найдено ни одного каталога Baking. Сначала выполни: cmake --build Build --config Release --target ForceBakeResources"
    return
}

$totalRenamed = 0

foreach ($root in $Roots) {
    $root = (Resolve-Path -LiteralPath $root).Path
    Write-Host "`n=== $root ===" -ForegroundColor Cyan

    foreach ($pack in Get-ChildItem -LiteralPath $root -Directory) {
        $spriteInfo = Join-Path $pack.FullName 'SpriteInfo'
        if (-not (Test-Path -LiteralPath $spriteInfo)) { continue }

        $infoFiles = Get-ChildItem -LiteralPath $spriteInfo -Filter '*.foinfo' -File
        if ($infoFiles.Count -eq 0) { continue }

        # Реальные имена файлов пака, ключ — путь в нижнем регистре
        $onDisk = @{}
        Get-ChildItem -LiteralPath $pack.FullName -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Substring($pack.FullName.Length + 1).Replace('\', '/')
            $onDisk[$rel.ToLowerInvariant()] = $_.FullName
        }

        $plan = @{}
        foreach ($info in $infoFiles) {
            foreach ($line in [System.IO.File]::ReadLines($info.FullName)) {
                if ($line.Length -lt 3) { continue }
                if ($line[0] -ne '[' -or $line[$line.Length - 1] -ne ']') { continue }

                $key = $line.Substring(1, $line.Length - 2)
                $actual = $onDisk[$key.ToLowerInvariant()]
                if (-not $actual) { continue }

                $wantedLeaf = Split-Path -Leaf $key
                if ((Split-Path -Leaf $actual) -cne $wantedLeaf) {
                    $plan[$actual] = $wantedLeaf
                }
            }
        }

        if ($plan.Count -eq 0) { continue }

        if ($DryRun) {
            $sample = @($plan.Keys)[0]
            Write-Host ("[DRY] {0}: расхождений {1}, напр. {2} -> {3}" -f `
                $pack.Name, $plan.Count, (Split-Path -Leaf $sample), $plan[$sample]) -ForegroundColor Yellow
            $totalRenamed += $plan.Count
            continue
        }

        foreach ($full in $plan.Keys) {
            $leaf = $plan[$full]
            $tmp = "$full.__casetmp"
            Rename-Item -LiteralPath $full -NewName (Split-Path -Leaf $tmp)
            Rename-Item -LiteralPath $tmp  -NewName $leaf
        }

        Write-Host ("{0}: переименовано {1}" -f $pack.Name, $plan.Count) -ForegroundColor Green
        $totalRenamed += $plan.Count
    }
}

if ($DryRun) {
    Write-Host "`n[DRY] Всего расхождений: $totalRenamed" -ForegroundColor Yellow
}
else {
    Write-Host "`nВсего переименовано: $totalRenamed" -ForegroundColor Green
}
