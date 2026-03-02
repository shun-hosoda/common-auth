#!/bin/bash

# Keycloakの準備完了を待つ
echo "Waiting for Keycloak to be ready..."
until curl -sf http://localhost:8080/health/ready > /dev/null; do
  echo "Keycloak is not ready yet. Waiting..."
  sleep 5
done

echo "✅ Keycloak is ready!"
echo ""
echo "Next steps:"
echo "1. Open http://localhost:8080 in your browser"
echo "2. Login with admin/admin"
echo "3. Select 'common-auth' realm"
echo "4. Go to Clients → Create client"
echo "5. Configure as shown in the terminal output above"
echo ""
echo "Then access your React app at http://localhost:3000"
