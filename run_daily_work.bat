@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
pushd "%~dp0" || exit /b 1
set "OUTPUT_FILE=%TEMP%\mmis-daily-%RANDOM%-%RANDOM%.log"

set "STEP=link"
call :run python -m mmis_connector auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders
if errorlevel 1 goto :finish

set "STEP=export"
call :run python -m tools.mmis_development.auto_process_unclosed_ab_fault_notices --export-xlsx

:finish
set "FINAL_RESULT=%errorlevel%"
if exist "%OUTPUT_FILE%" del /q "%OUTPUT_FILE%"
popd
echo.
if "%FINAL_RESULT%"=="0" echo 所有程式正常執行完畢，沒有錯誤。
if not "%FINAL_RESULT%"=="0" echo 有程式未正常執行完畢，請檢查上方結果。
echo 按 Q 鍵關閉視窗。
powershell.exe -NoProfile -Command "$Host.UI.RawUI.FlushInputBuffer(); do { $key = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown') } until ($key.Character -eq 'q' -or $key.Character -eq 'Q')"
exit /b %FINAL_RESULT%

:run
set "ATTEMPT=0"
:attempt
set /a ATTEMPT+=1 >nul
call %* >"%OUTPUT_FILE%" 2>&1
set "RESULT=%errorlevel%"
if "%RESULT%"=="0" goto :show_result

rem MMISSession reports transport failures in the JSON message field.
powershell.exe -NoProfile -Command "$r = Get-Content -LiteralPath $env:OUTPUT_FILE -Raw -Encoding UTF8 | ConvertFrom-Json; if ($r.message -match '^MMIS 網路請求失敗: (ConnectionError|ConnectTimeout|ReadTimeout|Timeout|TimeoutError|ProxyError|SSLError|ChunkedEncodingError)$') { exit 0 }; exit 1" 2>nul
if errorlevel 1 goto :show_result
if "%ATTEMPT%"=="1" goto :attempt
if "%ATTEMPT%"=="2" goto :wait_and_retry
goto :show_result

:wait_and_retry
powershell.exe -NoProfile -Command "Start-Sleep -Seconds 1"
goto :attempt

:show_result
type "%OUTPUT_FILE%"
if not "%RESULT%"=="0" exit /b %RESULT%
powershell.exe -NoProfile -Command "$r = Get-Content -LiteralPath $env:OUTPUT_FILE -Raw -Encoding UTF8 | ConvertFrom-Json; if ($env:STEP -eq 'link' -and $r.success -eq $true -and $r.completed -eq $true -and $r.failed -eq 0) { exit 0 }; if ($env:STEP -eq 'export' -and $r.success -eq $true -and $r.xlsx_export.status -eq 'success' -and $r.priority_approval_xlsx_export.status -eq 'success') { exit 0 }; exit 1" 2>nul
set "RESULT=%errorlevel%"
if not "%RESULT%"=="0" echo 程式結果未符合完成條件。
exit /b %RESULT%
