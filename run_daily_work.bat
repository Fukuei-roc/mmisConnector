@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
pushd "%~dp0" || exit /b 1
set "OUTPUT_FILE=%TEMP%\mmis-daily-%RANDOM%-%RANDOM%.log"

set "STEP=link"
call :run python -m mmis_connector auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders
if errorlevel 1 goto :finish

set "STEP=not_submitted"
call :run python -m tools.mmis_development.query_daily_inspection_work_orders_not_submitted_for_approval --export-xlsx
if errorlevel 1 goto :finish

set "STEP=export"
call :run python -m tools.mmis_development.auto_process_unclosed_ab_fault_notices --export-xlsx

:finish
set "FINAL_RESULT=%errorlevel%"
if exist "%OUTPUT_FILE%" del /q "%OUTPUT_FILE%"
popd
echo.
if "%FINAL_RESULT%"=="0" echo All steps completed successfully.
if not "%FINAL_RESULT%"=="0" echo A step failed. Check the output above.
echo Press Q to close this window.
powershell.exe -NoProfile -Command "$Host.UI.RawUI.FlushInputBuffer(); do { $key = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown') } until ($key.Character -eq 'q' -or $key.Character -eq 'Q')"
exit /b %FINAL_RESULT%

:run
set "ATTEMPT=0"
:attempt
set /a ATTEMPT+=1 >nul
call %* >"%OUTPUT_FILE%" 2>&1
set "RESULT=%errorlevel%"
if not "%RESULT%"=="0" goto :retry_or_finish
powershell.exe -NoProfile -Command "$raw = Get-Content -LiteralPath $env:OUTPUT_FILE -Raw -Encoding UTF8; if ($env:STEP -eq 'not_submitted') { if ($raw -match '(?m)^Status: SUCCESS\r?$') { exit 0 }; exit 1 }; $r = $raw | ConvertFrom-Json; if ($env:STEP -eq 'link' -and $r.success -eq $true -and $r.completed -eq $true -and $r.failed -eq 0) { exit 0 }; if ($env:STEP -eq 'export' -and $r.success -eq $true -and $r.xlsx_export.status -eq 'success' -and $r.priority_approval_xlsx_export.status -eq 'success') { exit 0 }; exit 1" 2>nul
set "RESULT=%errorlevel%"
if "%RESULT%"=="0" goto :show_result
echo Step %STEP% returned an incomplete result.>>"%OUTPUT_FILE%"

:retry_or_finish
if "%ATTEMPT%"=="3" goto :show_result
if not "%STEP%"=="link" goto :wait_and_retry
rem Link retries only on transport errors; other failures may need manual review.
powershell.exe -NoProfile -Command "$r = Get-Content -LiteralPath $env:OUTPUT_FILE -Raw -Encoding UTF8 | ConvertFrom-Json; if ($r.message -match '^MMIS .*: (ConnectionError|ConnectTimeout|ReadTimeout|Timeout|TimeoutError|ProxyError|SSLError|ChunkedEncodingError)$') { exit 0 }; exit 1" 2>nul
if errorlevel 1 goto :show_result

:wait_and_retry
echo Step %STEP% failed on attempt %ATTEMPT%; retrying.
powershell.exe -NoProfile -Command "Start-Sleep -Seconds 1"
goto :attempt

:show_result
type "%OUTPUT_FILE%"
exit /b %RESULT%
