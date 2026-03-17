$envPath = Join-Path $PSScriptRoot "..\\.env"

if (-not (Test-Path $envPath)) {
  throw ".env file not found at $envPath"
}

$config = @{}
Get-Content $envPath | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -match '^\s*$') {
    return
  }

  $parts = $_ -split '=', 2
  if ($parts.Count -ne 2) {
    return
  }

  $key = $parts[0].Trim()
  $value = $parts[1].Trim().Trim('"')
  $config[$key] = $value
}

$requiredKeys = @("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "MAIL_FROM")
foreach ($key in $requiredKeys) {
  if (-not $config.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($config[$key])) {
    throw "Missing required config key: $key"
  }
}

$to = "achim.dannecker@fhnw.ch"
$subject = "Bavarian RoboTaste SMTP Smoketest"
$body = @"
Hello Achim,

this is a Gmail SMTP smoketest from the Bavarian RoboTaste project.

Sent at: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz")
"@

$message = New-Object System.Net.Mail.MailMessage
$message.From = $config["MAIL_FROM"]
$message.To.Add($to)
$message.Subject = $subject
$message.Body = $body

$smtpClient = New-Object System.Net.Mail.SmtpClient($config["SMTP_HOST"], [int]$config["SMTP_PORT"])
$smtpClient.EnableSsl = $true
$smtpClient.Credentials = New-Object System.Net.NetworkCredential($config["SMTP_USER"], $config["SMTP_PASS"])

try {
  $smtpClient.Send($message)
  Write-Output "SMTP smoketest sent successfully to $to"
}
catch {
  Write-Output "SMTP smoketest failed: $($_.Exception.Message)"
  if ($_.Exception.InnerException) {
    Write-Output "Inner exception: $($_.Exception.InnerException.Message)"
  }
  throw
}
finally {
  $message.Dispose()
  $smtpClient.Dispose()
}
