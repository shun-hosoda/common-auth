$ErrorActionPreference = 'Stop'
$token = (Invoke-RestMethod "http://localhost:8080/realms/master/protocol/openid-connect/token" `
  -Method Post -UseBasicParsing `
  -Body @{client_id='admin-cli';grant_type='password';username='admin';password='admin'}).access_token
$h = @{Authorization="Bearer $token";"Content-Type"="application/json"}
$users = Invoke-RestMethod "http://localhost:8080/admin/realms/common-auth/users?username=testuser_acme-corp" -Headers $h -UseBasicParsing
Write-Host "Found $($users.Count) users"
if ($users.Count -gt 0) {
  $uid = $users[0].id
  Write-Host "User: $($users[0].username) / ID: $uid"
  Invoke-RestMethod "http://localhost:8080/admin/realms/common-auth/users/$uid/execute-actions-email?client_id=example-app&redirect_uri=http://localhost:3000" `
    -Method Put -Headers $h -UseBasicParsing `
    -Body '["UPDATE_PASSWORD"]' | Out-Null
  Write-Host "Password reset email sent! Check MailHog at http://localhost:8025"
} else {
  $all = Invoke-RestMethod "http://localhost:8080/admin/realms/common-auth/users" -Headers $h -UseBasicParsing
  Write-Host "All users:"
  $all | ForEach-Object { Write-Host "  - $($_.username)" }
}
