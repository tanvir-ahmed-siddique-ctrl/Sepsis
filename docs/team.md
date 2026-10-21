# Team ownership (suggested)

| Role | Owns | Primary folders |
|---|---|---|
| ML / data lead | Dataset, features, train, eval, model card | `ml/`, `docs/data-card.md`, `docs/model-card.md` |
| Backend / MLOps | API, inference, DB, Docker, deploy | `backend/`, `infra/`, `docker-compose.yml` |
| Frontend / product | Dashboard, charts, demo mode, UX | `frontend/` |
| Business / QA | Ethics, tests, pitch, market, docs QA | `docs/`, pitch assets |

Three-person team: fold Business/QA into Frontend/product.

## Weekly rituals

- Mon: model metrics review
- Wed: product / demo review
- Fri: pitch rehearsal (from Nov onward)

No feature is done without tests + docs + demo-ready state.
