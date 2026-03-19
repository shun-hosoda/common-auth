$ErrorActionPreference = 'Stop'
$token = (Invoke-RestMethod "http://localhost:8080/realms/master/protocol/openid-connect/token" `
  -Method Post -UseBasicParsing `
  -Body @{client_id='admin-cli';grant_type='password';username='admin';password='admin'}).access_token
Write-Host "Got token"
$h = @{Authorization="Bearer $token";"Content-Type"="application/json"}
$realm = Invoke-RestMethod "http://localhost:8080/admin/realms/common-auth" -Headers $h -UseBasicParsing
Write-Host "Got realm, current smtpServer.host=$($realm.smtpServer.host)"
$realm.smtpServer = [pscustomobject]@{
  host='mailhog'; port='1025'
  from='noreply@example.com'; fromDisplayName='Common Auth'
  auth='false'; ssl='false'; starttls='false'
}
$body = $realm | ConvertTo-Json -Depth 30
Invoke-RestMethod "http://localhost:8080/admin/realms/common-auth" -Method Put -Headers $h -Body $body -UseBasicParsing | Out-Null
Write-Host "SMTP updated. host=mailhog port=1025"
