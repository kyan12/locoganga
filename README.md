# Locoganga

Flask storefront for locoganga.com. Product catalog comes from the partner warehouse API (Winit/Wanyilian); checkout uses Stripe.

## Run locally
    python -m venv venv && . venv/bin/activate
    pip install -r requirements.txt
    export DATABASE_URL=sqlite:///local.db
    flask --app wsgi run

## Configuration (environment variables)
`SECRET_KEY`, `DATABASE_URL`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `WINIT_API_URL`, `WINIT_APP_KEY`, `WINIT_TOKEN`, `SUPPORT_EMAIL`, `PRICE_MARKUP` (default 1.45), mail settings (`MAIL_*`).

## Layout
- `app/blueprints` routes (storefront, cart, checkout, static pages)
- `app/services` Winit API client and product catalog (falls back to `app/static/fallback_products.json` when the API is unavailable)
- `scripts/` one-off maintenance and diagnostic scripts
- Deployed on Vercel (`vercel.json`, `api/index.py`)
