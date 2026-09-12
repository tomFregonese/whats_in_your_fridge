@echo off
cd /d %~dp0

rem Convenience wrapper for the common "pull latest code, apply it" cycle —
rem just chains update.bat (rebuild the images) and start.bat (launch the
rem newly built ones) so you don't have to run them one at a time. See
rem each script's own comments for what it actually does.

call update.bat
if errorlevel 1 exit /b 1
call start.bat
