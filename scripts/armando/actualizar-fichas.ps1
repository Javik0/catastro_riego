# Actualiza las fichas del padrón ya entregadas, reemplazándolas por su versión nueva.
#
# Está pensado para que lo use quien recibió el paquete, sin instalar nada: PowerShell
# viene con Windows. Lo lanza el archivo "ACTUALIZAR FICHAS.bat" que está al lado.
#
# Empareja por NOMBRE DE ARCHIVO, no por carpeta: el nombre de cada ficha empieza por su
# código (S01-C01-R008-F01 …), que es único en todo el padrón. Por eso funciona aunque
# las carpetas se hayan renombrado —"1 ASOCIACION 17 DE JUNIO" en vez de "ASOCIACIÓN 17
# DE JUNIO", por ejemplo—: encuentra cada ficha esté donde esté y la reemplaza en su
# sitio, sin crear carpetas nuevas.
#
# No escribe nada hasta que la persona confirma. Deja un registro en ACTUALIZACION.log.

param([string]$Destino = '')

$ErrorActionPreference = 'Stop'
$base   = Split-Path -Parent $MyInvocation.MyCommand.Path
$origen = Join-Path $base 'FICHAS NUEVAS'
$log    = Join-Path $base 'ACTUALIZACION.log'

function Escribir($texto, $color = 'Gray') {
    Write-Host $texto -ForegroundColor $color
    Add-Content -Path $log -Value $texto -Encoding utf8
}

# ¿Esta esa ruta dentro de la carpeta del propio programa? Hace falta porque el
# ZIP se puede descomprimir DENTRO del paquete de fichas. Si no se excluyera,
# al recorrer el destino se encontrarian tambien las fichas nuevas, cada nombre
# saldria dos veces y el programa las descartaria todas por repetidas.
function EsDelPrograma($ruta) {
    $b = [IO.Path]::GetFullPath($base).TrimEnd('\') + '\'
    return ([IO.Path]::GetFullPath($ruta) + '\').StartsWith($b, 'OrdinalIgnoreCase')
}

Set-Content -Path $log -Value "Actualización de fichas — $(Get-Date -Format 'dd/MM/yyyy HH:mm')" -Encoding utf8
Write-Host ''
Write-Host '  ACTUALIZAR LAS FICHAS DEL PADRON' -ForegroundColor Cyan
Write-Host '  Sistema de riego comunitario Guanguilqui-Porotog' -ForegroundColor DarkGray
Write-Host ''

if (-not (Test-Path $origen)) {
    Escribir "No encuentro la carpeta 'FICHAS NUEVAS' junto a este programa." 'Red'
    Escribir "Descomprima el ZIP completo antes de ejecutarlo: no funciona desde dentro del ZIP." 'Yellow'
    Read-Host 'Pulse Enter para salir'
    exit 1
}

$nuevas = @(Get-ChildItem -Path $origen -Filter *.pdf -Recurse -File)
Escribir "Fichas nuevas a instalar: $($nuevas.Count)" 'White'

# ── Dónde está el paquete a actualizar ──────────────────────────────────────────────
if (-not $Destino) {
    Write-Host ''
    Write-Host '  Buscando el paquete de fichas en sus discos y memorias...' -ForegroundColor DarkGray
    $candidatos = @()
    foreach ($u in (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Root -match '^[A-Z]:\\' })) {
        try {
            $hallados = Get-ChildItem -Path $u.Root -Directory -Recurse -Depth 3 `
                          -Filter 'Sector 1' -ErrorAction SilentlyContinue
            foreach ($h in $hallados) {
                $padre = Split-Path -Parent $h.FullName
                if (-not (EsDelPrograma $padre)) { $candidatos += $padre }
            }
        } catch { }
    }
    $candidatos = @($candidatos | Sort-Object -Unique)

    if ($candidatos.Count -eq 0) {
        Escribir 'No encontre ninguna carpeta de fichas.' 'Yellow'
        Write-Host '  Conecte la memoria y vuelva a ejecutar, o arrastre la carpeta sobre el programa.'
        Read-Host 'Pulse Enter para salir'
        exit 1
    }

    Write-Host ''
    Write-Host '  Encontre estas carpetas de fichas:' -ForegroundColor White
    for ($i = 0; $i -lt $candidatos.Count; $i++) {
        $n = @(Get-ChildItem -Path $candidatos[$i] -Filter *.pdf -Recurse -File).Count
        Write-Host ("   [{0}]  {1}   ({2} fichas)" -f ($i + 1), $candidatos[$i], $n)
    }
    Write-Host ''
    $eleccion = Read-Host '  Escriba el numero de la carpeta que quiere actualizar y pulse Enter'
    $idx = 0
    if (-not [int]::TryParse($eleccion, [ref]$idx) -or $idx -lt 1 -or $idx -gt $candidatos.Count) {
        Escribir 'Opcion no valida. No se hizo ningun cambio.' 'Red'
        Read-Host 'Pulse Enter para salir'
        exit 1
    }
    $Destino = $candidatos[$idx - 1]
}

Escribir ''
Escribir "Carpeta a actualizar: $Destino" 'White'

# ── Emparejar por nombre de archivo ─────────────────────────────────────────────────
# La tabla de PowerShell no distingue mayusculas, y eso hace falta: alguna ficha tiene
# el apellido corregido y su nombre cambio de "lanchimba" a "LANCHIMBA".
$porNombre = @{}
foreach ($f in (Get-ChildItem -Path $Destino -Filter *.pdf -Recurse -File)) {
    # Las fichas nuevas no cuentan como destino, aunque el ZIP se haya
    # descomprimido dentro del paquete.
    if (EsDelPrograma $f.FullName) { continue }
    if ($porNombre.ContainsKey($f.Name)) { $porNombre[$f.Name] += @($f.FullName) }
    else { $porNombre[$f.Name] = @($f.FullName) }
}
Escribir "Fichas en esa carpeta: $($porNombre.Values.Count)" 'White'

$aReemplazar = @(); $sinPareja = @(); $repetidas = @()
foreach ($n in $nuevas) {
    $c = $porNombre[$n.Name]
    if (-not $c)            { $sinPareja  += $n.Name }
    elseif ($c.Count -gt 1) { $repetidas  += $n.Name }
    else                    { $aReemplazar += ,@($n.FullName, $c[0]) }
}

Escribir ''
Escribir "  Se van a reemplazar : $($aReemplazar.Count)" 'Green'
if ($sinPareja.Count) { Escribir "  No estan en la carpeta: $($sinPareja.Count)" 'Yellow' }
if ($repetidas.Count) { Escribir "  Nombre repetido (no se tocan): $($repetidas.Count)" 'Yellow' }
foreach ($s in ($sinPareja | Select-Object -First 10)) { Escribir "     - $s" 'DarkYellow' }

if ($aReemplazar.Count -eq 0) {
    Escribir 'No hay nada que reemplazar. No se hizo ningun cambio.' 'Yellow'
    Read-Host 'Pulse Enter para salir'
    exit 0
}

# Todas las fichas del paquete tienen que haber encontrado su pareja. Si faltan,
# reemplazar solo una parte deja el resto desactualizado y nadie se entera. La
# proteccion esta en DECIRLE lo que va a pasar, no en pedirle una frase dificil:
# una frase larga se escribe mal y acaba tecleando cualquier cosa. Se guarda
# ademas la lista de las que faltan para poder revisarlas.
$pregunta = '  Escriba SI y pulse Enter para continuar (cualquier otra cosa cancela)'
if ($sinPareja.Count -or $repetidas.Count) {
    $listaFaltan = Join-Path $base 'FICHAS QUE NO SE ENCONTRARON.txt'
    Set-Content -Path $listaFaltan -Value ($sinPareja + ($repetidas | ForEach-Object { "$_  (nombre repetido)" })) -Encoding utf8
    Write-Host ''
    Write-Host '  ATENCION --------------------------------------------------------' -ForegroundColor Red
    Write-Host "  Se esperaban $($nuevas.Count) fichas y solo se encontraron $($aReemplazar.Count)." -ForegroundColor Red
    Write-Host "  Faltan $($nuevas.Count - $aReemplazar.Count). Esas NO se actualizarian." -ForegroundColor Red
    Write-Host '  -----------------------------------------------------------------' -ForegroundColor Red
    Write-Host ''
    Write-Host '  Lo normal es que esto NO pase. Antes de seguir, avise y envie el' -ForegroundColor Yellow
    Write-Host '  archivo que acabo de dejar junto a este programa:' -ForegroundColor Yellow
    Write-Host '     FICHAS QUE NO SE ENCONTRARON.txt' -ForegroundColor Yellow
    $faltan = $nuevas.Count - $aReemplazar.Count
    Escribir "FALTAN $faltan fichas; lista en $listaFaltan" 'Red'
    $pregunta = "  Esas $faltan fichas quedarian SIN actualizar. Escriba SI para continuar igual"
}

Write-Host ''
Write-Host '  Se reemplazaran esas fichas por su version nueva.' -ForegroundColor White
Write-Host '  Las demas no se tocan, y no se crea ninguna carpeta.' -ForegroundColor DarkGray
Write-Host ''
$ok = Read-Host $pregunta
# Se aceptan las formas cortas de decir que si; cualquier otra cosa cancela.
if ($ok.Trim().ToUpper() -notin @('SI', 'S', 'Y', 'YES', 'SÍ')) {
    Escribir 'Cancelado por el usuario. No se hizo ningun cambio.' 'Yellow'
    Read-Host 'Pulse Enter para salir'
    exit 0
}

# ── Reemplazar ──────────────────────────────────────────────────────────────────────
# Se copia con las funciones de .NET y el prefijo \\?\ en vez de Copy-Item: Windows
# no abre rutas de mas de 260 caracteres por la via normal, y entre el nombre de la
# carpeta, el de la comunidad y el de la ficha se pasa de ahi con facilidad. El
# prefijo levanta ese limite.
function RutaLarga($p) {
    if ($p.StartsWith('\\?\')) { return $p }
    if ($p.StartsWith('\\'))   { return '\\?\UNC' + $p.Substring(1) }
    return '\\?\' + $p
}

$hechas = 0; $renombradas = 0; $fallos = 0
foreach ($par in $aReemplazar) {
    $nuevo = $par[0]; $viejo = $par[1]
    try {
        [System.IO.File]::Copy((RutaLarga $nuevo), (RutaLarga $viejo), $true)
        $hechas++
        $nombreNuevo = Split-Path -Leaf $nuevo
        if ((Split-Path -Leaf $viejo) -cne $nombreNuevo) {
            # El contenido ya esta bien; el nombre tambien debe quedarlo.
            $destinoFinal = Join-Path (Split-Path -Parent $viejo) $nombreNuevo
            [System.IO.File]::Move((RutaLarga $viejo), (RutaLarga $destinoFinal))
            $renombradas++
        }
        if ($hechas % 250 -eq 0) { Write-Host "     $hechas..." -ForegroundColor DarkGray }
    } catch {
        $fallos++
        Escribir "   ! no se pudo reemplazar $(Split-Path -Leaf $nuevo): $_" 'Red'
    }
}

Escribir ''
Escribir "  LISTO. Reemplazadas: $hechas   ·   renombradas: $renombradas   ·   fallos: $fallos" 'Green'
if ($fallos) {
    Escribir '  Hubo fallos. Cierre cualquier ficha que tenga abierta y vuelva a ejecutar.' 'Yellow'
}
Escribir ''
Escribir "Se guardo el detalle en: $log" 'DarkGray'
Write-Host ''
Read-Host 'Pulse Enter para salir'
