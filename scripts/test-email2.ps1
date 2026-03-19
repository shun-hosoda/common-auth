$ErrorActionPreference = 'Stop'
$token = (Invoke-RestMethod "http://localhost:8080/realms/master/protocol/openid-connect/token" `
  -Method Post -UseBasicParsing `
  -Body @{client_id='admin-cli';grant_type='password';username='admin';password='admin'}).access_token
$h = @{Authorization="Bearer $token";"Content-Type"="application/json"}
$users = Invoke-RestMethod "http://localhost:8080/admin/realms/common-auth/users?username=testuser@example.com" -Headers $h -UseBasicParsing
$uid = $users[0].id
Write-Host "Sending reset email to: $($users[0].email) (ID=$uid)"
Invoke-RestMethod "http://localhost:8080/admin/realms/common-auth/users/$uid/execute-actions-email?client_id=example-app&redirect_uri=http://localhost:3000" `
  -Method Put -Headers $h -UseBasicParsing `
  -Body '["UPDATE_PASSWORD"]' | Out-Null
Write-Host "Done. Check MailHog at http://localhost:8025"
