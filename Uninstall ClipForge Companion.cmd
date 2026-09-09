@echo off
reg delete "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.clipforge.engine" /f /reg:32
echo Chrome registration removed. Your project folder and saved videos are kept.
pause
