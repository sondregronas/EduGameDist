# Konfigurere frontend

I `docker-compose.yml` kan du endre nettstedstittelen med miljøvariabelen `TITLE`. Frontend-porten endres i tjenestens `ports`-seksjon. Standard er port `80`.

## Legge til spill

Spill administreres i den separate admin-appen. Endringer publiseres på frontend når de lagres. Se [[Adding games]] for mer informasjon.

## Tilpasning

CSS-overstyringer og favicon kan legges i `cfg`. Mappen monteres i frontend-containeren.

> [!NOTE]+
> Enkelte konfigurasjonsendringer kan kreve omstart: `docker compose restart frontend`.
