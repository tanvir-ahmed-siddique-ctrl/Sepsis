# Release manifest

- Generated: `2026-10-22T22:01:19.557986+00:00`
- Source commit: `5716d365229a3d244d82f97cf18cbfd7dd3cc743` (branch `main`, working tree dirty: `True`)
- Frozen model: `v0.2.0-202609281906` — file SHA-256 `a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d` (matches registry: `True`)
- Replay beds in demo cases: 9 (BED-01.psv, BED-02.psv, BED-03.psv, BED-04.psv, BED-05.psv, BED-06.psv, BED-07.psv, BED-08.psv, BED-09.psv)

## Key file hashes

| File | SHA-256 |
|---|---|
| `ml/artifacts/models/ACTIVE.json` | `bad9c6531883783527e4aa3dc3d6192fa34e2ec56ccd81a06b3892f86533f341` |
| `backend/requirements.txt` | `7449de99fe4042009747b2c959d485857589e87179c20e8365e9f44c03b546c1` |
| `frontend/package.json` | `6419c92b50ef7f1e09ff64afef062ef4dc676b581542b96af14e942c210050f4` |
| `frontend/package-lock.json` | `0584f8d772121879dacdf00ecd53fd0d4dba6efca45251cfb6b138d9e828fce0` |
| `infra/Dockerfile.demo` | `8931fe2e889dc179dbec64ac69f452a13771a19bcaad35678148923763ffcc41` |
| `infra/Dockerfile.api` | `b4bfb918c1860a6d16d05fa78267cd362ba30d4960304041fa7fbbb68a1a6f80` |
| `infra/Dockerfile.web` | `a5fd3cf017bff0173138dff789a1f236e76f2ad8f4ad869272756314e3b41dc7` |
| `docker-compose.yml` | `08257de09434aa1a255d3ae4fcba973e15c2a0044b52a9716cd134a1a65764d9` |
| `docker-compose.site.yml` | `821925692cf63052d48165da8bb4e25f876d0d6aac2c2ed0d37b0dcc1b6f18a5` |
| `AGENTS.md` | `dd3e011b0047935371c91e91e6bca4bc3cf5e9dda7e8ded9c55179630f078f39` |

## Rollback

Redeploy the previous release image/compose bundle, restore the pre-upgrade ops_cli backup, then run `ops_cli verify-audit` and GET /ready before reopening the site.

Point ACTIVE.json at the previous frozen artefact only through the audited model-registry procedure; start-up rejects any hash mismatch.

Regenerate and verify with `infra/release_manifest.py` and `infra/release_manifest.py --verify`.
