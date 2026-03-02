import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@common-auth/react'
import App from './App'
import './index.css'

const AUTH_CONFIG = {
  authority: 'http://localhost:8080/realms/common-auth',
  clientId: 'example-app',
  redirectUri: 'http://localhost:3000/callback',
  postLogoutRedirectUri: 'http://localhost:3000',
  scope: 'openid profile email tenant',
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider {...AUTH_CONFIG}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>,
)
