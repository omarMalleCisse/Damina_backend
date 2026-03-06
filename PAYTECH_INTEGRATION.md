# Intégration PayTech - Documentation

Basé exclusivement sur :
- [doc.intech.sn/doc_paytech.php](https://doc.intech.sn/doc_paytech.php)
- [PayTech Postman collection](https://doc.intech.sn/PayTech%20x%20DOC.postman_collection.json)

---

## 1. Configuration Backend (.env)

```env
PAYTECH_API_KEY=votre_cle_api
PAYTECH_SIGNING_KEY=votre_cle_secrete
PAYTECH_SANDBOX=true
PAYTECH_IPN_URL=https://votre-ngrok.ngrok-free.app/api/payments/webhook
```

- **PAYTECH_API_KEY** / **PAYTECH_SIGNING_KEY** : depuis le dashboard PayTech (Paramètres → API)
- **PAYTECH_SANDBOX** : `true` pour test (montant débité 100–150 CFA), `false` pour production
- **PAYTECH_IPN_URL** : URL HTTPS du webhook. En local, utiliser [ngrok](https://ngrok.com) :
  ```bash
  ngrok http 8000
  # puis PAYTECH_IPN_URL=https://xxxx.ngrok-free.app/api/payments/webhook
  ```

---

## 2. Endpoints Backend

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/payments/create` | Crée un paiement (auth requise) |
| POST | `/api/payments/webhook` | Webhook IPN PayTech (sale_complete) |
| GET  | `/api/payments/{id}` | Statut du paiement |

---

## 3. Flux de paiement

1. Le frontend appelle `POST /api/payments/create` avec `{ order_id, amount, currency }`
2. Le backend appelle PayTech `POST /payment/request-payment`
3. Le backend renvoie `{ redirect_url }`
4. Le frontend redirige l'utilisateur vers `redirect_url` (page PayTech)
5. L'utilisateur paie sur PayTech
6. PayTech redirige vers `success_url` ou `cancel_url`
7. PayTech envoie un webhook POST vers `ipn_url` (type_event: sale_complete)

---

## 4. Intégration Frontend (React)

### Option A : Redirection classique

```tsx
// Exemple : créer un paiement et rediriger
async function initPayment(orderId: number, amount: number) {
  const res = await fetch('/api/payments/create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      order_id: orderId,
      amount,
      currency: 'XOF',
      success_url: `${window.location.origin}/payment/success`,
      cancel_url: `${window.location.origin}/payment/cancel`,
      target_payment: 'Orange Money, Wave, Free Money', // optionnel
    }),
  });
  const data = await res.json();
  if (data.redirect_url) {
    window.location.href = data.redirect_url;
  }
}
```

### Option B : Web SDK PayTech (popup)

La doc officielle propose un SDK JS. Inclure :

```html
<link rel="stylesheet" href="https://paytech.sn/cdn/paytech.min.css">
<script src="https://paytech.sn/cdn/paytech.min.js"></script>
```

Votre backend doit exposer un endpoint `requestTokenUrl` qui retourne `{ success: 1, token, redirect_url }`.
Vous pouvez réutiliser la logique de `/api/payments/create` ou créer un endpoint dédié.

```tsx
// Exemple avec Web SDK
function PayButton({ orderId, amount }) {
  const handlePay = () => {
    (new (window as any).PayTech({
      idTransaction: String(orderId),
    })).withOption({
      requestTokenUrl: `${API_BASE}/api/payments/create`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      presentationMode: (window as any).PayTech.OPEN_IN_POPUP,
      didReceiveError: (err) => console.error(err),
      didReceiveNonSuccessResponse: (res) => console.error(res),
    }).send();
  };
  return <button onClick={handlePay}>Payer {amount} FCFA</button>;
}
```

> **Note** : Le Web SDK attend un body avec `idTransaction` ; adaptez votre backend si nécessaire pour ce mode.

---

## 5. Pages success / cancel

Créez des routes pour les redirections PayTech :

- `/payment/success` : afficher un message de succès, lien vers la commande
- `/payment/cancel` : afficher "Paiement annulé", lien pour réessayer

PayTech peut ajouter des query params à `success_url` et `cancel_url` (ex. `transactionId`, `ref_command`).

---

## 6. Sécurité et bonnes pratiques

- **Ne jamais exposer** API_KEY et API_SECRET côté frontend (CORS désactivé sur PayTech)
- Toutes les requêtes PayTech passent par votre backend
- Vérifier le webhook via `api_key_sha256` et `api_secret_sha256` (déjà implémenté)
- En production, utiliser HTTPS pour l’IPN
- Logger les webhooks pour le debug
- Traiter les erreurs et afficher des messages clairs à l’utilisateur

---

## 7. Erreurs courantes

| Erreur | Cause | Solution |
|--------|-------|----------|
| `ipn_url doit être en HTTPS` | URL http pour le webhook | Configurer PAYTECH_IPN_URL avec ngrok |
| `Format de requête invalid` | Mauvais format de requête | Vérifier Content-Type: application/json et headers API_KEY, API_SECRET |
| `Invalid webhook signature` | Clés incorrectes | Vérifier PAYTECH_API_KEY et PAYTECH_SIGNING_KEY |
